# Installation of Virtual here on servers

Info from here. https://www.virtualhere.com/oem_faq

All of these examples assume x86_64 based systems


# Linux
### Install binaries
        cp virtualhere.service /etc/systemd/system/virtualhere.service
        wget -O /usr/local/bin/vhusbdx86_64 http://www.virtualhere.com/sites/default/files/usbserver/vhusbdx86_64
        wget -O /usr/local/bin/vhclientx86_64 https://virtualhere.com/sites/default/files/usbclient/vhclientx86_64
        chmod a+x /usr/local/bin/vhusbdx86_64 /usr/local/bin/vhclientx86_64

### Systemd

Look inside systemd directory for a service file (virtualhere.service).
    
        systemctl daemon-reload
        systemctl enable virtualhere
        systemctl start virtualhere

After the service starts you can register the server with the following 
