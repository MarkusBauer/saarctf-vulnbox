#!/usr/bin/env bash

set -e

# Stop some services known for keeping files alive
systemctl stop mariadb || true

# Clear APT
apt-get update
apt-get --with-new-pkgs upgrade -y
apt-get remove -y linux-image-5.10.0-13-amd64 || true
apt-get autoremove -y
apt-get clean
# remove configured caching proxy
rm -f /etc/apt/apt.conf.d/01proxy || true
sed -i 's|http://HTTPS///|https://|' /etc/apt/apt.conf.d/*.list || true
sed -i 's|http://HTTPS///|https://|' /etc/apt/sources.list.d/*.list || true

# Clear pip cache
rm -rf /root/.cache/pip || true

# Clear tmp
rm -rf /tmp/*

# Clear logs
rm -f /var/log/nginx/*.log
rm -rf /var/log/installer/syslog
rm -f /root/.bash_history
rm -rf /root/.cache  # for example: go build
rm -f /home/*/.bash_history
journalctl --flush
journalctl --rotate
journalctl --vacuum-time=1s
history -c
#TODO
