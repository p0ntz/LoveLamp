"""
Contains tools and classes for debugging various parts of the friendship lamp.

Will be developed and implemented after necessity.
"""

from umqtt import MQTTClient
from settingshandler import SettingsHandler
import network
import time
from machine import ADC, Pin

class sensor_debugger:
    """
    Debugging tools concerning the sensor. 
    Requires a functional implementation of settingshandler and the config.txt file.
    """
    _sensor = None
    _sensor_tick = None
    _serv_client = None
    _conf = None
    _wlan = None
    _topic = None
    
    def __init__(self):
        """
        Initialization. Imports settings from config.txt, connects to wifi, connects to broker,
        initializes a sensor object.
        """
        
        # Importing connection settings
        self._conf = SettingsHandler()
        self._conf.import_config()
        print('Settings imported')
        
        # Connecting to broker
        self._wlan = network.WLAN(network.STA_IF)
        self._wlan.active(True)
        self._wlan.connect(self._conf.c['wifi_ssid'], self._conf.c['wifi_pass'])
        
        while self._wlan.status() != network.STAT_GOT_IP:
            time.sleep(1)
        
        print('Connected to network')
        
        self._serv_client = MQTTClient(self._conf.c['name'],
                                       self._conf.c['server_addr'],
                                       self._conf.c['server_port'],
                                       self._conf.c['name'],
                                       self._conf.c['server_pass'])
        
        self._serv_client.connect()
        
        print('Connected to broker')
        
        self._topic = self._conf.c['name'] + '/debug'
        
        print(f'Outputs will be published to {self._topic}')
        
        # Setting up sensor
        self._sensor = ADC(Pin(self._conf.c['sensor_pin'], Pin.IN))
        self._sensor_tick = self._conf.c['sensor_tick_length']
        
        print('Sensor set up')
        
    def report_values(self) -> None:
        """
        Both prints and uploads the sensor's values once each sensor_tick_length.
        """
        while True:
            value = self._sensor.read_u16()
            
            msg = f'Sensor value: {value}'
            
            print(msg)
            self._serv_client.publish(self._topic, msg)
            
            time.sleep(self._sensor_tick)
            
    def report_diff(self):
        """
        Both prints and uploads the sensor's differential values, i.e. the difference in
        value between two subsequent samples, once per sensor_tick_length.
        """
        old = 0
        while True:
            new = self._sensor.read_u16()
            
            msg = f'Sensor differential value: {new-old}'
            
            print(msg)
            self._serv_client.publish(self._topic, msg)
            
            old = new
            
            time.sleep(self._sensor_tick)