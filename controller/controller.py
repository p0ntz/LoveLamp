"""
Module that allows for some remote control of the lamp.
"""

import time
import paho.mqtt.client as mqtt

class Controller:
    """
    Controller that does logic and communicates with the broker.
    """
    
    server_addr = None
    server_port = None
    ssl = None
    server_username = None
    server_pass = None
    
    target = None
    target_friend = None

    client = None
    
    def __init__(self):
        """
        Initializes object.
        """
        pass

    def import_config(self):
        """
        Imports configuration parameters from controller_config.txt.
        """
        with open('controller_config.txt', 'r') as file:
                
                config = file.readlines()
                
                for line in config:
                    if line.strip() and not line.startswith('#'):   # Skip comments and empty rows
                        setting, value = line.split('=')
                        
                        setting = setting.strip()
                        value = value.split('#')[0].strip()     # Trim away comments and whitespaces
                        
                        setattr(self, setting, value)
                        
        self.server_port = int(self.server_port)

    def connect(self):
        """
        Connects to broker server.
        """
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=self.server_username+'-controller')
        self.client.username_pw_set(self.server_username, self.server_pass)
        self.client.connect(self.server_addr, self.server_port)
        
    def disconnect(self):
        """
        Disconnects from broker server.
        """
        self.client.disconnect()
        
    def send_state_update(self, state: str, col: str):
        """
        Sends a state update to a lamp, like the lamp's friend usually does.

        Args:
            state (str): Either 'inactive', 'active', 'holding' or 'sleep'
            col (str): Color tuple formatted as (r,g,b), with values from 0 to 255 (inclusive)
        """
        topic = None
        
        if self.target_friend < self.target:
            topic = f'{self.target_friend}-{self.target}/{self.target}'
        else:
            topic = f'{self.target}-{self.target_friend}/{self.target}'
            
        self.client.publish(topic, f'{state}:{col}', qos = 1)
        
    def send_config_update(self, setting: str, value: str):
        """
        Tells the lamp to update its config.txt file.

        Args:
            setting (str): Name of setting
            value (str): New value of setting
        """
        topic = f'{self.target}/control'
        msg = f'{setting}:{value}'
        self.client.publish(topic, msg, qos = 1)
        
    def reboot(self):
        """
        Tell lamp to reboot.
        """
        topic = f'{self.target}/control'
        self.client.publish(topic, 'reboot', qos = 1)
        
    def sub_debug(self, callback):
        """
        Subscribe to the debug topic of the lamp.

        Args:
            callback (function): Callback function used for MQTT messages.
        """
        self.client.on_message = callback
        
        topic = f'{self.target}/debug'
        self.client.subscribe(topic, qos = 2)
        
    def desub_debug(self):
        """
        Unsubscribe from the debug topic.
        """
        topic = f'{self.target}/debug'
        self.client.unsubscribe(topic)
        
    def msg_stream(self):
        """
        Enters an infinite loop only interrupted by processing of incoming messages.
        """
        self.client.loop_forever()
    
############################################################################################

class Application:
    """
    Allows command line interaction with the controller.
    """
    
    def __init__(self):
        """
        Initializes the object.
        """
        self._cont = Controller()
        self._cont.import_config()
        
        self.actions = {'Manual control'    : self.manual_control,
                        'Update settings'   : self.update_settings,
                        'View debug log'    : self.view_debug_log,
                        'Reboot'            : self.reboot,
                        'Set target'        : self.set_target,
                        'Set target\'s friend' : self.set_friend,
                        'Exit'              : self.exit}

    def print_welc_msg(self):
        """
        Prints the welcome screen.
        """
        print('\n\n####################################')
        print('#            Welcome to            #')
        print('#                                  #')
        print('#             LOVELAMP             #')
        print('#            controller            #')
        print('#                                  #')
        print('####################################\n')
    
    def connect(self):
        """
        Connects to the broker.
        """
        print('Connecting to broker...', end = '', flush = True)
        self._cont.connect()
        print(' SUCCESS!')
        
    def main_menu(self):
        """
        Views the main menu with all possible actions.
        """
        print('\n#### MAIN MENU ####')
        print('Choose action:\n')
        
        options = list(self.actions.keys())
        
        for i, option in enumerate(options):
            print(f'[{i}]  {option}')
            
        print('')
        
        choice = options[int(input())]
        
        self.actions[choice]()
        
    def manual_control(self):
        """
        Uses the manual_control mode of the controller.
        """
        if self._cont.target_friend == None:
            self.set_friend()

        print('\n# Manual control: Send state updates to the target lamp.')
        print('#')
        print('# State: choose between \'active\', \'holding\', \'sleep\', \'inactive\'')
        print('# Color: a tuple formatted as (r,g,b) with values in [0, 255]')
        print('#')
        print('# Exit to main menu via KeyboardInterrupt (Ctrl-C)\n')
        
        try:
            while True:
                print('state:  ', end='', flush=True)
                state = input()
                
                print('color:  ', end='', flush=True)
                color = input()
                
                self._cont.send_state_update(state, color)
                
                print('\nCommand sent\n')
        except KeyboardInterrupt:
            pass
    
    def update_settings(self):
        """
        Update lamp config.
        """
        print('\n# Update settings: Update the config file of the target lamp.')
        print('#')
        print('# Updates take effect after reboot.')
        print('#')
        print('# Setting: enter exactly as it is called in the config file')
        print('# New value: enter the new value, or \'default\' to overwrite with default')
        print('#')
        print('# Exit to main menu via KeyboardInterrupt (Ctrl-C)\n')
        
        try:
            while True:
                print('setting:  ', end='', flush=True)
                setting = input()
                
                print('new value:  ', end='', flush=True)
                value = input()
                
                self._cont.send_config_update(setting, value)
                
                print('\nCommand sent\n')

        except KeyboardInterrupt:
            pass
    
    def view_debug_log(self):
        """
        View the debug messages when lamp is placed in debug mode.
        """
        print('\n# View debug log: See debug messages from lamp in debug mode.')
        print('#')
        print('# Exit to main menu via KeyboardInterrupt (Ctrl-C)\n')
        
        try:
            self._cont.sub_debug(self._print_log)
            self._cont.msg_stream()
        except KeyboardInterrupt:
            self._cont.desub_debug()
        
    def _print_log(self, client, userdata, msg):
        """
        Callback function that prints the incoming message.
        """
        print(msg.payload.decode('utf-8'))
    
    def reboot(self):
        """
        Reboot the lamp.
        """
        self._cont.reboot()
        print('\n Reboot command sent')
    
    def exit(self):
        """
        Disconnect from broker and close application.
        """
        self._cont.disconnect()
        exit(0)
    
    def set_target(self):
        """
        Set which lamp should be controlled.
        """
        print('Enter username of target lamp:  ', end='', flush=True)
        self._cont.target = input()
    
    def set_friend(self):
        """
        Set the name of the lamp's friend.
        
        Necessary because communication is made via the topic name-friend_name/name.
        """
        print('Enter username of friend\'s lamp:  ', end='', flush=True)
        self._cont.target_friend = input()
        

if __name__ == '__main__':
    app = Application()
    app.print_welc_msg()
    app.connect()
    app.set_target()
    
    while True:
        app.main_menu()