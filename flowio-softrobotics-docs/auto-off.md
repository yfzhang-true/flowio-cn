# Auto Power OFF

> Source: https://www.softrobotics.io/auto-off

Another unique feature of FlowIO is the ability to power itself off and draw quiescent current of only 0.07mA, which is so tiny that the shelf life is limited only by the self-discharge of the LiPo battery itself. 

FlowIO has a built-in power-off timer, that by default is set to 5 minutes of inactivity. If you perform any action that involves either the valves, the pumps, or a Bluetooth connect / disconnect event, the timer will reset. The timer is running regardless of whether the system is in an actuated or idle state; it is only change of state that resets the timer. This implementation choice was made for safety reasons to ensure that the system will power off even if it has been forgotten in an actuated state. 

However, as the user, you have the option to change the duration of the auto-off timer or even to disable it completely. You can do this directly for the GUI or by changing the embedded code. 

The GUI gives you the option to change the timer value to anything between 1 and 5 minutes, or to disable the Auto-OFF feature. However, the changes you make from the GUI last only until you power-cycle the device, at which point the auto-off timer will reset back to 5 minutes. The option to change the Auto-Off timer setting is located on the left-hand-side of the GUI, right besides the power button.

You can make the changes persistent by changing the hardcoded value in the firmware to something else, or by disabling the Auto-OFF timer completely. Making this firmware change requires that you connect the device to your computer with a USB cable to flash the modified firmware.

Pin 13 (the red LED pin) is used for powering off the board. If you raise this pin to HIGH in the code, that will power the board off. This means that you should be careful not to write some code that uses pin 13 or the RED led for any other purpose, because as soon as you raise that pin to HIGH, FlowIO will shut down. But suppose you accidentally upload some code that on startup causes pin 13 to go HIGH. This would mean that as soon as you power on the device, it will instantly power itself back on - and you won't even be able to upload new code! If this happens to you, then there is a simple fix involving a hidden feature I added to the driver board design. If you get yourself into this kind of situation let me know, and I will post the solution. 

[Get Involved ](https://www.softrobotics.io/contribute)

Find out how you can help
