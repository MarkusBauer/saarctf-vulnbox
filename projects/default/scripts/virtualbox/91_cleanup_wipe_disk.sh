#!/usr/bin/env bash

set -e

echo "This machine is a VM - wiping empty sectors on disk"
systemctl stop nginx 2>/dev/null || true
(lsof | grep deleted) || echo lsof failed
echo "This might take several minutes without visible progress ..."
dd if=/dev/zero of=/var/tmp/bigemptyfile bs=512k || true
rm -f /var/tmp/bigemptyfile

history -c
