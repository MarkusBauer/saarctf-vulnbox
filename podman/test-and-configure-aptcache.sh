#!/usr/bin/env bash

set -eu

rm -f /etc/apt/apt.conf.d/01proxy || true

if [ -d "/etc/apt" ]; then
  if [ $# -eq 0 ]; then
    IP=$(/sbin/ip route | awk '/default/ { print $3 }')
  else
    IP="$1"
  fi
  echo "Testing $IP:3142 for apt-cacher-ng ..."
  exec 3<>/dev/tcp/$IP/3142
  echo -e "GET / HTTP/1.0\r\nConnection: close\r\n\r\n" >&3
  cat <&3 | grep -q 'Apt-Cacher'
  echo "... found."

  echo "Acquire::http { Proxy \"http://$IP:3142\"; }" > /etc/apt/apt.conf.d/01proxy

else
  echo "not apt."
  exit 1
fi
