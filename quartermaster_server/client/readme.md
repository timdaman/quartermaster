## What is this?
This is a utility that is designed to run on the host that is receiving 
USB devices. 

Give a url to a Quartermaster resource reservation API
endpoint and, if needed, an authorization token.

1. It will connect with endpoint
2. It will attempt to "reserve" the resource. If the resource is already owned 
by the token owner or the password in the url is correct the API will return the 
configuration data needed to connect to the resource. If the resource is
already in use the client will exit with a non-zero return code.
3. It will connect the remote USB devices to local host.
4. It will start monitoring the USB devices and if they fall offline it
will attempt to reconnect them
5. It will also poll the quarter master server periodically to ensure
it's reservation has not expired

## Why was it made?
This script makes is easier to make uses of Quartermaster resources
on a personal workstation/laptop and in a CI pipeline. 

Rather than display complicated setup steps that are platform specific
the client, in simple cases, takes a single string and 
"just makes things work".

It also works around some tricky workloads, like firmware flashing, 
where the device may fall offline or reboot. It check periodically and
reconnects devices as needed.
