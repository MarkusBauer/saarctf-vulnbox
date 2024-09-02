#!/usr/bin/env python3
import os
import subprocess
import sys
import threading
import time
from typing import Literal

NETWORK_CONFIG_FILE = '/root/.team_ip'
EXTERNAL_INTERFACE = 'enp0s3'
INTERNAL_INTERFACE = 'enp0s8'
IP_PATTERN = [(1, 1, 10), (200, 200, 32), (1, 200, 0)]


def background_check() -> None:
	"""
	Exit this script once the network has been configured (for example: by another connection).
	:return:
	"""
	while True:
		if os.path.exists(NETWORK_CONFIG_FILE):
			time.sleep(1)
			print('Network configured by another connection.')
			os._exit(0)
		time.sleep(5)


# Network already configured?
if len(sys.argv) > 1 and sys.argv[1] == '--check':
	if os.path.exists(NETWORK_CONFIG_FILE):
		sys.exit(0)
	threading.Thread(target=background_check, daemon=True).start()


def get_ip(team_id: int, suffix: int | str) -> str:
	return '.'.join([str(((team_id // a) % b) + c) for a, b, c in IP_PATTERN] + [str(suffix)])


def query_yes_no(question: str, default: Literal['yes', 'no'] | None = "yes") -> bool:
	"""Ask a yes/no question via raw_input() and return their answer.

	"question" is a string that is presented to the user.
	"default" is the presumed answer if the user just hits <Enter>.
		It must be "yes" (the default), "no" or None (meaning
		an answer is required of the user).

	The "answer" return value is True for "yes" or False for "no".
	From http://code.activestate.com/recipes/577058/
	"""
	valid = {"yes": True, "y": True, "ye": True,
			 "no": False, "n": False}
	if default is None:
		prompt = " [y/n] "
	elif default == "yes":
		prompt = " [Y/n] "
	elif default == "no":
		prompt = " [y/N] "
	else:
		raise ValueError("invalid default answer: '%s'" % default)

	while True:
		sys.stdout.write(question + prompt)
		choice = input().lower()
		if default is not None and choice == '':
			return valid[default]
		elif choice in valid:
			return valid[choice]
		else:
			sys.stdout.write("Please respond with 'yes' or 'no' (or 'y' or 'n').\n")


def configure_interface(team_id: int) -> None:
	subprocess.run(['ifdown', INTERNAL_INTERFACE], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
	text = f'''
	auto {INTERNAL_INTERFACE}
	iface {INTERNAL_INTERFACE} inet static
		address {get_ip(team_id, 1)}
		netmask 255.255.255.0
		broadcast {get_ip(team_id, 255)}
	'''.replace('\n\t', '\n')
	with open(f'/etc/network/interfaces.d/{INTERNAL_INTERFACE}.conf', 'w') as f:
		f.write(text)
	subprocess.check_call(['ifup', INTERNAL_INTERFACE])


def configure_dhcpd(team_id: int) -> None:
	text = f'''
# AUTOCONF
option rfc3442-classless-static-routes code 121 = array of integer 8;
option ms-classless-static-routes code 249 = array of integer 8;

subnet {get_ip(team_id, 0)} netmask 255.255.255.0 {{
	range {get_ip(team_id, 10)} {get_ip(team_id, 191)};
	option subnet-mask 255.255.255.0;
	option broadcast-address {get_ip(team_id, 255)};
	option routers {get_ip(team_id, 1)};
	option domain-name-servers 8.8.8.8;
	# routes for VPN (10.32.X.192/26) and default (0.0.0.0/0).
	option rfc3442-classless-static-routes 26, {get_ip(team_id, 192).replace('.', ', ')}, {get_ip(team_id, 1).replace('.', ', ')}, 0, {get_ip(team_id, 1).replace('.', ', ')};
	option ms-classless-static-routes 26, {get_ip(team_id, 192).replace('.', ', ')}, {get_ip(team_id, 1).replace('.', ', ')}, 0, {get_ip(team_id, 1).replace('.', ', ')};
}}
	
host vulnbox {{
	hardware ethernet 0A:00:27:3D:63:02;
	fixed-address {get_ip(team_id, 2)};
}}
	
host testbox {{
	hardware ethernet 0A:00:27:3D:63:03;
	fixed-address {get_ip(team_id, 3)};
}}
'''
	with open('/etc/dhcp/dhcpd.conf', 'r') as f:
		content = f.read()
	if '# AUTOCONF' in content:
		content = content.split('# AUTOCONF')[0]
	content += '\n\n' + text
	with open('/etc/dhcp/dhcpd.conf', 'w') as f:
		f.write(content)
	subprocess.check_call(['systemctl', 'restart', 'isc-dhcp-server'])
	subprocess.run(['ifdown', INTERNAL_INTERFACE], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
	subprocess.check_call(['ifup', INTERNAL_INTERFACE])


def generate_vpn_keys() -> None:
	path = '/etc/openvpn/pki'
	if os.path.exists(os.path.join(path, 'ta.key')):
		print('[.] VPN keys already present')
		return
	env = dict(os.environ.items())
	env['EASYRSA_BATCH'] = '1'
	subprocess.check_call(['/usr/share/easy-rsa/easyrsa', 'init-pki'], env=env, cwd='/etc/openvpn')
	subprocess.check_call(['/usr/share/easy-rsa/easyrsa', 'build-ca', 'nopass'], env=env, cwd='/etc/openvpn')
	subprocess.check_call(['/usr/share/easy-rsa/easyrsa', 'gen-req', 'server', 'nopass'], env=env, cwd='/etc/openvpn')
	subprocess.check_call(['/usr/share/easy-rsa/easyrsa', 'gen-req', 'TeamMember', 'nopass'], env=env, cwd='/etc/openvpn')
	subprocess.check_call(['/usr/share/easy-rsa/easyrsa', 'sign-req', 'server', 'server'], env=env, cwd='/etc/openvpn')
	subprocess.check_call(['/usr/share/easy-rsa/easyrsa', 'sign-req', 'client', 'TeamMember'], env=env, cwd='/etc/openvpn')
	subprocess.check_call(['/usr/share/easy-rsa/easyrsa', 'gen-dh'], env=env, cwd='/etc/openvpn')
	subprocess.check_call(['openvpn', '--genkey', '--secret', 'ta.key'], cwd=path)
	print('[*] VPN keys have been generated.')


def configure_vpnserver(team_id: int) -> None:
	generate_vpn_keys()
	server_config = f'''
	port 1194
	proto udp
	dev tun
	
	server {get_ip(team_id, 192)} 255.255.255.192
	keepalive 10 120
	
	push "route 10.32.0.0 255.255.0.0"
	push "route 10.33.0.0 255.255.0.0"
	
	ca /etc/openvpn/pki/ca.crt
	cert /etc/openvpn/pki/issued/server.crt
	key /etc/openvpn/pki/private/server.key
	dh /etc/openvpn/pki/dh.pem
	tls-auth /etc/openvpn/pki/ta.key
	duplicate-cn
	cipher AES-128-CBC
	
	user nobody
	group nogroup
	persist-key
	persist-tun
	status openvpn-status.log
	verb 3
	explicit-exit-notify 1
	'''.replace('\n\t', '\n')
	with open('/etc/openvpn/teamserver.conf', 'w') as f:
		f.write(server_config)

	client_config = f'''
	remote TODO_YOUR_SERVER_IP 1194  # TODO PATCH HERE
	client
	dev tun
	proto udp
	nobind

	remote-cert-tls server
	cipher AES-128-CBC

	user nobody
	group nogroup
	persist-key
	persist-tun
	'''.replace('\n\t', '\n')
	included_files = {
		'ca': '/etc/openvpn/pki/ca.crt',
		'cert': '/etc/openvpn/pki/issued/TeamMember.crt',
		'key': '/etc/openvpn/pki/private/TeamMember.key',
		'tls-auth': '/etc/openvpn/pki/ta.key'
	}
	for name, fname in included_files.items():
		client_config += f'\n<{name}>\n'
		with open(fname, 'r') as f:
			client_config += f.read()
		client_config += f'\n</{name}>\n'
	with open('/root/team-vpn-client.conf', 'w') as f:
		f.write(client_config)
	print('[.] Find your client configuration at "/root/team-vpn-client.conf". ')
	print('    IMPORTANT: Update the first line with your IP, then distribute to your teammates.')
	subprocess.check_call(['systemctl', 'start', 'openvpn@teamserver'])
	subprocess.check_call(['systemctl', 'enable', 'openvpn@teamserver'])


def main() -> None:
	print('')
	while True:
		x = input('Please enter your Team ID: ')
		if not x:
			break
		try:
			team_id = int(x)
		except ValueError:
			print('Invalid ID.')
			continue
		print(f'[.]  Configuring interface {INTERNAL_INTERFACE} ...')
		configure_interface(team_id)
		print(f'[*]  Interface {INTERNAL_INTERFACE} is your team interface.')
		if query_yes_no('Do you want to use DHCP for easier configuration?'):
			print(f'[.]  Configuring DHCP server ...')
			configure_dhcpd(team_id)
			print(f'[*]  DHCP active.')
		if query_yes_no('Do you want a VPN server for your teammates to connect to?'):
			print(f'[.]  Configuring VPN server ...')
			configure_vpnserver(team_id)
			print(f'[*]  VPN active.')
		print('')
		print(f'Your team range: {get_ip(team_id, 0)}/24')
		print(f'Your router IP:  {get_ip(team_id, 1)}')
		print(f'Your vulnbox IP: {get_ip(team_id, 2)}')
		print(f'Your testbox IP: {get_ip(team_id, 3)}')
		print(f'Your teammates:  {get_ip(team_id, 64)} - {get_ip(team_id, 254)}')
		print('')
		print('Configuration finished.')
		with open(NETWORK_CONFIG_FILE, 'w') as f:
			f.write(get_ip(team_id, ''))
		subprocess.run(['/root/internet-access-vm-disable.sh'], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
		break
	print(f'You can always repeat this process by calling "{sys.argv[0]}".\n')
	print('Also check out:')
	print(' -  ./internet-access-vm-enable.sh  and  ./internet-access-vm-disable.sh')
	print('')


if __name__ == '__main__':
	main()
