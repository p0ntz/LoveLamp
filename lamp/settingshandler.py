"""
Module containing a class that can import settings from the config.txt file. 
The settings are stored in a dict which is accessible to the rest of the
program. The class can also modify said config file after server command.
"""

import colorsdatabase

class SettingsHandler:
    """
    Class that handles configuration.
    
    Attributes:
        c (dict): Dictionary containing all configuration parameters.
    
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
    
    def _parse_value(self, setting, value):
        """
        Converts a settings value into a suitable datatype.

        Args:
            setting (str): Name of setting.
            value (str): String representing value.

        Returns:
            any: Parsed value.
        """
        
        try:                        # Parse numeric values
            value = float(value)
            
            if value % 1 == 0:      # Parse to int if possible
                value = int(value)
        except (ValueError, TypeError):
            pass
        
        if setting == 'active_color' or setting == 'sleep_color':   # If setting is a colorsetting,
            predefined_colors = dir(colorsdatabase)                 # format into color tuple
            
            if value in predefined_colors:
                value = getattr(colorsdatabase, value)
            else:
                value = value.replace('(', '').replace(')', '').replace(' ', '')
                temp = value.split(',')
                value = tuple(int(v) for v in temp)
        
        if setting == 'connect_to_internet':
            if value.lower() == 'true':
                value = True
            else:
                value = False
        
        if value == '':     # Empty entry
            value = None
        
        return value