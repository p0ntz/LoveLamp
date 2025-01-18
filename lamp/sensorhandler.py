"""
Module containing class that handles tick-based control over a touch sensor.

Able to detect when a user has placed or removed their hand from the sensor
based on the difference of two subsequent samples. Also implements logic for
detecting when user is holding their hand on the sensor and when it has been
placed twice within a short interval.

Sensitivity is adjustable for detection of hand having been placed or removed
as well as time window of detecting double placements and threshold before a
placed hand is to be considered as a holding hand.
"""

from machine import ADC
from exceptions import IllegalSetupException

class SensorHandler:
    """
    Class that handles the sensor hardware.
    
    Attributes:
        tick_length (float or int): Time between ticks in seconds.
        placed_sensitivity (int): Difference in sensor value between ticks that would trigger detection of a placed hand
        removed_sensitivity (int): Difference is sensor value between ticks that would trigger detection of a removed hand
        sleep_window (int): Max number of ticks between two hand placements that would activate sleep mode
        hold_threshold (int): Number of ticks of subsequent hand placement that would activate hold mode
    
    Methods:
        update_settings(**settings): Updates settings.
        verify_setup(): Verifies that the object is set up properly.
        tick(): Does the sensor's main operation.
        
    Notes:
        - placed_- and removed_sensitivity are detection threshold for changes in sensor hardware value
          between ticks. If tick_length is changed, these should therefore change as well. For too short
          tick lengths, performance may be poor.
    """
    
    # Settings
    _sensor = None
    tick_length = -1            # In seconds
    placed_sensitivity = -1
    removed_sensitivity = 1
    sleep_window = -1           # In ticks
    hold_threshold = -1         # In ticks
    
    # State
    _prev = 0                   # Previous sample
    _update = None              # New state just detected by sensor
    _is_hand_placed = False
    _is_holding = False
    _hand_placed_duration = 0   # In ticks
    _since_placed = -1           # Ticks since hand was last placed (if not currently placed)
    
    def __init__(self, sensor: ADC):
        """
        Creates SensorHandler object.
        
        Args:
            sensor (ADC): machine.ADC analog input pin object.
        """
        self._sensor = sensor
    
    def update_settings(self, settings: dict) -> None:
        """
        Changes the handler's settings. Running verify_setup() afterwards is recommended.
        
        Recognized keys:
            sensor_tick_length: Time between ticks in seconds
            sensor_placed_sensitivity: Hand placed detection sensitivity
            sensor_removed_sensitivity: Hand removed detection sensitivity
            sleep_command_window: Time interval in which a hand twice placed will trigger sleep mode in seconds
            hold_command_threshold: Time a hand must be placed before triggering hold mode.
        
        Other parameters will be ignored.
        
        Returns:
            None
        """
        if 'sensor_tick_length' in settings:
            self.tick_length = settings['sensor_tick_length']
        
        if 'sensor_placed_sensitivity' in settings:
            self.placed_sensitivity = settings['sensor_placed_sensitivity']
        
        if 'sensor_removed_sensitivity' in settings:
            self.removed_sensitivity = settings['sensor_removed_sensitivity']
        
        if 'sleep_command_window' in settings:
            self.sleep_window = settings['sleep_command_window'] / self.tick_length
            self._since_placed = self.sleep_window
        
        if 'hold_command_threshold' in settings:
            self.hold_threshold = settings['hold_command_threshold'] / self.tick_length
    
    def verify_setup(self) -> None:
        """
        Tries to detect if the object has been illegally set up.
        
        Raises:
            IllegalSetupException: Signals that the object is not properly set up.
        
        Returns:
            None
        """
        
        if self.tick_length <= 0:
            raise IllegalSetupException('Tick length must be set to a value > 0.')
        
        if self.placed_sensitivity < 1 or self.placed_sensitivity > 65535:
            raise IllegalSetupException('Sensor placed sensitivitiy must be in [1, 65535]')
        
        if self.removed_sensitivity > -1 or self.removed_sensitivity < -65535:
            raise IllegalSetupException('Sensor removed sensitivity must be in [-65535, -1]')
        
        if self.sleep_window < 1 or self.sleep_window % 1 != 0:
            raise IllegalSetupException('Sleep command window must be divisible by tick length.')
        
        if self.hold_threshold < 1 or self.hold_threshold % 1 != 0:
            raise IllegalSetupException('Hold command threshold must be divisible by tick length.')
    
    def tick(self):
        """
        Handler performs all of its duties.

        Returns:
            None or str: Of nothing of interest has happened, it returns None. Otherwise it will return
            either 'active', 'sleep' or 'holding'.
        """
        
        if self._is_hand_placed:
            self._hand_placed_duration += 1
        else:
            self._since_placed += 1
        
        new = self._sensor.read_u16()
        
        if new - self._prev > self.placed_sensitivity and not self._is_hand_placed: # Filters out incorrect duplicate placement detections
            self._is_hand_placed = True
            
            if self._since_placed < self.sleep_window:
                self._update = 'sleep'
            else: 
                self._update = 'active'
                
            self._since_placed = 0
            
        elif new - self._prev < self.removed_sensitivity:
            self._is_hand_placed = False
            self._hand_placed_duration = 0
            
            if self._is_holding:    #If user was holding, sensor drops into active state.
                self._is_holding = False
                self._update = 'active'
        
        if self._hand_placed_duration == self.hold_threshold:
            self._is_holding = True
            self._update = 'holding'
            
        self._prev = new
        
        result = self._update
        self._update = None
        
        return result