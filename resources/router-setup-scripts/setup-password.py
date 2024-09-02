#!/usr/bin/env python3
import sys
import os
import random
import string
import threading
import time

PASS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'password')


def background_check() -> None:
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


# Password already changed?
if len(sys.argv) > 1 and sys.argv[1] == '--check':
	if os.path.exists(PASS_FILE):
		sys.exit(0)
	threading.Thread(target=background_check, daemon=True).start()

print('=================================')
print('= Welcome to the saarCTF Router =')
print('=================================')
print('')
input('Press ENTER to generate your root password ...')
print('')

# Change root password
r = random.SystemRandom()
new_password = ''.join(r.choice(string.ascii_lowercase + string.digits) for _ in range(10))
os.system('echo "root:{}" | chpasswd'.format(new_password))
print('#######################################')
print('##  YOUR NEW PASSWORD: "{}"  ##'.format(new_password))
print('#######################################')
print('')
with open(PASS_FILE, 'w') as f:
	f.write(new_password)
os.chmod(PASS_FILE, 0o600)
print(f'Your password has been saved to {PASS_FILE}. Please note it NOW.')
print('\nHint: Insert your SSH key into "/var/www/html/saarctf/authorized_keys".')
print('\n\n')
