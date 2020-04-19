#!/usr/bin/env bash

set -eu

export DEBIAN_FRONTEND=noninteractive

# Check for proxy
timeout 2 /dev/shm/test-and-configure-aptcache.sh || echo "No cache."

# Install basic software
apt-get update
apt-get upgrade -y
apt-get install -y sudo nano htop wget dkms build-essential module-assistant
m-a prepare
apt-get clean

# Install Virtualbox Guest Additions from CD
# cd /dev/shm
# mount -t iso9660 -o loop /dev/shm/VBoxGuestAdditions.iso /mnt
# /mnt/VBoxLinuxAdditions.run
# unmount /mnt
# rm -f /dev/shm/*.iso

# Install guest utilities from sid:
echo 'deb http://http.us.debian.org/debian sid main contrib' > /etc/apt/sources.list.d/sid.list
apt-get update
apt-get install virtualbox-guest-dkms
apt-get clean
rm -f /etc/apt/sources.list.d/sid.list

# Clean proxy config
rm -f /etc/apt/apt.conf.d/01proxy || true

# Wipe empty sectors
echo "Cleaning empty sectors ..."
(dd if=/dev/zero of=/var/tmp/bigemptyfile bs=4096k || true) ; rm /var/tmp/bigemptyfile ; echo OK
#echo "TODO: Skipped for now."
echo "Cleaned."
