#!/usr/bin/env bash

set -e

export DEBIAN_FRONTEND=noninteractive

# install things that are present on every basic VM, but not in a basic container
apt-get update
apt-get install -y openssh-server sudo nano htop wget systemd locales-all
apt-get install -y openvpn
systemctl enable ssh
echo "PermitRootLogin yes" >> /etc/ssh/sshd_config
