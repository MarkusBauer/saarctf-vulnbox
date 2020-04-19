#!/usr/bin/env python3
import re
import sys
import os
import random
import string
import subprocess
import time
import threading

PASS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'password')
AUTOCONF_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.password_autoconf')
INTERFACE = 'enp0s3'


def background_check():
	"""
	Exit this script once a password has been set (for example: by another connection).
	:return:
	"""
	while True:
		if os.path.exists(PASS_FILE):
			time.sleep(1)
			with open(PASS_FILE, 'r') as f:
				print('')
				print('#######################################')
				print('##  YOUR NEW PASSWORD: "{}"  ##'.format(f.read()))
				print('#######################################')
			os._exit(0)
		time.sleep(5)


def get_my_ip(interface):
	output = subprocess.check_output(['ip', 'addr', 'show', 'dev', interface])
	return re.findall(r'inet (\d+\.\d+.\d+.\d+)', output.decode())[0]


def autoconf():
	"""
	Autoconf is started when the user is asked for a password. That happens after network is configured.
	We send a request to the router and check if he has SSH keys for us. If so we install them.
	This happens only once after initial network configuration.
	"""
	# Random delay if multiple instances want to start autoconf concurrently
	time.sleep(random.randint(1000, 5000) / 1000.0)
	# try this step only once
	if not os.path.exists(AUTOCONF_FILE):
		with open(AUTOCONF_FILE, 'w') as f:
			f.write('Running...')
	# trying to access router
	my_ip = get_my_ip(INTERFACE)
	router_ip = '.'.join(my_ip.split('.')[:3] + ['1'])
	url = f'http://{router_ip}/saarctf/authorized_keys'
	try:
		output = subprocess.check_output(['wget', '-O-', '-q', url], stderr=subprocess.DEVNULL, timeout=4).decode()
	except:
		import traceback
		with open(AUTOCONF_FILE, 'w') as f:
			f.write('Failed.\n')
			traceback.print_exc(file=f)
		return
	if not output.strip().startswith('#') and not output.strip().startswith('ssh-'):
		with open(AUTOCONF_FILE, 'w') as f:
			f.write('Received invalid response:\n' + output)
		return
	with open('/root/.ssh/authorized_keys', 'r') as f:
		keys = f.read()
	keys += '\n\n# Autoconf wrote these keys:\n' + output + '\n# Autoconf end.\n'
	with open('/root/.ssh/authorized_keys', 'w') as f:
		f.write(keys)
	os.chmod('/root/.ssh/authorized_keys', 0o0600)
	with open(AUTOCONF_FILE, 'w') as f:
		f.write('Installed SSH keys:\n' + output)
	if 'ssh-rsa' in output:
		change_root_password()


def has_preinstalled_ssh_key() -> bool:
	"""
	Check if additional SSH keys (next to the organizer key) have been installed.
	:return:
	"""
	if not os.path.exists('/root/.ssh/authorized_keys'):
		return False
	with open('/root/.ssh/authorized_keys', 'r') as f:
		content = f.read()
	return content.count('ssh-rsa ') > 1


def change_root_password():
	# Change root password
	r = random.SystemRandom()
	new_password = ''.join(r.choice(string.ascii_lowercase + string.digits) for _ in range(12))
	os.system('echo "root:{}" | chpasswd'.format(new_password))
	print('')
	print('#######################################')
	print('##  YOUR NEW PASSWORD: "{}"  ##'.format(new_password))
	print('#######################################')
	print('')
	with open(PASS_FILE, 'w') as f:
		f.write(new_password)
	os.chmod(PASS_FILE, 0o600)
	print(f'Your password has been saved to {PASS_FILE}. Please note it NOW.')
	print('')

	# Enable SSH server
	with open('/etc/ssh/sshd_config', 'r') as f:
		content = f.read().replace('PasswordAuthentication no', 'PasswordAuthentication yes')
	with open('/etc/ssh/sshd_config', 'w') as f:
		f.write(content)
	os.system('systemctl enable ssh')
	os.system('systemctl restart ssh')
	print('SSH server is active.')
	print('\n\n')


# Password already changed?
if len(sys.argv) > 1 and sys.argv[1] == '--check':
	if os.path.exists(PASS_FILE):
		sys.exit(0)
	if has_preinstalled_ssh_key():
		print('Additional SSH keys already present.')
		change_root_password()
		sys.exit(0)
	# Start autoconf
	if os.fork() == 0:
		autoconf()
		sys.exit(0)
	# Check if another instance configures the password
	threading.Thread(target=background_check, daemon=True).start()

	print('======================')
	print('= Welcome to saarCTF =')
	print('======================')
	print('')
	input('Press ENTER to generate your root password ...')
	print('')
	change_root_password()
