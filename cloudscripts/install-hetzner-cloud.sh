#!/usr/bin/env bash

is_hetzner() {
  (dmidecode -t system|grep 'Manufacturer\|Product' | grep -q 'Hetzner')
  return $?
}


if is_hetzner; then
	sleep 5

	if dpkg -s hc-utils > /dev/null 2>&1; then
		echo already installed
	else
		wget https://packages.hetzner.com/hcloud/deb/hc-utils_0.0.4-1_all.deb -O /tmp/hc-utils_0.0.4-1_all.deb -q
		apt-get install -f /tmp/hc-utils_0.0.4-1_all.deb
	fi
fi
