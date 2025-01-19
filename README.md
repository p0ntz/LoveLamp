# LoveLamp

## Description
This project allows a microcontroller to act as a friendship lamp over the MQTT protocol. The classic function of a friendship lamp is that two devices are connected, and activating one of them will activate the other as well. 

This was made specifically for use with the Raspberry PI pico W, with a NeoPixel RGB led strip as light source and a homemade touch sensor connected to the analog pins as activation system. 

I have called it the LoveLamp because it is made as a gift to my long distance girlfriend.

## Installation
1. Set up an MQTT broker and solder all hardware in place.
2. Flash your microcontroller with MicroPython. For raspberry PIs, more information can be found at https://www.raspberrypi.com/documentation/microcontrollers/micropython.html 

3. Clone the git repository:
   ```bash
   git clone https://github.com/p0ntz/LoveLamp.git
   ```
   or download it in some other way.

4. Install dependencies
    - For the lamp: 
        - Download source code from
        https://github.com/micropython/micropython-lib/blob/master/micropython/umqtt.simple/umqtt/simple.py

        - MicroPython's standard library is supposed to have a NeoPixel module. I, however, couldn't get it to work. Instead, the code is based on an external module, but could probably work with the standard library with minor modifications. If you do not want to go through the hassle of modifying anything, just download the source code from
        https://github.com/blaz-r/pi_pico_neopixel/blob/main/neopixel.py 

    - For the remote controller:
       ```bash
        pip install paho-mqtt
        ```

5. Fill out config.txt and, if you want to use remote control, controller_config.txt. See config_guide.txt for assistance.

6. Upload all contents of the lamp directory onto root of the microcontroller (using Thonny or some other software).

7. Disconnect the microcontroller from your computer and connect it to a power source. You are now running LoveLamp.

## Usage
### Normal operation
When both lamps are connected they will initially be in inactive mode. Activating the touch sensor on lamp A will activate it, meaning it will light up in the 'active_color' specified in the config file. Lamp B will as well. The color will slowly fade out over the 'active_duration' specified in the config file. If lamp B activates as well, both lamps will now glow in a mix of A's and B's active colors. The brightness will refresh.

If one or both users hold the touch sensor until it has remained active for the config's 'hold_command_threshold', both lamps will begin to flash in a manner resembling a heartbeat, until released. The color rules are the same as for the case of regular activation.

If the sensor of lamp A is activated twice within the 'sleep_command_window', meaning the sensor is touched, released and touched again, the lamp will enter sleep mode. It will activate lamp B as in the normal activation way, but with the color specified in 'sleep_color'. All incoming messages to lamp A will only be displayed with a short spike in the appropriate color. The purpose of this is to avoid the lamp activating while asleep, potentially waking or at least annoying the user. The lamp automatically enters inactive mode after 'sleep_duration' has expired. All activations of lamp B will take the color of lamp A's sleep color, telling the user of B that A is asleep. When both enters sleep mode, they will light up in a mix of both's sleep colors.

### Remote controller
The remote controller is command line tool that run on regular Python. It has a few features:
- *Manually sending state updates*. Thus allowing for simulation of the activity of another lamp.
- *Reading debug log*. When a lamp is placed in debug mode, it will publish updates to the MQTT broker. This can be viewed in real time here.
- *Changing configuration*. This makes changes to the lamp's config.txt file, which will take effect after next reboot.
- *Reboot*. Tells the lamp to do a hard reboot.

If some exception has occured, the lamp will not obey these commands. As of right now, the controller has no direct way of knowing if the lamp has acknowledged the command.

### Troubleshooting
The lamp tries to do some simple communication about the state of the system via the LEDs. Translation:
- *Blue glow* - The lamp is booting up other systems than network connections. This is usually very fast (< 1 second), so if this is glowing, something is likely wrong.
- *Orange glow* - The lamp is attempting to connect to WiFi and the broker server.
- *Green glow for 3 s* - Boot and connections successful.
- *Red flash* - Setup failed because some field in the config.txt has illegal values.
- *Orange flash* - Connectivity problems encountered. The lamp will flash a specific number of times, switch off for a longer period and then repeat the sequence. The number of flashes correspond to the error code:
        1. Other error.
        2. Connection to the local WiFi network failed.
        3. Internet connection failed. (It has failed to ping google.com).
        4. Connection to broker server failed.
- *Yellow flash* - Some other error has occured.

By connecting the lamp to e.g. Thonny and running main from there, the console messages will be visible, possibly containing more information. 

If further troubleshooting is necessary, the lamp can be placed in debug mode by modifying a flag in main.py. The lamp will then publish diagnostic information to the broker which can be easily viewed by the remote controller.

If the lamp fails at connecting to the primary wifi at boot, it will attempt the backup. It will then proceed normal operation, but use this backup until next reboot. If it disconnects sometime later than boot, it will display the proper error code and attempt reconnecting every 5 minutes.

Worth mentioning is that it might be wise to specify a backup wifi connection. If the lamp needs to switch to a new wifi network, you can open a mobile hotspot with credentials matching that of the backup specified in config.txt and use the controller to edit the primary wifi settings.

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgements
- simple umqtt from micropython-lib - The MQTT client that the lamp uses. https://github.com/micropython/micropython-lib/blob/master/micropython/umqtt.simple/umqtt/simple.py

- pi-pico-neopixel - NeoPixel drivers for the lamp. https://github.com/blaz-r/pi_pico_neopixel/blob/main/neopixel.py

- paho-mqtt - MQTT Client that the remote controller uses. https://pypi.org/project/paho-mqtt/