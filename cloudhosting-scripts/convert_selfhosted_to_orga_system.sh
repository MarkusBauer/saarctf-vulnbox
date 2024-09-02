#!/usr/bin/env bash

# This script is executed while chroot'ing into the future VM

set -eu

# install the hetzner cloud package
if [ -f /cloud-scripts/install-hetzner-cloud.sh ]; then
  /cloud-scripts/install-hetzner-cloud.sh
fi
rm -rf /cloud-scripts
sed '/install-hetzner-cloud.sh/d' -i /etc/crontab

# install openvpn etc
apt-get update
apt-get install -y openvpn
systemctl enable openvpn@vulnbox

# auto restart openvpn
mkdir -p /etc/systemd/system/openvpn-client@.service.d
mkdir -p /etc/systemd/system/openvpn@.service.d
cat > /etc/systemd/system/openvpn-client@.service.d/override.conf <<'EOF'
[Service]
Restart=always
RestartSec=5
EOF
cat > /etc/systemd/system/openvpn@.service.d/override.conf <<'EOF'
[Service]
Restart=always
RestartSec=5
EOF

# cleanup setup scripts
sed '/setup-password.py/d' -i /root/.bash_profile
rm /root/setup-password.py

# enable ssh password authentication
sed 's/PasswordAuthentication no/PasswordAuthentication yes/g' /etc/ssh/sshd_config

# remove root password reset
# likely not useful here
sed '/^root/s/:0:0:99999:/:1:0:99999:/' -i /etc/shadow

echo "[OK] System has been adjusted to be orga-hosted"
