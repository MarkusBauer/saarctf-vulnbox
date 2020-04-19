#!/usr/bin/env python3
import os
import subprocess
import sys
import threading
import time

NETWORK_CONFIG_FILE = '/root/.team_ip'
INTERFACE = 'enp0s3'
IP_PATTERN = [(1, 1, 10), (200, 200, 32), (1, 200, 0)]


def background_check():
	"""
	Exit this script once the network has been configured (for example: by another connection).
	:return:
	"""
	while True:
		if os.path.exists(NETWORK_CONFIG_FILE):
			time.sleep(1)
			print('Network configured by another connection.')
			os._exit(0)
		time.sleep(3)


# Network already configured?
if len(sys.argv) > 1 and sys.argv[1] == '--check':
	if os.path.exists(NETWORK_CONFIG_FILE):
		sys.exit(0)
	threading.Thread(target=background_check, daemon=True).start()


def get_ip(team_id, suffix):
	return '.'.join([str(((team_id // a) % b) + c) for a, b, c in IP_PATTERN] + [str(suffix)])


def is_vulnbox():
	return b'vuln' in subprocess.check_output(['hostname'])


def configure_interface(team_id):
	subprocess.run(['ifdown', INTERFACE], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
	# generate static interface configuration
	ip = get_ip(team_id, 2 if is_vulnbox() else 3)
	text = f'''
	auto {INTERFACE}
	iface {INTERFACE} inet static
		address {ip}
		netmask 255.255.255.0
		broadcast {get_ip(team_id, 255)}
		gateway {get_ip(team_id, 1)}
	'''.replace('\n\t', '\n')
	with open(f'/etc/network/interfaces.d/{INTERFACE}.conf', 'w') as f:
		f.write(text)
	# comment out interface definition in original file
	with open('/etc/network/interfaces', 'r') as f:
		lines = f.read().split('\n')
	lines = ['#' + l if INTERFACE in l else l for l in lines]
	with open('/etc/network/interfaces', 'w') as f:
		f.write('\n'.join(lines))
	# enable interface again
	subprocess.check_call(['ifup', INTERFACE])
	print(f'[*] Configured interface to {ip}.')


def dhcp_config(ip: str):
	if os.path.exists(NETWORK_CONFIG_FILE):
		print('Network is already configured.')
		return
	if not ip.startswith('10.32.') and not ip.startswith('10.33.'):
		raise Exception(f'Invalid IP "{ip}", please configure manually')
	parts = [int(x) for x in ip.split('.')]
	# ending = 2 if is_vulnbox() else 3
	team_id = (parts[1] - 32) * 200 + parts[2]
	if team_id < 1 or team_id > 400:
		raise Exception(f'Invalid IP "{ip}", please configure manually')
	# if parts[3] == ending:
	#	# we got the correct IP assigned using DHCP
	#	print('IP correct, DHCP is working')
	#else:
	#	# we got another IP from the team network segment assigned, we fix our ip to .2/.3
	#	print('IP not corrent, but DHCP gave us a team subnet. Configuring interface ...')
	# Due to a DHCLIENT bug we should configure the interface static in every case.
	# Otherwise network connection might get lost as soon as the clock gets updated.
	configure_interface(team_id)
	with open(NETWORK_CONFIG_FILE, 'w') as f:
		f.write(get_ip(team_id, ''))
	print('[*] DHCP configuration finished!')


def main():
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
		print(f'[.]  Configuring interface {INTERFACE} ...')
		configure_interface(team_id)
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
		break
	print(f'You can always repeat this process by calling "{sys.argv[0]}".\n')
	print('')


if __name__ == '__main__':
	if len(sys.argv) > 3 and sys.argv[1] == '--dhcp' and sys.argv[2] == INTERFACE:
		dhcp_config(sys.argv[3])
	else:
		main()
