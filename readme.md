# What is Quartermaster?
Quartermaster is a system coordinates sharing of USB devices. 

It has a plugable interface that supports multiple USB sharing 
technologies, currently VirtualHere and usbip are supported. 

Additionally it integrates with CI systems to supply hardware to jobs
stuck in queue. Support is in place for TeamCity but supporting other
CI systems should be fairly simple.

# Why was Qaurtermaster built?

Usually with USB devices the device has to physically attached to computer. 
For devices that are rare, expensive, or are needed many places this can
be frustrating. In my case I found I was having to set up many special
servers with attached hardware to support certain workloads. Each server
had a cost associated with it and lead to significant under-use of
resources and/or long delays in scheduling workloads.

# Security

Although attempts have been made to secure Quartermaster at present there
are a number of significant shortcomings. At this point the security
most prevents abuse by benign neglect such as a user forgetting to
release a device.

* No protection of any sort of USB device device communications
* Limited controls to prevent device usage when not reserved
* No prevent of user from stealing and disconnecting each others devices

As a result Quartermaster should only be run and users in **trusted environemnts**

# Terminology

A `Pool` is a collection of "like" resources. Users should be able to 
request a resource a from a pool and find any resource in the pool to 
be sufficient for their needs.

A `Resource` is a collection of USB devices logically grouped together.
In most case a resource will only have one device but in special workloads,
for example a device under test and hardware doing the testing, multiple
devices are supported.

A `Device` is the representation of a single USB devices in a single port.
Devices have a drive associated with them
