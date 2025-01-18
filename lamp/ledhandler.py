"""
Module containing class that handles tick-based control over Neopixel led strip or led ring.
Time between ticks are adjustable, and module handles quick switching between a 'fast' and a 'slow' setting.

Contains built-in color series (here called animations) and means for controlling the hardware accordingly,
as well as logic for choosing the proper one.

Colors and tick lengths are customizable.

For some reason, my build doesn't seem to have the build in neopixel library. Instead,
this module relies on the neopixel module from https://github.com/blaz-r/pi_pico_neopixel/tree/main
Credit to the contributors for excellent work.
"""

from math import exp
from colorsdatabase import *
from exceptions import IllegalSetupException

class LedHandler:
    """
    Class that handles the Neopixel led hardware.
    
    Attributes:
        fast_tick_length (float): Time between ticks while in fast mode (s).
        slow_tick_length (float): Time between ticks while in slow mode (s).
        current_tick_length (float): Time between ticks currently (slow, fast or custom) (s).
        active_duration (float): Time that the active mode should last (s).
        colors (dict): All colors as RGB tuples. Supported keys:
            - active: Only this unit is active.
            - friend_active: Only friend's unit is active.
            - both_active: Both this and friend's unit is active.
            - sleep: This unit has entered sleep mode.
            - friend_sleep: Friend's unit has entered sleep mode.
            - both_sleep: Both unit's has entered sleep mode.
    """

    #   MATHEMATICAL FUNCTIONS
    # Functions that return a normalized value as a function of time. 
    # Should be used as dim factors for animation methods.
    
    def _heartbeat_function(self, t: float) -> float:
        """
        Function that resembles a heartbeat. Function of time.
        
        Args:
            t (float): Time of evaluation (s).
        
        Returns:
            float: Function value.
        """
        
        t -= int(t/1.5)*1.5             #Time shift to within [0, 1.5)
        
        if t < 0.5:
            return exp(-100*(t-0.2)**2) + 0.75*exp(-100*(t-0.5)**2)
        else:
            return 0.75*exp(-7*(t-0.5)**1.8)

    def _decay_function(self, t: float) -> float:
        """
        Exponential decay. Will evaluate to < 1 for times longer than active_duration.
            
        Args:
            t (float): Time of evaluation (s).

        Returns:
            float: Function value.
        """
        
        return exp(-5.541*t/self.active_duration)
    
    def _spike_function(self, t: float) -> float:
        """
        Sharp spike.
        
        Args:
            t (float): Time of evaluation (s).

        Returns:
            float: Function value.
        """
        
        if t < 0.5:
            return exp(-20*(t-0.5)**2)
        elif t < 3:
            return exp(-1*(t-0.5)**2)
        else:
            return 0
    
    #   ANIMATION METHODS
    # Methods that takes (at least) time t as argument and returns the appropriate color at this time point.
    
    def _transition_animation(self, t: float, duration: float, c1: tuple, c2: tuple) -> tuple:
        """
        Animation that handles a smooth (linear) transition from one color to another.
        
        Args:
            t (float): Time of evaluation (s).
            duration (float): Duration of the complete transition (s).
            c1 (tuple): Color to transition from.
            c2 (tuple): Color to transition to.
        
        Limitations:
            - Method assumes that all pixels in the led strip starts with identical colors.
        """
        
        if self._leds.get_pixel(0) == c2 or t > duration:    # If transition is finished.
            self._is_transitioning = False
            return c2
        else:
            ci = tuple(int(a*(1-t/duration)+b*t/duration) for a, b in zip(c1, c2))
            return ci
    
    def _empty_animation(self, t:  any) -> None:
        """
        Does nothing. Code structure requires that self.animate is regularly called. 
        Other animation methods switches the 'animation' attribute to this when they are finished.

        Args:
            t (any): Originally time of evaluation, but doesn't really matter.
            
        Returns:
                None.
        """
        
        return None
    
    def _heartbeat_animation(self, t: float) -> tuple:
        """
        Handles the heartbeat animation.
        
        Args:
            t (float): Time of evaluation (s).
        
        Returns:
            tuple: Appropriate color at this time.
        """
        
        if self._is_transitioning:
            c1 = self._prev_c
            c2 = dim(self._heartbeat_function(t), self._current_c)
            return self._transition_animation(self._transition_time, 0.5, c1, c2)
        else:
            return dim(self._heartbeat_function(t), self._current_c)
    
    def _active_animation(self, t: float) -> tuple:
        """
        Handles the regular "active" animation (hand placed).
        
        Args:
            t (float): Time of evaluation (s).
        
        Returns:
            tuple: Appropriate color at this time.
        """
            
        if self._is_transitioning:
            c1 = self._prev_c
            c2 = dim(self._decay_function(t), self._current_c)
            return self._transition_animation(self._transition_time, 1, c1, c2)
        elif t > self.active_duration:
            self._animate = self._empty_animation
            return OFF
        else:
            return dim(self._decay_function(t), self._current_c)
    
    def _sleep_animation(self, t: float) -> tuple:
        """
        Handles the animation used when lamp is in sleep mode.
        
        Args:
            t (float): Time of evaluation (s).
        
        Returns:
            tuple: Appropriate color at this time.
        """
        if self._is_transitioning:
            c1 = self._prev_c
            c2 = dim(self._spike_function(t), self._current_c)
            return self._transition_animation(self._transition_time, 1, c1, c2)
        elif t > 3:
            self._animate = self._empty_animation
            return OFF
        else:
            return dim(self._spike_function(t), self._current_c)
    
    # Settings
    _leds = None
    fast_tick_length = -1.0
    slow_tick_length = -1.0
    active_duration = -1
    
    # State
    current_tick_length = -1.0  # Default: slow_tick_length
    _prev_c = None              # Previous color (of interest during a color transition)
    _current_c = None           # Current color at maximum brightness
    _is_transitioning = False   # Is the object currently transitioning from one color to another?
    _animate = None             # Current animation scheme
    _current_time = 0           # Current time. Resets after each state change
    _transition_time = 0        # How long the transition has lasted

    def __init__(self, leds):
        """
        Creates LedHandler object.
        
        Args:
            leds (Neopixel): Neopixel hardware.
        """
        self._leds = leds
        
        self._prev_c = OFF
        self._current_c = OFF
        self._animate = self._empty_animation
    
    def update_settings(self, settings: dict) -> None:
        """
        Update the handler's settings.
        Running verify_setup() afterwards is recommended.
        
        Recognized keys:
            fast_tick_length: Time between ticks in fast mode (s).
            slow_tick_length: Time between ticks in slow mode (s).
            active_duration: Time after activation that active mode should remain (s).
            current_tick_length: Either 'fast', 'slow' or custom value. Make sure it matches the
                frequency by which tick() is called though.
            
        Other parameters will be ignored.
        
        Returns:
            None
        """
        
        if 'led_fast_tick_length' in settings:
            self.fast_tick_length = settings['led_fast_tick_length']
            
        if 'led_slow_tick_length' in settings:
            self.slow_tick_length = settings['led_slow_tick_length']
            
        if 'active_duration' in settings:
            self.active_duration = settings['active_duration']
            
        if 'current_tick_length' in settings:
            if settings['current_tick_length'] == 'fast':
                self.current_tick_length = self.fast_tick_length
            elif settings['current_tick_length'] == 'slow':
                self.current_tick_length = self.slow_tick_length
            else:
                self.current_tick_length = settings['current_tick_length']
    
    def verify_setup(self) -> None:
        """
        Tries to detect if the object has been illegally set up.
        
        Raises:
            IllegalSetupException: Signals that the object is not properly set up.
        
        Returns:
            None
        """
        
        if self.slow_tick_length < 0:
            raise IllegalSetupException('Slow tick length must be set to a value > 0.')
        
        if self.fast_tick_length < 0:
            raise IllegalSetupException('Fast tick length must be set to a value > 0.')
        
        if self.current_tick_length < 0:
            self.current_tick_length = self.slow_tick_length
            
        if self.active_duration < 0:
            raise IllegalSetupException('Duration of active mode must be set to a value > 0.')
        
    def set_tick_length(self, speed) -> None:
        """
        Quick method for setting tick length.
        
        Args:
            speed (float or 'fast' or 'slow'): New time between ticks (s).
        """
        if speed == 'fast':
            self.current_tick_length = self.fast_tick_length
        elif speed == 'slow':
            self.current_tick_length = self.slow_tick_length
        else:
            self.current_tick_length = speed

    def tick(self) -> None:
        """
        Handler performs all of its duties.
        
        Returns:
            None    
        """
        
        next = self._animate(self._current_time)

        if next != None:
            self._leds.fill(next)
            self._leds.show()
        
        if not self._is_transitioning:
            self._current_time += self.current_tick_length
        else:
            self._transition_time += self.current_tick_length
        
    def set_animation(self, anim: str) -> None:
        """
        Set which animation should be active. It will start from its beginning.

        Args:
            anim (str): The animation ('active', 'holding' or 'sleep')
        """
        
        self._current_time = 0
        
        self._is_transitioning = True
        self._transition_time = 0
        self._prev_c = self._leds.get_pixel(0)
        
        if anim == 'active':
            self._animate = self._active_animation
        elif anim == 'holding':
            self._animate = self._heartbeat_animation
        elif anim == 'sleep':
            self._animate = self._sleep_animation
    
    def set_color(self, c: tuple):
        """
        Set which color the handler should transition to.

        Args:
            c (tuple): The new color.
        """
        self._prev_c = self._leds.get_pixel(0)
        self._is_transitioning = True
        self._transition_time = 0
        self._current_c = c