#!/usr/bin/env bash

set -eu
TEAM_NET=$(cat /root/.team_ip)

iptables -A FORWARD -i enp0s8 -o enp0s3 -s "$TEAM_NET"2 -j REJECT
iptables -A FORWARD -i enp0s8 -o enp0s3 -s "$TEAM_NET"3 -j REJECT

iptables-save > /etc/iptables/rules.v4
echo "Disabled internet access for vulnbox."
