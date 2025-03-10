"""
Module containing ServerHandler class that communicates with the MQTT broker.
The class responds to the activity of connected lamps, 
and sends updates to them when this lamp has any to send.
Also processes and forwards config changes from server commands.

ServerHandler uses the other class in this module called ConnectionHandler which
maintains and tries to repair connections to the wifi, internet and to the broker
server. This class is not meant to be used independently.

This module relies on the umqtt module from https://github.com/micropython/micropython-lib/blob/master/micropython/umqtt.simple/umqtt/simple.py
Credit to the contributors for excellent work.
"""

from exceptions import *
import network
import socket
import time
from umqtt import MQTTClient, MQTTException
from user_com import UserCom

class ServerHandler:
    
    """
    Class that handles communication with MQTT broker server.

    Attributes:
        name (str): Username when authenticating to the MQTT broker.
        friend_name (str): Username of friend.
        ping_interval (int): Number of ticks between sending each server ping.
        
    Methods:
        update_settings(settings: dict): Setting up the handler.
        connect(): The handler connects to the network, (internet) and broker.
        send_state(state: str, col: tuple): Update the server about this lamp's state and corresponding color.
        check_msg(): Checks if there are any messages from broker waiting.
    """
    
    # Settings
    name: str = None
    friend_name: str = None
    ping_interval: int = None
        
    _room_name: str = None
    _lamp_id: str = None
    
    # State
    _received: dict = None
    _usercom: UserCom = None
    _client = None
    _count: int = 0
    
    def __init__(self):
        """
        Creates the ServerHandler object.
        """
        self._client = ConnectionHandler()
        
    def connect(self) -> None:
        """
        Connect to wifi, (internet) and broker.
        
        Should only by called at boot. Afterwards, all reconnection attempts
        are made inside ConnectionHandler. Usage of this method will not result in any
        reconnection attempts. The idea is that errors should be quicker to diagnose at startup.
        """
        try:
            self._client.connect()
        except NetworkException as e:   # This makes sure that we try the backup credentials too
            self._client._connfail(e)
            self._client.connect()
        
    def check_msg(self) -> dict:
        """
        Check for messages from server.
        
        None if there are no messages available.

        Returns:
            dict: Received message.
        """
        self._client.check_msg()
        
        if self._count % self.ping_interval == 0:
            self._client.ping()
        
        self._count += 1
        
        msg = self._received
        self._received = None
        
        return msg
            
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
            'ping_interval' (int): Every ping_interval:th time that check_msg is called, it will also send a ping to the server.
        
        Returns:
            None
        """
            
        if 'name' in settings:
            self._lamp_id = settings['name'] + '_lamp'
            self.name = settings['name']
            
        if 'friend_name' in settings:
            if self.name < settings['friend_name']:
                self._room_name = self.name + '-' + settings['friend_name']
            else:
                self._room_name = settings['friend_name'] + '-' + self.name
            self.friend_name = settings['friend_name']
            
        if 'ping_interval' in settings:
            self.ping_interval = settings['ping_interval']
            
        # Add settings that the ConnectionHandler wants
        toclient = settings.copy()
        toclient['last_will'] = (self._room_name + '/' + self.friend_name, 'inactive:(0, 0, 0)')
        toclient['callback'] = self._handle_msg
        toclient['subscriptions'] = [
                self._room_name + '/' + self.name,
                self.name + '/control'
            ]
        toclient['ping_topic'] = self._room_name + '/' + self.name + "-ping"
            
        self._client.update_settings(toclient)
    
    def verify_setup(self) -> None:
        """
        Tries to detect if the object has been illegally set up.
        
        Raises:
            IllegalSetupException: Signals that the object is not properly set up.
        
        Returns:
            None
        """

        if not isinstance(self.name, str):
            raise IllegalSetupException('No username given or username is not a string.')
        if not isinstance(self.friend_name, str):
            raise IllegalSetupException('Friend\'s name is not given or name is not a string')
        if not isinstance(self.ping_interval, int) or self.ping_interval <= 0:
            raise IllegalSetupException('Ping interval is not given, not an int or not bigger than 0.')
        
        self._client.verify_setup()
        
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
        
        self._client.send(target, msg, qos = 0)
        
    def _handle_msg(self, topic: str, msg: str) -> None:
        """
        Callback function for subscriptions.

        Args:
            topic (str): Topic where message appeared.
            msg (str): Message content.
        """
        
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
                
class ConnectionHandler:
    """
    Attributes:
        ssid (str): Wifi SSID
        passw (str): Wifi password
        backup_ssid (str): Backup Wifi SSID
        backup_pass (str): Backup Wifi password
        enable_internet (bool): Whether or not the lamp should attempt to connect to internet.
        ssl (str): SSL address to use (optional).
        timeout (int): Seconds to wait for connection.
        
        reconnect_policy (list[int]): Number of minutes between each reconnection attempt.
        success_limit (int): Number of minutes a connection must be persistent to be considered successful
                                and reset the reconnect policy.
        
        name (str): Username when authenticating to the MQTT broker.
        server_addr (str): Address of broker server.
        port (int): Broker's port. Set to 0 to use the default unencrypted 1883.
        server_pass (str): Password when authenticating to the MQTT broker.
        ping_topic (str): Topic where ping messages are to be sent.
        
        last_will (tuple[str]): Last will in MQTT protocol, formatted as (topic, msg).
        callback (function): Callback function for incoming messages.
        subscriptions (list[str]): Topics that should be subscribed to.
    """
    
    # Settings
    ssid = None
    passw = None
    backup_ssid = None
    backup_pass = None
    enable_internet = False
    ssl = None
    timeout = None
    
    reconnect_policy = [0, 0, 0, 1, 5, 15, 30, 60, 180, 180, 180]  # minutes between reconnection attemps
    success_limit = 5        # minutes necessary for a connection to be deemed successful
    _reconnect_iteration = 0
    
    name = None
    server_addr = None
    port = 0
    server_pass = None
    ping_topic = None
    dropped_ping_limit = None
    
    last_will = None
    callback = None
    subscriptions = None
    
    _lamp_id = None
    
    # State
    _wlan = None
    _mqtt_client = None
    _received = None
    _usercom: UserCom = None
    _last_fail = None   # last time the connection failed
    _since_pong = 0
    
    def __init__(self):
        """
        Creates the ConnectionHandler object.
        """
        self._last_fail = time.time()
        self._usercom = UserCom()
        
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
            'ssl' (str): SSL address.
            'timeout' (int): Timeout that, when possible, should be used for network connectivity. 
            'last_will' (tuple[str]): Last will in MQTT protocol (topic, msg).
            'callback' (function): Callback function to be used for incoming messages.
            'subscriptions' (list[str]): Topics that should be subscripted to.
            'room_name' (str): MQTT room name.
            'dropped_ping_limit (int): Number of ping intervals without hearing a response before considering the network lost.
        
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
            self.name = settings['name']
            self._lamp_id = settings['name'] + '_lamp'
            
        if 'server_addr' in settings:
            self.server_addr = settings['server_addr']
            
        if 'server_port' in settings:
            self.port = settings['server_port']
        
        if 'server_pass' in settings:
            self.server_pass = settings['server_pass']
        
        if 'ssl' in settings:
            self.ssl = settings['ssl']
            
        if 'timeout' in settings:
            self.timeout = settings['timeout']
            
        if 'last_will' in settings:
            self.last_will = settings['last_will']
            
        if 'callback' in settings:
            self.callback = settings['callback']
            
        if 'subscriptions' in settings:
            self.subscriptions = settings['subscriptions']
            
        if 'ping_topic' in settings:
            self.ping_topic = settings['ping_topic']
            
        if 'dropped_ping_limit' in settings:
            self.dropped_ping_limit = settings['dropped_ping_limit']
    
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
        if self.callback == None:
            raise IllegalSetupException('Callback function is not set.')
        if not isinstance(self.ping_topic, str):
            raise IllegalSetupException('No ping topic given or address is not a string.')
  
    def connect(self) -> None:
        """
        Connect to the Wifi network, (internet) and to broker server.
        
        Only needs to be called once from outside, at boot.

        Raises:
            IllegalSetupException: Illegal configuration.
            NetworkException: Something went wrong in the connection process.
            
        Returns: 
            None
        """
        
        if self.reconnect_policy[int(self._reconnect_iteration/2)] != 0:    # If this wasn't a direct reconnect.
            self._usercom.connecting()
                
        if self.ssid == None:
            raise IllegalSetupException('No SSID is given.')

        # Wlan
        use_backup = self._reconnect_iteration % 2 == 1
        self._connect_wlan(use_backup)
        
        # Internet
        if self.enable_internet:
            self._test_internet()
        
        # Server
        self._connect_server()
        
        if self.reconnect_policy[int(self._reconnect_iteration/2)] != 0:    # If this wasn't a direct reconnect.
            self._usercom.boot_succ()
            
    def check_msg(self) -> None:
        """
        Checks if any messages are available.
        """
        reconn = False
        while True:
            try:
                if reconn:
                    self.connect()
                    reconn = False
                    
                self._mqtt_client.check_msg()
                break
            except OSError as e:
                err = NetworkException('OSError thrown. Likely that network socket timed out.', SERVER_FAULT)
                self._connfail(err)
                reconn = True
            except MQTTException as e:
                err = NetworkException(f'Unknown error. MQTT error code: {e}', SERVER_FAULT)
                self._connfail(err)
                reconn = True
            except NetworkException as e:
                self._connfail(e)
                reconn = True
    
    def ping(self) -> None:
        """
        Sends a ping to the server.
        
        Should be called periodically as this detects when connection has gone out and serves as
        keepalive packets.
        """
        
        reconn = False
        while True:
            try:
                if reconn:
                    self.connect()
                    reconn = False
                    
                if self._since_pong > self.dropped_ping_limit:
                    self._since_pong = 0
                    raise NetworkException('To many pings dropped. Unknown error.', UNSPECIFIED_FAULT)
            
                self._since_pong += 1
                
                self.send(self.ping_topic, 'ping')
                
                break
            
            except OSError as e:
                err = NetworkException('OSError thrown. Likely that network socket timed out.', SERVER_FAULT)
                self._connfail(err)
                reconn = True
            except MQTTException as e:
                err = NetworkException(f'Unknown error. MQTT error code: {e}', SERVER_FAULT)
                self._connfail(err)
                reconn = True
            except NetworkException as e:
                self._connfail(e)
                reconn = True
                
    def send(self, target: str, msg: str, qos = 0):
        """
        Send a message to server.

        Args:
            target (str): Topic the message is to be sent to.
            msg (str): Message content.
            qos (int, optional): QoS. Defaults to 0.
        """
        reconn = False
        while True:
            try:
                if reconn:
                    self.connect()
                    reconn = False
                    
                self._mqtt_client.publish(target, msg, qos)
                break
            except OSError as e:
                err = NetworkException('OSError thrown. Likely that network socket timed out.', SERVER_FAULT)
                self._connfail(err)
                reconn = True
            except MQTTException as e:
                err = NetworkException(f'Unknown error. MQTT error code: {e}', SERVER_FAULT)
                self._connfail(err)
                reconn = True
            except NetworkException as e:
                self._connfail(e)
                reconn = True
    
    def _callback_wrapper(self, topic: str, msg: str):
        """
        Determines if the message is the return pong of sent ping and filters that out.
        Relays the rest to the actual callback function.

        Args:
            topic (str): _description_
            msg (str): _description_
        """
        topic = topic.decode('utf-8')
        msg = msg.decode('utf-8')
        
        print(f"Inbound message: {topic} : {msg}")
        
        if topic == self.ping_topic:
            self._since_pong = 0
        else:
            self.callback(topic, msg)
                        
    def _connfail(self, error: NetworkException) -> None:
        """
        Called when connection has failed somewhere.
        
        Effectively handles the reconnection policy.
        Whenever function calls that uses network features are made, they should be enclosed in a try except
        within a while True.
        If a NetworkException is raised, this method should be called followed by a call to connect()
        (also within the while True and try).

        Args:
            error (NetworkException): The NetworkException that was caught.

        Raises:
            error: That same NetworkException if the reconnect policy has deemed it time to give up.
        """
        
        # if the last connection was too short lived to be considered successful
        if time.time() - self._last_fail - self.reconnect_policy[min(0, int(self._reconnect_iteration/2))]*60.0 <= self.success_limit*60.0:
            self._reconnect_iteration += 1
        else:
            self._reconnect_iteration = 0
        
        self._last_fail = time.time()
        
        wait = 0
        
        if self._reconnect_iteration % 2 == 0:    # We want to try backup. No wait necessary.
            try:
                wait = self.reconnect_policy[int(self._reconnect_iteration/2)]*60.0
            except IndexError:
                print('Connection failed. Restart to retry.')
                raise error     # we have given up
        
        if wait > 1.0:
            print(f'Connection error. Reattempting in {wait} seconds.')
            self._usercom.conn_err(error.errorcode, wait)
            print('Reconnecting...\n')
        else:
            print('Connection error')
            print('Reconnecting...\n')
                
    def _connect_wlan(self, use_backup: bool) -> None:
        """
        Connect to Wifi network.

        Params:
            use_backup (bool): True if backup credentials are to be used.

        Raises:
            NetworkException: Connection failed.
        """
        
        # Cleaning from previous connections (unclear how necessary this is)
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
                print('Attempting backup wifi')
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
        
        # Cleaning from previous sessions
        if self._mqtt_client != None:
            try:
                self._mqtt_client.disconnect()
            except OSError:	# Sometimes raised by mqtt client when connection was broken on server side
                pass
            
            del self._mqtt_client
        
        self._mqtt_client = MQTTClient(self._lamp_id, self.server_addr, self.port,
                                    self.name, self.server_pass, keepalive = 0)
        
        try:
            self._mqtt_client.connect(timeout = self.timeout)
        except MQTTException as e:
            errcode = str(e)
            if errcode == "4":
                raise IllegalSetupException('Incorrect username or password to broker server.')
            else:
                raise NetworkException('Unknown error. MQTT error code: ' + errcode, SERVER_FAULT)
        except OSError:
            raise NetworkException('OSError thrown. Likely that network socket timed out.', SERVER_FAULT)
        
        try:
            self._mqtt_client.set_last_will(*self.last_will)
            self._mqtt_client.set_callback(self._callback_wrapper)
            
            for s in self.subscriptions:
                self._mqtt_client.subscribe(s)
                
            self._mqtt_client.subscribe(self.ping_topic)
                
        except MQTTException as e:
            raise NetworkException('Unknown error. MQTT error code: ' + str(e), SERVER_FAULT)
        except OSError:
            raise NetworkException('OSError thrown. Could be that network socket timed out.', UNSPECIFIED_FAULT)