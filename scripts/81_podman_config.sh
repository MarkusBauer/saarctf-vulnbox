#!/usr/bin/env bash

set -e

# Terminal colors (yellow in contrast to red/green by usual systems)
for D in /home/*/.bashrc; do
	if [ -f "$D" ]; then
		echo -e "force_color_prompt=yes\n\n$(cat ${D})" > "${D}"
		sed -i 's|\[01;32m|\[11;33m|' "${D}"
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
