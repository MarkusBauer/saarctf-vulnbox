#!/usr/bin/env bash

set -e

echo router > /etc/hostname
echo 127.0.1.1 router >> /etc/hosts
echo '======================' > /etc/motd
echo '==  SaarCTF Router  ==' >> /etc/motd
echo '======================' >> /etc/motd
echo '' >> /etc/motd

# patch openvpn/wireguard services
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
mkdir -p /etc/systemd/system/wg-quick@.service.d
cat > /etc/systemd/system/wg-quick@.service.d/override.conf <<'EOF'
[Service]
Restart=on-failure
RestartSec=5
EOF

# initial setup scripts
chmod +x /root/*.py
echo '/root/setup-password.py --check' >> /root/.bash_profile
echo '/root/setup-network.py --check' >> /root/.bash_profile

# authorized_keys to deploy
mkdir -p /var/www/html/saarctf
echo "# Your team's public SSH keys:" > /var/www/html/saarctf/authorized_keys
