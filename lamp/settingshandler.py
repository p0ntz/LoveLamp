"""
Module containing a class that can import settings from the config.txt file. 
The settings are stored in a dict which is accessible to the rest of the
program. The class can also modify said config file after server command.
"""

import colorsdatabase
from exceptions import IllegalSetupException

TYPES = {
    'led_pin'       : int,
    'num_leds'      : int,
    'sensor_pin'    : int,
    
    'name'          : str,
    'wifi_ssid'     : str,
    'wifi_pass'     : str,
    'server_addr'   : str,
    'server_port'   : int,
    'ssl'           : str,
    'server_pass'   : str,
    'backup_wifi_ssid'      : str,
    'backup_wifi_pass'      : str,
    'connect_to_internet'   : bool,
    'timeout'               : int,
    'ping_interval'         : int,
    'dropped_ping_limit'    : int,
    
    'message_check_interval'    : float,
    'sensor_tick_length'        : float,
    'led_fast_tick_length'      : float,
    'led_slow_tick_length'      : float,
    'sensor_placed_sensitivity' : int,
    'sensor_removed_sensitivity': int,
    
    'friend_name'       : str,
    'active_color'      : 'color tuple',
    'sleep_color'       : 'color tuple',
    'active_duration'   : int,
    'sleep_duration'    : int,
    'sleep_command_window'      : int,
    'hold_command_threshold'    : int
    }

class SettingsHandler:
    """
    Class that handles configuration.
    
    Attributes:
        c (dict): Dictionary containing all configuration parameters.
        types (dict): Dictionary containing the proper datatype of the parameter names.
    
    Methods:
        import_config(): Imports configuration fields into dict c.
        update_config(settings**): Overwrites relevant fields in configuration file.
    """
    
    # Config parameters
    c = dict()
    
    def __init__(self):
        """
        Creates SettingsHandler object.
        """
        
        pass
    
    def import_config(self) -> None:
        """
        Parses config.txt file in same directory as this module and updates c attribute accordingly.
        
        Returns:
            None
        """
        
        with open('config.txt', 'r') as file:
            
            config = file.readlines()
            
            for line in config:
                if line.strip() and not line.startswith('#'):   # Skip comments and empty rows
                    setting, value = self._format(line)
                    if value != None:
                        self.c[setting] = value

    def update_config(self, update) -> None:
        """
        Overwrites config file accordingly. Requires reboot for new values to take effect.

        Args:
            settings (dict): Dict containing one change.
        
        Some settings can be assigned the string 'default' which overwrites the value with its default.
        
        Returns:
            None
        """
        
        with open('config.txt', 'r') as file:
        
            lines = file.readlines()
                
            setting = update['setting']
            value = str(update['value'])
            
            found = False
            
            for i, line in enumerate(lines):        # Iterate over config file
                if line.strip() and not line.startswith('#'):       # Skip comments and empty lines
                    setting_name, rest = line.split('=')
                    setting_name = setting_name.strip()
                    
                    if setting_name == setting:     # If there is a match
                        
                        comment = None
                        
                        try:        # Extract comment from line (if present)
                            _, comment = rest.split('#')
                        except ValueError:
                            pass
                        
                        if value == 'default':
                            lines[i] = self._find_default(setting_name)
                        else:
                            lines[i] = f"{setting_name} = {value}"
                            if comment != None:                         # Add comment if present
                                lines[i] += '\t\t\t#' + comment
                            
                        lines[i] += '\n'
                            
                        found = True
                        break
            
            if not found:
                raise ValueError('Unknown configuration parameter.')
        
            with open('config.txt', 'w') as wfile:      # Overwrite all lines into updated version
                for line in lines:
                    wfile.write(line)
    
    def _find_default(self, setting: str):
        """
        Parses config_default.txt and returns entire line.

        Args:
            setting (str): Name of configuration field to search for.

        Raises:
            ValueError: If setting cannot be found.

        Returns:
            any: Value of setting.
        """
        
        with open('config_default.txt', 'r') as file:
            default_lines = file.readlines()
            
            for line in default_lines:
                if line.strip() and not line.startswith('#'):   #Skip empty lines and comments
                        file_setting, value = line.split('=')
                        file_setting = file_setting.strip()
                        
                        if file_setting == setting:
                            return line
            
            raise ValueError('Unknown configuration parameter.')
    
    def _format(self, line: str):
        """
        Parses line in config file, returns setting name and 
        setting value parsed into suitable datatype.

        Args:
            line (str): A line in config.txt.

        Returns:
            str, any: Name of setting in line and its value.
        """
        
        setting, value = line.split('=')
                    
        setting = setting.strip()
        value = value.split('#')[0].strip()     # Trim away comments and whitespaces
        
        value = self._parse_value(setting, value)
        
        return setting, value
    
    #TODO fix this bad boy and use the new constant types
    # make sure it throws an illegalsetup error if the config field is unknown.
    def _parse_value(self, setting, value):
        """
        Converts a settings value into a suitable datatype.

        Args:
            setting (str): Name of setting.
            value (str): String representing value.

        Returns:
            any: Parsed value.
        """
        
        if setting not in TYPES:
            raise IllegalSetupException(f"Settingshandler does not recognize setting {setting}")
        
        if value == "":
            value = None
        
        elif TYPES[setting] == int:
            value = int(value)
            
        elif TYPES[setting] == float:
            value = float(value)
        
        elif TYPES[setting] == 'color tuple':
            predefined_colors = dir(colorsdatabase)                 # format into color tuple
            
            if value in predefined_colors:
                value = getattr(colorsdatabase, value)
            else:
                value = value.replace('(', '').replace(')', '').replace(' ', '')
                temp = value.split(',')
                value = tuple(int(v) for v in temp)
                
        elif TYPES[setting] == bool:
            if value.lower() == 'true':
                value = True
            else:
                value = False
            
        elif TYPES[setting] == str:
            pass
        
        else:
            raise NotImplementedError("The expected datatype cannot be parsed by _parse_value()")
        
        return value