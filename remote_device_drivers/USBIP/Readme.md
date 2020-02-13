# How to prepare servers to share USB devices through Quartermaster

Three things are needed

* The USBIP tools and kernel module needed to be installed
* A user account for Quartermaster (by default `quartermaster`) needs to be created
* The public key of the Quartermaster server needed to be added to the `authorized_keys` file of the Quartermaster user
* A sudoers file need to be installed to permit the Quartermaster user to run the `usbip` command
* The `usbipd` startup script should be installed and enabled.
* The `usbipd` service should be started

Here are step by step directions for systems using SystemD. Run as root

1. On CentOS: `yum install usbip-utils kmod-usbip`
    On Ubuntu: `apt install linux-tools-common`
2. Run the following command and resolve any issues it brings up, `usbip list -l`
3. Add `usbip.server` script found in the `systemd/` of this folder to `/etc/systemd/system/usbip.service` and set up permissions to match other scripts
4. Edit  `/etc/systemd/system/usbip.service` and set `ExecStart` to the path to `usbipd` as found by `which usbipd`
5. Start the `usbipd` server, `systemctl enable usbip.service; systemctl start usbip.service` 
6. `adduser --disabled-password --gecos 'Quartermaster Service'  quartermaster`
7. Setup ssh directories and files, `install -o quartermaster -g quartermaster -m 700 -d ~quartermaster/.ssh; install -o quartermaster -g quartermaster -m 600 /dev/null ~quartermaster/.ssh/authorized_keys`
8. Added Quartermaster ssh public key to `~quartermaster/.ssh/authorized_keys`
10. Use the follow command to add a sudoers file `visudo -f /etc/sudoers.d/quartermaster` with the following contents `quartermaster   ALL=(root) NOPASSWD: /sbin/usbip`
