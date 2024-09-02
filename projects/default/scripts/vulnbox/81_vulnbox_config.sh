#!/usr/bin/env bash

set -e

# Terminal colors (yellow in contrast to red/green by usual systems)
for D in /home/*/.bashrc; do
  if [ -f "$D" ]; then
    owner=$(stat -c '%U' "$D")
    chown root "$D"
    sed -i '1s;^;force_color_prompt=yes\n\n;' "$D"  # prepend this line
    sed -i 's|\[01;32m|\[11;33m|' "$D"
    chown "$owner" "$D"
  fi
done

# Colors for root (bold yellow console)
cat << 'EOF' >> /root/.bash_profile
	if [ -x /usr/bin/tput ] && tput setaf 1 >&/dev/null; then
		color_prompt=yes
	else
		color_prompt=
	fi
	if [ "$color_prompt" = yes ]; then
		PS1='\[\e]0;\u@\h \w\a\]${debian_chroot:+($debian_chroot)}\[\033[01;33m\]\h\[\033[01;34m\]:\w\$\[\033[00m\] '
		#PS1='${debian_chroot:+($debian_chroot)}\u@\h:\w\$ '
		# Colored ls
		export LS_OPTIONS='--color=auto'
		eval "`dircolors`"
		alias ls='ls $LS_OPTIONS'
		alias ll='ls $LS_OPTIONS -l'
		alias l='ls $LS_OPTIONS -lA'
	fi
	unset color_prompt force_color_prompt
EOF


# Hostname
echo vulnbox > /etc/hostname
echo 127.0.1.1 vulnbox >> /etc/hosts


# Initial setup scripts (for the first start)
if [[ -f /root/setup-network.py ]]; then
  apt-get install -y python3-minimal
  chmod +x /root/*.py
  echo '/root/setup-network.py --check && /root/setup-password.py --check' >> /root/.bash_profile
  PASS=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 32 | head -n 1)
  echo "root:$PASS" | chpasswd
  # ssh is disabled until initial password is set
  echo 'PasswordAuthentication no' >> /etc/ssh/sshd_config
  passwd -d root

  # setup script after DHCP
  echo '#!/bin/sh' > /etc/dhcp/dhclient-exit-hooks.d/setupnetwork
  echo 'if [ $reason = "BOUND" ] ; then' >> /etc/dhcp/dhclient-exit-hooks.d/setupnetwork
  echo '(date ; python3 -u /root/setup-network.py --dhcp "$interface" "$new_ip_address") >> /root/autoconf.log 2>&1 &' >> /etc/dhcp/dhclient-exit-hooks.d/setupnetwork
  echo 'sleep 1' >> /etc/dhcp/dhclient-exit-hooks.d/setupnetwork
  echo 'fi' >> /etc/dhcp/dhclient-exit-hooks.d/setupnetwork
  chmod +x /etc/dhcp/dhclient-exit-hooks.d/setupnetwork
fi
