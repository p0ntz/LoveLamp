"""
Communication with the user regarding the state of the lamp via the leds.
Requires a config.txt file to supply led pin number and number of leds in neopixel,
and the module colorsdatabase.
"""

from colorsdatabase import *
from neopixel import Neopixel
from time import sleep

class UserCom:
    
    # Used colors
    _col_boot = BLUE
    _col_conn = ORANGE
    _col_boot_success = GREEN
    _col_setup_err = RED
    _col_other_err = YELLOW
    
    _led = None
    
    def __init__(self):
        """
        Create UserCom object.
        """
        
        self.led_setup()
        
    def led_setup(self):
        """
        Set up led.
        """
        
        led_pin = -1
        led_num = -1
        
        # Finding correct pin and number of leds
        with open('config.txt', 'r') as file:
    
            config = file.readlines()
            
            for line in config:
                if line.strip() and not line.startswith('#'):   # Skip comments and empty rows
                    
                    setting, value = line.split('=')
                    setting = setting.strip()
                    
                    if setting == 'led_pin':
                        value = value.split('#')[0].strip()     # Trim away comments and whitespaces
                        led_pin = int(value)
                    if setting == 'num_leds':
                        value = value.split('#')[0].strip()
                        led_num = int(value)
                    if led_pin != -1 and led_num != -1:
                        break
        
        self._led = Neopixel(led_num, 0, led_pin, "GRB")
        
    def booting(self):
        """
        Device is booting. 
        
        Stationary boot color.
        """
        
        self._led.fill(self._col_boot)
        self._led.show()
    
    def connecting(self):
        """
        Device is connecting to networks.
        
        Stationary connection color.
        """
        
        self._led.fill(self._col_conn)
        self._led.show()
        
    def boot_succ(self):
        """
        Boot has been successful.
        
        Boot success color visible for 3 seconds before moving on.
        """
        
        self._led.fill(self._col_boot_success)
        self._led.show()
        
        sleep(3)
        
        self._led.fill(OFF)
        self._led.show()
        
    def setup_err(self):
        """
        A setup error has occured (erroneous config).
        
        Setup error color blinks indefinitely.
        """
        
        while (True):
            self._led.fill(self._col_setup_err)
            self._led.show()
            
            sleep(1.5)
            
            self._led.fill(OFF)
            self._led.show()
            
            sleep(0.5)
            
    def conn_err(self, code: int, duration: int = 31536000):
        """
        A connection error has occured.
        
        Connecting color blinking as many times as the error code, 3 seconds switched off, repeat.

        Args:
            code (int): Error code of the connection error.
            duration (int): Seconds that the error should be displayed (inexact). Default is one year.
        """
             
        if duration != 0:
            looptime = 1.5*code + 2    # Time required to run one loop
            numloops = int(duration/looptime)   # Number of loops that should run
        
            for i in range(numloops):
                for j in range(code):
                    self._led.fill(self._col_conn)
                    self._led.show()
                    
                    sleep(1)
                    
                    self._led.fill(OFF)
                    self._led.show()
                    
                    sleep(0.5)
                    
                sleep(2)
        
    def other_err(self):
        """
        Some other error has occured.
        
        Other error color blinking indefinitely.
        """
        
        while (True):
            self._led.fill(self._col_other_err)
            self._led.show()
            
            sleep(2)
            
            self._led.fill(OFF)
            self._led.show()
            
            sleep(1)