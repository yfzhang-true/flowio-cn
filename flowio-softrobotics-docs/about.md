# About

> Source: https://www.softrobotics.io/about

###### 

###### About FlowIO

###### 

FlowIO is a miniature, modular, pneumatic development platform with a software toolkit for control, actuation, and sensing of soft robots and programmable materials. Five pneumatic ports and multiple fully-integrated modules to satisfy various pressure, flow, and size requirements make FlowIO suitable for most wearable and non-wearable pneumatic applications in HCI and soft robotics. FlowIO includes a software stack with APIs, Bluetooth capabilities, and web-GUI supported on all major mobile and desktop operating systems. The system is fully compatible with Arduino, JavaScript, and Google Chrome, while support for Scratch, Python, and Unity is planned for future development, making FlowIO suitable for makers from any technical background. Over a dozen people have used the FlowIO platform, ranging from high-school and college students to graduate students and researchers. 

###### 

###### Motivation

###### 

Platform technologies such as Arduino, Raspberry Pi, Lego Mindstorms, and Scratch have liberated entire fields by diminishing barriers to entry. Arduino transformed electronics, Raspberry Pi – portable computing, Lego Mindstorms – robotics, and Scratch – programming. These and similar platforms have not only made esoteric fields more accessible for artists, designers, and makers, but they have also enabled researchers and engineers to prototype more rapidly. For instance, an electronics project that two decades ago may have required advanced engineering expertise, and a week of work in a lab with expensive equipment, today such a project can be done in a weekend, by a high-school student, in his/her living room! This transformation, I believe, is thanks to: (1) the availability of platforms and tools that are easy to learn and use; (2) the emergence of modules from companies like Adafruit, designed specifically for popular platforms; and (3) a growing community that is continuously contributing software, projects, ideas, tutorials, and other content – inspiring even more people to be part of that community as both users and contributors.

Today, prototyping in soft robotics and programmable materials has high barriers to entry and is as inaccessible to most people as electronics prototyping was two decades ago. This problem exists because the three aforementioned factors that transformed electronics prototyping have yet to occur in the domain of soft robotics. In recent years, projects such as [PneUI](https://tangible.media.mit.edu/project/pneui/), [aeroMorph](https://tangible.media.mit.edu/project/aeromorph/), [MorphIO](https://dl.acm.org/doi/10.1145/3322276.3322337), [Bubble](https://dl.acm.org/doi/10.1145/3290607.3312868), [AuxeticBreath](https://dl.acm.org/doi/10.1145/3430524.3444636), and numerous others, demonstrate a growing interest in soft robotics from HCI researchers, students, artists, designers, and makers. However, a challenge faced by nearly everyone working on pneumatically actuated projects is that one typically has to build their own driving systems from the ground up and dedicate sometimes most of their time on developing the pneumatics, electronics, and software, instead of developing novel soft actuators, applications, or user experiences. This challenge creates significant time inefficiencies, stifles innovation, and even discourages the pursuit of ideas requiring more sophisticated drive electronics or software.

###### 

###### Related Works and Origins of FlowIO

###### 

While many platforms exist for electronics and computing, platforms for soft robotics and programmable materials still lag far behind. [Pneuduino](http://pneuduino.org/), [Programmable Air](https://www.programmableair.com/), and [Soft Robotics Toolkit (SRT)](https://softroboticstoolkit.com/) are the three most well-known pneumatic toolkit attempts to date. However, they all have large size, limited sensing and control capabilities, and require external pressure and/or power sources, making them impractical for most real-world wearable or complex soft-robotics projects, such as [Bubble](https://dl.acm.org/doi/10.1145/3290607.3312868). The SRT is a DIY solution with off-the-shelf parts. Pneuduino is smaller than SRT, has custom modular hardware, and comes with an Arduino library; however, it still requires external pumps and power sources. Programmable Air provides similar capabilities to Pneuduino while using more affordable parts and integrating the pumps into the device itself. However, the base version has only a single pneumatic I/O port (with the possibility to add more), external high-current power source is still required, and the pumps cannot be changed easily to accommodate different pressure or flow-rate needs. All of the aforementioned toolkits also lack any GUIs and are compatible only with Arduino, making them accessible only to users familiar with Arduino programming. 

FlowIO addresses all of the aforementioned hardware and software limitations of related systems. The goal of FlowIO is to be a truly-general-purpose, miniature, pneumatics development platform that is accessible for everyone. FlowIO was inspired out of pure necessity when I was working on [project Bubble](https://dl.acm.org/doi/10.1145/3290607.3312868) in 2018-2019, which required a miniature fluidics driver with 5 pneumatic ports, but nothing existed to satisfy that need. This led me on a 2-year quest resulting in over 20 prototype iterations to create the world’s smallest, wearable, full-featured, pneumatics development platform. Continuous feedback from diverse users helped FlowIO become not just a toolkit but a true general-purpose platform technology with both hardware and software, capable of satisfying the needs of nearly anyone working on wearable or non-wearable pneumatics projects, while also being highly user-friendly for both novice and expert users and cross-platform compatible.

FlowIO was designed using a first-principles approach, and is not based on any related works. The pneumatic and system architecture is significantly different from the prior works, and was motivated by my familiarity with the challenges and unmet needs in the HCI, soft robotics, and maker communities, as well as the needs of my own future projects. 

###### 

###### Read More

###### 

For technical details of FlowIO, please read the published paper:

Ali Shtarbanov. 2021. FlowIO Development Platform – the Pneumatic “Raspberry Pi” for Soft Robotics. In CHI Conference on Human Factors in Computing Systems (CHI ’21 Extended Abstracts), May 08–13, 2021, Yokohama, Japan. ACM, New York, NY, USA, 6 pages. <https://doi.org/10.1145/3411763.3451513>

([Download PDF](https://www.softrobotics.io/_files/ugd/cefaa7_ee86313c9f304264a3ad2ab39a64989c.pdf))

######    
This ongoing work is designed and developed by Ali Shtarbanov (including all hardware & electronics, the software stack plus APIs & GUI, and this website) as part of his continuing Ph.D. studies at MIT Media Lab. Some of the content on this website, where noted, was provided by contributors. This work was made possible thanks to many people and organizations at who provided help, feedback, examples, advice, and financial assistance. [See the full list of contributors and donors](https://www.softrobotics.io/contributors)
