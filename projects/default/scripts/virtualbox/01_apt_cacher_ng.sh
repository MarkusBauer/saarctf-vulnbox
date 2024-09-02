#!/usr/bin/env bash

set -eu
IP=$(/sbin/ip route | awk '/default/ { print $3 }')
echo Configuring apt cache, with ip = $IP
echo "Acquire::http { Proxy \\"http://$IP:3142\\"; }" > /etc/apt/apt.conf.d/01proxy
