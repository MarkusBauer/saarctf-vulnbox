#!/usr/bin/env bash

# Clear APT
apt-get autoremove -y
apt-get clean
rm -f /etc/apt/apt.conf.d/01proxy || true  # remove configured caching proxy

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

# Wipe empty sectors
if grep -q ^flags.*\ hypervisor\  /proc/cpuinfo; then
	echo "This machine is a VM - wiping empty sectors on disk"
	systemctl stop nginx 2>/dev/null || true
	lsof | grep deleted
	#apt-get install -y secure-delete
	echo "This might take several minutes without visible progress ..."
	dd if=/dev/zero of=/var/tmp/bigemptyfile bs=512k
	rm /var/tmp/bigemptyfile
	#sfill -zllv /
	# TODO DISABLED FOR NOW
	#echo "===  WARNING ==="
	#echo "WARNING: WIPING SKIPPED FOR NOW (DEMO PHASE)"
	#echo "=== /WARNING ==="
else
	echo "Not a VM - not wiping empty sectors"
fi
history -c
