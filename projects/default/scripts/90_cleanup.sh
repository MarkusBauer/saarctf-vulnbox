#!/usr/bin/env bash

set -e

# Clear APT
apt-get update
apt-get --with-new-pkgs upgrade -y
apt-get remove -y linux-image-5.10.0-13-amd64 || true
apt-get autoremove -y
apt-get clean
# remove configured caching proxy
rm -f /etc/apt/apt.conf.d/01proxy || true
sed -i 's|http://HTTPS///|https://|' /etc/apt/apt.conf.d/*.list || true

# Clear pip cache
rm -rf /root/.cache/pip || true

# Clear tmp
rm -rf /tmp/*

# Clear logs
rm -f /var/log/nginx/*.log
rm -f /root/.bash_history
rm -f /home/*/.bash_history
history -c
#TODO
