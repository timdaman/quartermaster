
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

   
Update `RESERVATION_MAX_MINUTES`, store the expiration timeline in the DB and display to the user in GUI and CLIENT

Tasks to update device status are not scalable as they are done serially. Look ay making them async, or break them up into subtasks.
    Move host information to separate table
    Set up tasks to process hosts in parallel
    Merge checks for share state and online state so only one connection is needed for both
