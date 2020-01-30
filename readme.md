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
mostly prevents abuse by benign neglect such as a user forgetting to
release a device after they are done using it.

* No protection of any sort of USB device device communications
* Limited controls to prevent device usage when not reserved
* No prevent of user from stealing and disconnecting each others devices

As a result Quartermaster should only be run and users in
**trusted networks** or access should be controlled using networking.

# Terms

A `Pool` is a collection of "like" resources. Users should be able to 
request a resource a from a pool and find any resource in the pool to 
be sufficient for their needs.

A `Resource` is a collection of USB devices logically grouped together.
In most case a resource will only have one device but in special workloads,
for example a device under test and hardware doing the testing, multiple
devices are supported.

A `Device` is the representation of a single USB devices in a single port.

The `server` which is a central point of control. It maintains a inventory of resources and their status
There are two basic methods of making use of a resource presented by Quartermaster

An `agent` hosts USB devices devices that Quartermaster is configured to provision

A `client` which attached a remote USB device to use it


# Using a Quartermaster resources

1) Using the web service. Using the GUI users can log-in and reserve a resource for their use. They will get a special
url for the resource they reserved and by using the qua


# How to deploy quartermaster

    git clone https://github.com/timdaman/quartermaster.git
    cd quartermaster
    deploy/build_docker_images.sh
    # Add you own certs or use the command below to generate self signed test certs
    # openssl req -new -newkey rsa:2048 -days 365 -nodes -x509 -keyout tls.key  -out tls_chain.crt -subj "/C=CA/ST=ON/L=Kitchener/O=Ops/CN=quartermaster.example.com"
    # If you forgot to generate your certificates before starting services delete the tls.key and tls_chain.crt directories Docker created and run `docker-compose rm frontend` to recover  
    docker-compose up -d

# How to develop plugins
## Add a driver
## Add an integration
