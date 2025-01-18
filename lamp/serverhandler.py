"""
Module containing ServerHandler class that communicates with the MQTT broker.
The class responds to the activity of connected lamps, 
and sends updates to them when this lamp has any to send.
Also processes and forwards config changes from server commands.

This module relies on the umqtt module from https://github.com/micropython/micropython-lib/blob/master/micropython/umqtt.simple/umqtt/simple.py
Credit to the contributors for excellent work.
"""

from exceptions import *
import network
import socket
import time
from umqtt import MQTTClient, MQTTException

class ServerHandler:
    
    """
    Class that handles communication with MQTT broker server.

    Attributes:
        ssid (str): Wifi SSID
        passw (str): Wifi password
        backup_ssid (str): Backup Wifi SSID
        backup_pass (str): Backup Wifi password
        enable_internet (bool): Whether or not the lamp should attempt to connect to internet.
        name (str): Username when authenticating to the MQTT broker.
        server_addr (str): Address of broker server.
        port (str): Broker's port. Set to 0 to use the default unencrypted 1883.
        server_pass (str): Password when authenticating to the MQTT broker.
        friend_name (str): Username of friend.
        
    Methods:
        update_settings(settings: dict): Setting up the handler.
        connect(): The handler connects to the network, (internet) and broker.
        send_state(state: str, col: tuple): Update the server about this lamp's state and corresponding color.
        check_msg(): Checks if there are any messages from broker waiting.
    """
    
    # Settings
    ssid = None
    passw = None
    backup_ssid = None
    backup_pass = None
    enable_internet = False
    ssl = None
    timeout = None
    
    name = None
    server_addr = None
    port = 0
    server_pass = None
    friend_name = None
    
    _room_name = None
    _lamp_id = None
    
    # State
    _wlan = None
    _mqtt_client = None
    _received = None
    
    def __init__(self):
        """
        Creates the ServerHandler object.
        """
        pass
            
    def update_settings(self, settings: dict) -> None:
        """
        Updates settings in the handler.

        Args:
            settings (dict): All settings.
            
        Recognized keys:
            'wifi_ssid' (str): SSID of Wifi
            'passw' (str): Wifi password
            'backup_ssid' (str): Backup Wifi SSID
            'backup_pass' (str): Backup Wifi password
            'enable_internet' (bool): Whether or not the lamp should attempt to connect to internet.
            'name' (str): Username when authenticating to the MQTT broker.
            'server_addr' (str): Address of broker server.
            'port' (int): Broker's port (int). Set to 0 to use the default unencrypted 1883 or encrypted 8883.
            'server_pass' (str): Password when authenticating to the MQTT broker.
            'friend_name' (str): Username of friend.
            'ssl' (str): SSL address.
            'timeout' (int): Timeout that, when possible, should be used for network connectivity. 
        
        Returns:
            None
        """
        
        if 'wifi_ssid' in settings:
            self.ssid = settings['wifi_ssid']
            
        if 'wifi_pass' in settings:
            self.passw = settings['wifi_pass']
            
        if 'backup_wifi_ssid' in settings:
            self.backup_ssid = settings['backup_wifi_ssid']
            
        if 'backup_wifi_pass' in settings:
            self.backup_pass = settings['backup_wifi_pass']

        if 'connect_to_internet' in settings:
            self.enable_internet = settings['connect_to_internet']
            
        if 'name' in settings:
            self._lamp_id = settings['name'] + '_lamp'
            self.name = settings['name']
            
        if 'server_addr' in settings:
            self.server_addr = settings['server_addr']
            
        if 'server_port' in settings:
            self.port = settings['server_port']
        
        if 'server_pass' in settings:
            self.server_pass = settings['server_pass']
            
        if 'friend_name' in settings:
            if self.name < settings['friend_name']:
                self._room_name = self.name + '-' + settings['friend_name']
            else:
                self._room_name = settings['friend_name'] + '-' + self.name
            self.friend_name = settings['friend_name']
        
        if 'ssl' in settings:
            self.ssl = settings['ssl']
            
        if 'timeout' in settings:
            self.timeout = settings['timeout']
    
    def verify_setup(self) -> None:
        """
        Tries to detect if the object has been illegally set up.
        
        Raises:
            IllegalSetupException: Signals that the object is not properly set up.
        
        Returns:
            None
        """
        
        if not isinstance(self.ssid, str):
            raise IllegalSetupException('No SSID given or SSID is not a string.')
        if not isinstance(self.timeout, int):
            raise IllegalSetupException('No timeout given or timeout is not an int.')
        if not isinstance(self.name, str):
            raise IllegalSetupException('No username given or username is not a string.')
        if not isinstance(self.server_addr, str):
            raise IllegalSetupException('No server address given or address is not a string.')
        if not isinstance(self.friend_name, str):
            raise IllegalSetupException('Friend\'s name is not given or name is not a string')
            
    def connect(self, use_backup: bool) -> None:
        """
        Connect to the Wifi network, (internet) and to broker server.

        Params:
            use_backup (bool): True if backup credentials are to be used.

        Raises:
            IllegalSetupException: Illegal configuration.
            NetworkException: Something went wrong in the connection process.
            
        Returns: 
            None
        """
        
        if self.ssid == None:
            raise IllegalSetupException('No SSID is given.')
        
        self._connect_wlan(use_backup)
        
        if self.enable_internet:
            self._test_internet()
        
        self._connect_server()
        
    def _connect_wlan(self, use_backup: bool) -> None:
        """
        Connect to Wifi network.

        Params:
            use_backup (bool): True if backup credentials are to be used.

        Raises:
            NetworkException: Connection failed.
        """
        
        # Cleaning from previous connections
        temp = network.WLAN(network.STA_IF)
        temp.disconnect()
        temp.active(False)
        del temp
    
        self._wlan = network.WLAN(network.STA_IF)
        self._wlan.active(True)
        
        if not use_backup:
            self._wlan.connect(self.ssid, self.passw)
        else:
            if self.backup_ssid == None:
                raise NetworkException('Could not connect to local WIFI. Error code: ' + str(self._wlan.status()),
                                   LAN_FAULT)
            else:
                self._wlan.connect(self.backup_ssid, self.backup_pass)
                
        wait = self.timeout
        
        while wait > 0:
            if self._wlan.status() in [network.STAT_CONNECTING, 2]:
                time.sleep(1)
                wait -= 1
            else:
                break
        
        if self._wlan.status() != network.STAT_GOT_IP:
            raise NetworkException('Could not connect to local WIFI nor to backup. Error code: ' + str(self._wlan.status()),
                                   LAN_FAULT)
            
    def _test_internet(self) -> None:
        """
        Tests the internet connection by pinging google.com.

        Raises:
            NetworkException: Connection failed.
        """
        
        s = None
        
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(self.timeout)
            addr = socket.getaddrinfo('www.google.com', 80)[0][-1]
            s.connect((addr))
            s.close()
        except Exception as e:
            s.close()
            raise NetworkException('Unable to ping Google', INTERNET_FAULT)
    
    def _connect_server(self) -> None:
        """
        Connects to the broker server.

        Raises:
            NetworkException: Connection failed.
            
        Returns:
            None
        """
        
        self._mqtt_client = MQTTClient(self._lamp_id, self.server_addr, self.port,
                                       self.name, self.server_pass, keepalive = 0)
        
        try:
            self._mqtt_client.connect(timeout = self.timeout)
        except MQTTException as e:
            errcode = str(e)
            if errcode == "4":
                raise NetworkException('Incorrect username or password', SERVER_FAULT)
            else:
                raise NetworkException('Unknown error. MQTT error code: ' + errcode, SERVER_FAULT)
        except OSError:
            raise NetworkException('OSError thrown. Likely that network socket timed out.', SERVER_FAULT)
        
        try:
            self._mqtt_client.set_last_will(self._room_name + '/' + self.friend_name, 'inactive:(0, 0, 0)')
            self._mqtt_client.set_callback(self._handle_msg)
            self._mqtt_client.subscribe(self._room_name + '/' + self.name)
            self._mqtt_client.subscribe(self.name + '/control')
        except MQTTException as e:
            raise NetworkException('Unknown error. MQTT error code: ' + str(e), SERVER_FAULT)
        except OSError:
            raise NetworkException('OSError thrown. Could be that network socket timed out.', UNSPECIFIED_FAULT)
        
    def send_state(self, state: str, col: tuple) -> None:
        """
        Send state and color tuple to broker server.

        Args:
            state (str): 'active', 'holding' or 'sleep'
            col (tuple): The new color of the change.

        Raises:
            NetworkException: Connection to broker failed.
        """
        
        msg = state + ':' + str(col)
        target = self._room_name + '/' + self.friend_name
        
        try:
            self._mqtt_client.publish(target, msg, qos = 0)
        except MQTTException as e:
            raise NetworkException('Unknown error. MQTT error code: ' + str(e), SERVER_FAULT)
        except OSError:
            raise NetworkException('OSError thrown. Could be that network socket timed out.', UNSPECIFIED_FAULT)
        
    def check_msg(self) -> dict:
        """
        Check for new messages.

        Raises:
            NetworkException: Connection failed.

        Returns:
            str: Friend's state.
            str: Friend's color.
        """
        
        try:
            self._mqtt_client.check_msg()
        except MQTTException as e:
            raise NetworkException('Unknown error. MQTT error code: ' + str(e), SERVER_FAULT)
        except OSError:
            raise NetworkException('OSError thrown. Could be that network socket timed out.', UNSPECIFIED_FAULT)
        
        temp = self._received
        self._received = None
        
        return temp
        
    def _handle_msg(self, topic: str, msg: str) -> None:
        """
        Callback function for subscriptions.

        Args:
            topic (str): Topic where message appeared.
            msg (str): Message content.
        """
        
        topic = topic.decode('utf-8')
        msg = msg.decode('utf-8')
        
        rcv = dict()
        
        if topic == self._room_name + '/' + self.name:
            rcv['type'] = 'friend_update'
            
            state, color = msg.split(':')
            
            # Parse string into color tuple
            color = color.replace('(', '').replace(')', '').replace(' ', '')
            temp = color.split(',')
            color = tuple(int(v) for v in temp)
            
            rcv['state'] = state
            rcv['color'] = color
            
            self._received = rcv
        
        elif topic == self.name + '/control':
            if msg == 'reboot':
                rcv['type'] = 'reboot'
                self._received = rcv
            else:
                print('config update received')
                rcv['type'] = 'update_config'
                setting, value = msg.split(':')
                
                changes = dict()
                changes['setting'] = setting
                changes['value'] = value
                rcv['changes'] = changes
                
                self._received = rcv