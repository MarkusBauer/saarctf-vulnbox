#!/usr/bin/env bash

export DEBIAN_FRONTEND=noninteractive

apt-get install -y openvpn isc-dhcp-server iptables-persistent \
		bmon iftop iptraf nload pktstat
ln -s /usr/bin/nload /usr/sbin/iftop /usr/sbin/iptraf /usr/bin/bmon /usr/sbin/pktstat /root/


# Enable IP forwarding
sysctl -w net.ipv4.ip_forward=1
echo 'net.ipv4.ip_forward = 1' >> /etc/sysctl.conf

# Default firewall
iptables -t nat -A POSTROUTING -o enp0s3 -j MASQUERADE
iptables -A FORWARD -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
iptables-save > /etc/iptables/rules.v4

# Configure the DHCP server
echo 'INTERFACESv4="enp0s8"' >> /etc/default/isc-dhcp-server
sed -i 's|default-lease-time .*;|default-lease-time 7200;|' /etc/dhcp/dhcpd.conf

# TODO document:
# ip route del default via 10.32.X.1
