
* Create agent to run on remote servers to manage local devices that are being shared.
    This would have all the intelligence on how to accommodate OS differences
    This would install kernel modules as needed
    Will have to figure out plugin support for different server or just bake them in.
 
 When remote commands fail raise good errors in GUI
    
Update jobs to have pre and post scripts for sharing and unsharing
  Agent side or server side
  Add toggle to enable/disable script execution

Add client api for retrieving reservation record

Resources for USB power switching
  https://acroname.com/store/s79-usbhub-3p
  https://www.crowdsupply.com/capable-robot-components/programmable-usb-hub/updates/production-update-part-ii
  https://www.yepkit.com/product/300115/YKUSHXS
  https://electronics.stackexchange.com/questions/393468/efficient-way-to-selectively-unpower-usb-ports
  https://www.smartspate.com/how-to-convert-a-basic-usb-hub-into-driven-one/

   
Tasks to update device status are not scalable as they are done serially. Look ay making them async, or break them up into subtasks.
    Move host information to separate table
    Set up tasks to process hosts in parallel
    Merge checks for share state and online state so only one connection is needed for both

Windows support

Update client to have a wait for connections command

Andriod ADB support

for all servers
  schedule task
    in task
      for each connector
        get all state information
        update online status
        if online
          update share state


Create autocomplete for adding host
    automatically retrieve host key
    display host key in record as read only

Create autocomplete for adding device
    automatically retrieve all suitable devices on host not being used elsewhere 
    
    
Migration plan
   create remote host table
   add field to device
   
   for each dev
     get host field
     host = check if remote host exists for SSH
     if not create remote host for ssh
     host = new host
     delete host field from device
     update device host field to $host
     update driver field to "USBIP"
     save device


Update client to
    embed default server url
    change reservation arg to only need reservation number
    add server arg to override default
