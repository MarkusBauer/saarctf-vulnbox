#!/usr/bin/env bash

# Install bindfs package for append-only mounts and
# add marker to /etc/fstab so additional entries
# from services can be extracted easily

apt-get update
apt-get install -y bindfs
echo "# service mounts" >> /etc/fstab
