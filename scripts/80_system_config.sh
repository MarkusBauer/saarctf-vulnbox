#!/usr/bin/env bash

set -e

# Organizer SSH key
mkdir -p /root/.ssh
chmod 0700 /root/.ssh
echo '# Saarsec Organizer Key - Please do not delete' >> /root/.ssh/authorized_keys
cat /tmp/saarctf.pub >> /root/.ssh/authorized_keys
echo '' >> /root/.ssh/authorized_keys
chmod 0600 /root/.ssh/authorized_keys
sed -i 's|disable_root: true|disable_root: false|' /etc/cloud/cloud.cfg


# Larger screen resolution
echo 'GRUB_CMDLINE_LINUX_DEFAULT="splash nomodeset"' >> /etc/default/grub
echo 'GRUB_GFXMODE=1024x768x24' >> /etc/default/grub
echo 'GRUB_GFXPAYLOAD=1024x768x24' >> /etc/default/grub
echo 'GRUB_GFXPAYLOAD_LINUX=1024x768x24' >> /etc/default/grub
echo 'virtio_console' > /etc/initramfs-tools/modules
update-initramfs -u
update-grub


# Greeter
echo '=======================' > /etc/motd
echo '==  SaarCTF Vulnbox  ==' >> /etc/motd
echo '=======================' >> /etc/motd
echo '' >> /etc/motd
echo 'PrintLastLog no' >> /etc/ssh/sshd_config
sed -i 's|session    optional   pam_lastlog.so|#session    optional   pam_lastlog.so|' /etc/pam.d/login
rm -f /etc/update-motd.d/10-uname


# "root" autologin (also on serial console)
sed -i 's|ExecStart=-/sbin/agetty |ExecStart=-/sbin/agetty --autologin root |' /lib/systemd/system/getty\@.service
sed -i 's|ExecStart=-/sbin/agetty |ExecStart=-/sbin/agetty --autologin root |' /lib/systemd/system/serial-getty\@.service
sed -i "s|-o '-p -- \\\\u'| |" /lib/systemd/system/getty\@.service
sed -i "s|-o '-p -- \\\\\\\\u'| |" /lib/systemd/system/getty\@.service
sed -i "s|-o '-p -- \\\\u'| |" /lib/systemd/system/serial-getty\@.service
sed -i "s|-o '-p -- \\\\\\\\u'| |" /lib/systemd/system/serial-getty\@.service
sed -i 's|Restart=|#Restart=|' /lib/systemd/system/serial-getty\@.service  # no restart if TTY is not connected
systemctl enable serial-getty@ttyS0.service

# Activate serial console 1, Host-Pipe, uncheck "connect to pipe/socket"
# socat UNIX-CONNECT:/tmp/vm PTY,link=/tmp/vm-pty
# screen /tmp/vm-pty
