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
    lamp.wireless_setup()
    
    uc.boot_succ()
    
    lamp.run()
        
except IllegalSetupException as e:
   print(e)
   uc.setup_err()
    
except NetworkException as e:
   print(e)
   uc.conn_err(e.errorcode)
    
except Exception as e:
    print(e)
    uc.other_err()