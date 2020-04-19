#!/usr/bin/env bash

set -eu
TEAM_NET=$(cat /root/.team_ip)

while iptables -D FORWARD -i enp0s8 -o enp0s3 -s "$TEAM_NET"2 -j REJECT 2>/dev/null ; do : ; done
while iptables -D FORWARD -i enp0s8 -o enp0s3 -s "$TEAM_NET"3 -j REJECT 2>/dev/null ; do : ; done

iptables-save > /etc/iptables/rules.v4
echo "Enabled internet access for vulnbox."
