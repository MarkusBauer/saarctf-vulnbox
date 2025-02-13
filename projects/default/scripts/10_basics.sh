#!/usr/bin/env bash

export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get upgrade -y
apt-get install -y sudo wget curl acl python3-minimal \
		htop nano net-tools bash-completion screen vim man lsof tcpdump rsync \
		qemu-guest-agent cloud-init cloud-initramfs-growroot cloud-utils iptables-persistent \
		wireguard
