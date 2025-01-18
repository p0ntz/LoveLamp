"""
Main script that runs the lamp.
"""

from lamp import Lamp
from exceptions import *
from user_com import UserCom
import debuggers

debug_target = None     # Valid options: 'sensor'
debug_mode = None       # Valid options: 'report_values', 'report_diff'

# Entering debug mode if specified
if debug_target == 'sensor':
    debugger = debuggers.sensor_debugger()
    
    if debug_mode == 'report_values':
        debugger.report_values()
    elif debug_mode == 'report_diff':
        debugger.report_diff()
        
# Normal operation

uc = UserCom()
uc.booting()

try:
    lamp = Lamp()
    
    lamp.settings_setup()
    lamp.sensor_setup()
    lamp.led_setup()
    
    uc.connecting()

    using_backup = False
    
    try:
        lamp.wireless_setup()
    except NetworkException as e:
        using_backup = True
    
    if using_backup:
        lamp.wireless_setup(use_backup = True)
    
    uc.boot_succ()
    
    while True:
        try:
            lamp.run()
        except NetworkException as e:
            print(e)
            uc.conn_err(e.errorcode, 300)   # Reattempt in 5 minutes
            uc.connecting()
            
            while True:     # Reconnect loop
                try:
                    lamp.wireless_setup(use_backup=using_backup)
                    uc.boot_succ()
                    break
                except NetworkException as e2:
                    print(e2)
                    uc.conn_err(e2.errorcode, 300)   # Reattempt in 5 minutes
                    uc.connecting()
        
except IllegalSetupException as e:
   print(e)
   uc.setup_err()
    
except NetworkException as e:   # This code is likely dead
   print(e)
   uc.conn_err(e.errorcode, 31536000)  # One year
    
except Exception as e:
    print(e)
    uc.other_err()