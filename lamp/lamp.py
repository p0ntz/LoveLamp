"""
Module containing the Lamp class which handles all operations of the friendship lamp.
"""

from machine import Pin, ADC, reset
from neopixel import Neopixel
from sensorhandler import SensorHandler
from ledhandler import LedHandler
from settingshandler import SettingsHandler
from serverhandler import ServerHandler
from colorsdatabase import *
from utils import gcd
from colorsdatabase import color_mix
import time

class Lamp:
    """
    Class that handles the friendship lamp's operation.
    """
    
    # SUPPORTING CLASSES
    _conf = None
    _sensor = None
    _led = None
    _server_client = None
    
    #   STATE
    # Ticks
    _sensor_tick_i = 0
    _led_tick_i = 0
    _update_tick_i = 0
    _tick_counter = 0
    _fast_led_timeout = 0
    _state_timeout = 0
    _led_tick = None
    _main_tick = -1
    
    # States
    _this_state = 'inactive'
    _friend_state = 'inactive'
    _friend_col = None
    
    # Update flags
    _anim_upd_sent = True
    _col_upd_sent = True
    _update_sent_server = True
    
    def __init__(self):
        """
        Creates the lamp object.
        """
        pass
    
    def settings_setup(self) -> None:
        """
        Parses configuration file content into memory.
        
        Returns:
            None
        """
        
        self._conf = SettingsHandler()
        self._conf.import_config()
    
    def wireless_setup(self, use_backup = False) -> None:
        """
        Sets up server client and connects to broker.
        
        Returns:
            None
        """
        
        self._server_client = ServerHandler()
        self._server_client.update_settings(self._conf.c)
        self._server_client.verify_setup()
        self._server_client.connect(use_backup)
    
    def sensor_setup(self) -> None:
        """
        Initializes the sensor object. 
        
        Raises:
            IllegalSetupException: Signals that the sensor couldn't be set up properly.
        
        Returns:
            None
        """
        
        sensor_hardware = ADC(Pin(self._conf.c['sensor_pin'], Pin.IN))
        self._sensor = SensorHandler(sensor_hardware)
        self._sensor.update_settings(self._conf.c)
        self._sensor.verify_setup()
    
    def led_setup(self) -> None:
        """
        Initializes the led object. 
        
        Raises:
            IllegalSetupException: Signals that the led couldn't be set up properly.
        
        Returns:
            None
        """
        
        leds_hardware = Neopixel(self._conf.c['num_leds'], 0, self._conf.c['led_pin'], "GRB")
        self._led = LedHandler(leds_hardware)
        self._led.update_settings(self._conf.c)
        self._led.verify_setup()
        self._led_tick = self._conf.c['led_slow_tick_length']
        
    def _update_tick_intervals(self) -> None:
        """
        Calculates a main tick length as the greates common divider of the component's tick length
        and converts the component's time intervals into tick intervals.
        
        Returns:
            None
        """
        
        self._main_tick = gcd(self._led_tick, 
            self._conf.c['sensor_tick_length'], 
            self._conf.c['message_check_interval'])
        
        self._sensor_tick_i = self._conf.c['sensor_tick_length']/self._main_tick
        self._led_tick_i = self._led_tick/self._main_tick
        self._update_tick_i = self._conf.c['message_check_interval']/self._main_tick
    
    def _do_sensor_tick(self) -> None:
        """
        Does sensor tick and handles any response from the sensor object.
        
        Returns:
            None
        """
        
        reading = self._sensor.tick()
        
        if reading != None:
            self._this_state = reading
            self._anim_upd_sent = False
            self._col_upd_sent = False
            self._update_sent_server = False
            
            # Set proper state timeout
            if reading == 'active':
                self._state_timeout = int(self._conf.c['active_duration'] / self._conf.c['sensor_tick_length'])
            elif reading == 'sleep':
                self._state_timeout = int(self._conf.c['sleep_duration'] / self._conf.c['sensor_tick_length'])
        elif self._this_state != 'holding':     # Count down state timeout
            self._state_timeout -= 1
        
        # State has expired
        if self._state_timeout == 0:
            self._this_state = 'inactive'
            self._col_upd_sent = False
            self._update_sent_server = False
    
    def _do_led_tick(self) -> None:
        """
        Updates the current lamp state if neccessary and does the led tick.
        
        Returns:
            None
        """

        if not self._anim_upd_sent:        # Available animation update to send
            self._anim_upd_sent = True
            
            self._led.set_animation(self._compute_anim())
            
            self._led.set_tick_length('fast')    # Led is placed in fast mode
            self._led_tick = self._conf.c['led_fast_tick_length']
            self._update_tick_intervals()
            self._fast_led_timeout = int(self._conf.c['active_duration']*0.3/self._led_tick)
            
        if not self._col_upd_sent:          # Available color update to send
            self._col_upd_sent = True
            self._led.set_color(self._compute_col())
        
        if self._fast_led_timeout == 0:  # Led is placed in slow mode
            self._led.set_tick_length('slow')
            self._led_tick = self._conf.c['led_slow_tick_length']
            self._update_tick_intervals()
        
        if self._this_state != 'holding' and self._friend_state != 'holding':
            self._fast_led_timeout -= 1
        
        self._led.tick()
        
    def _compute_anim(self):
        """
        Computes which animation the LedHandler should use.

        Returns:
            str: Appropriate animation (active, holding or sleep)
        """
        
        if self._this_state == 'sleep':
            return 'sleep'
        elif self._this_state == 'holding' or self._friend_state == 'holding':
            return 'holding'
        elif self._this_state == 'active' or self._friend_state == 'active':
            return 'active'
        elif self._friend_state == 'sleep':
            return 'active'
        
    def _compute_col(self):
        """
        Computes which color the LedHandler should use.

        Returns:
            tuple: Appropriate color
        """
        ts = self._this_state
        fs = self._friend_state
        
        if ts in ['active', 'holding']:
            if fs in ['active', 'holding']:
                return color_mix(self._conf.c['active_color'], self._friend_col)
            elif fs == 'sleep':
                return self._friend_col
            elif fs == 'inactive':
                return self._conf.c['active_color']
        elif ts == 'sleep':
            if fs == 'sleep':
                return color_mix(self._conf.c['sleep_color'], self._friend_col)
            elif fs in ['active', 'holding']:
                return self._friend_col
            elif fs == 'inactive':
                return self._conf.c['sleep_color']
        elif ts == 'inactive':
            if fs != 'inactive':
                return self._friend_col
            else:
                return (0, 0, 0)
        raise ValueError('Invalid state')
        
    def _do_message_check(self) -> None:
        """
        Checks for messages from server and handles any response.
        
        Returns:
            None
        """
        if not self._update_sent_server:
            self._update_sent_server = True
            
            c = None
            if self._this_state in ['holding', 'active']:
                c = self._conf.c['active_color']
            elif self._this_state == 'sleep':
                c = self._conf.c['sleep_color']
            elif self._this_state == 'inactive':
                c = (0, 0, 0)
                
            self._server_client.send_state(self._this_state, c)
        
        resp = self._server_client.check_msg()
        
        if resp != None:
        
            if resp['type'] == 'friend_update':
                self._friend_col = resp['color']
                self._friend_state = resp['state']
                
                self._col_upd_sent = False
                
                if resp['state'] != 'inactive':
                    self._anim_upd_sent = False
            
            elif resp['type'] == 'reboot':
                reset()
            
            elif resp['type'] == 'update_config':
                self._conf.update_config(resp['changes'])
    
    def run(self) -> None:
        """
        Starts lamp operation. Proceeds until lamp is switched off or an error occurs.
        
        Returns:
            None
        """
        
        self._update_tick_intervals()
        
        while True:
            start_time = time.time_ns()

            if self._tick_counter % self._sensor_tick_i == 0:
                self._do_sensor_tick()

            if self._tick_counter % self._update_tick_i == 0:
                self._do_message_check()

            if self._tick_counter % self._led_tick_i == 0:
                self._do_led_tick()
                
            self._tick_counter += 1
            
            # Sleeping (clock drift proof)
            now = time.time_ns()
            sleeptime = self._main_tick - (now - start_time) / 1e9
                
            time.sleep(sleeptime)