# Limitations

> Source: https://www.softrobotics.io/limitations

######    
Limitations of FlowIO  

FlowIO is the most advanced and the most user-friendly miniature pneumatics development platform in existence today! However, it is not without its shortcomings and drawbacks. The FlowIO platform and this website are still works in progress. As such, FlowIO should not be viewed as a finished product but rather as a project that is still rapidly evolving, changing, and improving. There are limitations, new features to be implemented, and additional content to be added to this website. 

On this page, I list some of the limitations of FlowIO and how to overcoming them \- so that readers know better what this project offers, where it comes short, and what still needs improvement and more work.

This article is also a call for action for potential volunteers and contributors to see where we are today, and to help us address some those challenges in order to make FlowIO and this website what they eventually aspire to be.

Hardware: Warable-First Design Approach

FlowIO was designed mainly for wearable applications \- which meant that it had to be super small, fully-integrated with built-in batteries and chargers, very low power, comfortable to wear, have a nice aesthetic feel, and be within a reasonable cost for a device of this kind. As my secondary objectives, I also wanted it to be a truly-general-purpose solution suitable not only for a wide variety of wearable applications, but also for many nonwearable applications that are typically more demanding in terms of pressure, flow-rate, and power. Satisfying all of these objectives is in fact impossible with a single device, because many of them are completely at odds with each other. For example, you can easily make a platform that is suitable for highly-demanding applications if you don't need it to be miniature and low power. Or, you can make a solution very low cost if designed for a specific application rather than for general-purpose. Numerous tradeoffs were faced and had to be carefully evaluated.

The primary objectives for FlowIO were wearability, low-power, miniaturization, versatility, and low cost. Everything else was secondary. Whenever a design choice had to be made that involved a tradeoff, priority was given to satisfying the primary objectives at the expense of secondary objectives. 

The wearable-first design approach that was followed, meant right away that FlowIO will have some shortcomings when compared to larger nonwearable systems. The first two of those are the pressure and flow-rates that are possible with FlowIO. In the first several versions of FlowIO the maximum pressures possible were in the 10psi range and flow-rates in the 0.5 l/min range. With subsequent iterations FlowIO was greatly improved by making the design completely modular with the ability to swap pump modules on-the-fly. Today, FlowIO can achieve pressures in the 30psi range and flow-rates in the 3L/min range - which is huge for a wearable device of this size and operating at such low power. Much higher pressures are also possible (up to 6bar) when an external pressure source is used with FlowIO (with valve type D). The modular and open-source design of FlowIO allows anyone to make new modules for FlowIO, with alternative components that can deliver higher pressures and flow-rates; but of course this would come at the expense of larger size and more power consumption. 

Hardware: Simultaneous Sensing

The main module of FlowIO has many different kinds of sensors. However, there is only one internal pressure + temperature sensor that is used for monitoring the pressure on all 5 ports. To measure the pressure at a port, the corresponding port valve must first be opened. Therefoe, you cannot simultaneously measure the pressure at all 5 ports, and you have to use time-multiplexing instead where you cycle through each of the 5 ports.

This is where the Sensors++ module comes to the rescue. Sensors++ offers a dedicated pressure sensor at the output of each port, and you don't need to open any valves to read the pressure at a port. If you have an applications that requires you to sense pressures at multiple ports simultaneously, you would also need the Sensors++ module in addition to the Main module.

Hardware: Simultaneous Actuation

You can inflate, vacuum, or release one or more ports at the same time, as long as you do the same operation on all the ports. However, you cannot simultaneously do different operations on different ports. For example you cannot inflate on port 1 while vacuuming on port 2. However, if you want to do something like this, there is a solution for this. Both the JavaScript API and the GUI allow you to connect to and control more than one device synchronously. Thus, if you use 2 FlowIO devices you can do different operations simultaneously!

Software: Arduino Libraries and APIs

The software for FlowIO consists of a stack with multople layers of abstraction as explained here. The lowest layers of the stack are completely stable and all known bugs in those layers have been fixed. The Arduino Libraries and APIs are more-or-less complete. Some additional features such as low-level feedback-control loops remain to be added and finalized. Experimental versions of some new low-level features under development are available only to collaborators with [premium access](https://www.softrobotics.io/premium-content). If you wish to have limitation-free software experience with FlowIO, you can work directly with the low-level layers of the software stack and write your own custom code from the ground up. 

Software: Arduino Firmware for BLE Control of FlowIO

The firmware layer of the stack is also very stable and all known bugs have been fixed. There are however, a great number of new features and enhancements that remain to be added to this layer. Some of those yet to be implemented features include:

\- BLE service for controlling all the available GPIO pins.

\- BLE security and authentication.

\- Feedback control loops that run directly on the microcontroller.

\- Direct communication between FlowIO devices without a web-browser in the middle. 

However, these are mainly enhancements that would be good to have, but arent essential for most applications. And implementing them is pretty straightforward to do, and is just a matter of finding time to do them myself or finding a volunteer to do them.

Software: JavaScript APIs

This layer of the software stack is in a slighly less complete state compared to the lower layers, but is still very rebust and stable, and all known bugs have been fixed. There are however, a pletora of interesting features remaining to be added. The biggest limitation with this layer is that the API is not fully documented yet, because changes are still being made. The documentation for this layer will be publicly posted once the implementation reaches a more mature state. While the JavaScript API layer is still rapidly evolving, the draft documentation for this layer is only available to collaborators with [premium access](https://www.softrobotics.io/premium-content). 

Software: Web GUI

The Graphical User Interface for FlowIO provides a graphical representation of a subsect of the features that the JavaScript API offers. All features that you see in the GUI currently work fine and well, without known bugs. However, there are many enhancements to be made and new features to be added. There are far more features available in the API right now that just have to also be implemented in the GUI. However, because the GUI and the JavaScript API are both accessible via the Chrome web browser, this provides the user with the option to use both at the same time! For example if you wish to do something with FlowIO that the GUI does not yet support, you can write your JavaScript code just for the specific feature you need directly in the Chrome console, and you can still use the GUI for everything else - all in the same Chrome tab!

(More content coming soon)

Remote Communication 

Documentation

Website

Production Challenges

Examples

[Get Involved ](https://www.softrobotics.io/contribute)

Find out how you can help
