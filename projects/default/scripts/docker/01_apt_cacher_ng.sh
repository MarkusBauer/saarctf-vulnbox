#!/usr/bin/env bash

set -eu
set -o pipefail

install_cacher () {
  IP=$1
  echo "Testing $IP:3142 for apt-cacher-ng ..."
  exec 3<>/dev/tcp/$IP/3142 || return 1
  echo -e "GET / HTTP/1.0\r\nConnection: close\r\n\r\n" >&3 || return 1
  cat <&3 | grep -q 'Apt-Cacher' || return 1
  echo "... found $IP."
  echo "Acquire::http { Proxy \"http://$IP:3142\"; }" > /etc/apt/apt.conf.d/01proxy
}

IP=$(/sbin/ip route | awk '/default/ { print $3 }')
install_cacher $IP && exit 0 || echo "$IP has no cacher"

IP=host.docker.internal
install_cacher $IP && exit 0 || echo "$IP has no cacher"

echo "No apt-cacher available"
