#!/usr/bin/env python3
import functools
import json
import os
import glob
import re
import sys
import subprocess
import shutil

import requests
import yaml
from typing import List, Dict, Optional


def cache_result(func):
	result = []

	@functools.wraps(func)
	def cached_func(*args):
		if not result:
			result.append(func(*args))
		return result[0]

	return cached_func


@cache_result
def assert_docker():
	try:
		subprocess.check_call(['docker', 'ps'], stdout=subprocess.DEVNULL, timeout=10)
	except subprocess.CalledProcessError:
		print('Docker is required in order to build the services. Please install docker.', file=sys.stderr)
		sys.exit(1)


@cache_result
def assert_podman():
	try:
		subprocess.check_call(['podman', 'ps'], stdout=subprocess.DEVNULL, timeout=10)
	except subprocess.CalledProcessError:
		print('Podman is required in order to build this image. Please podman docker.', file=sys.stderr)
		sys.exit(1)


@cache_result
def assert_packer():
	try:
		subprocess.check_call(['packer', '--version'], stdout=subprocess.DEVNULL, timeout=10)
	except subprocess.CalledProcessError:
		print('Packer (https://packer.io) is required in order to build the vulnbox. Please install packer.', file=sys.stderr)
		sys.exit(1)


@cache_result
def assert_virtualbox():
	try:
		subprocess.check_call(['vboxmanage', '--version'], stdout=subprocess.DEVNULL, timeout=10)
	except subprocess.CalledProcessError:
		print('Virtualbox is required in order to build the vulnbox. Please install Virtualbox.', file=sys.stderr)
		sys.exit(1)


@cache_result
def apt_cacher_ng_present() -> bool:
	try:
		response = requests.get('http://localhost:3142/', timeout=1)
		if 'Apt-Cacher' in response.text:
			print('[*] Local apt-cacher-ng will be used to speed up build')
			return True
	except requests.RequestException:
		print('[!] Hint: Install apt-cacher-ng to speed up builds')
	return False


@cache_result
def get_physical_interface() -> str:
	links = subprocess.check_output(['ip', 'link'])
	interfaces = re.findall(r'\d+: ([A-Za-z0-9-_]+):', links.decode())
	for iface in interfaces:
		if iface.startswith('e'):
			return iface
	for iface in interfaces:
		if iface.startswith('w'):
			return iface
	return interfaces[0]


def docker_image_exists(image_name: str) -> bool:
	output = subprocess.check_output(['docker', 'images', '-q', image_name])
	return len(output) >= 12


def build_ci_base_image(service_path: str, image: str):
	path = os.path.join(service_path, 'gamelib', 'ci', 'docker-saarctf-ci-base')
	script = os.path.join(path, 'docker-build.sh')
	print(f'[-] Image {image} is not present, building ...')
	subprocess.check_call([script], cwd=path)
	print(f'[*] Image {image} has been created.')


def query_yes_no(question, default="yes"):
	"""Ask a yes/no question via raw_input() and return their answer.

	"question" is a string that is presented to the user.
	"default" is the presumed answer if the user just hits <Enter>.
		It must be "yes" (the default), "no" or None (meaning
		an answer is required of the user).

	The "answer" return value is True for "yes" or False for "no".
	"""
	valid = {"yes": True, "y": True, "ye": True, "no": False, "n": False}
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


class Service:
	def __init__(self, folder: str):
		folder = os.path.abspath(folder)
		self.folder = folder
		self.name = os.path.basename(folder)
		with open(os.path.join(folder, '.gitlab-ci.yml'), 'r') as f:
			self.ci_config: Dict = yaml.safe_load(f)

	def __lt__(self, other):
		return self.name.lower() < other.name.lower()

	def __gt__(self, other):
		return self.name.lower() > other.name.lower()

	def pull(self):
		if os.path.exists(os.path.join(self.folder, '.git')):
			print(f'[-] Service {self.name}: pull ...')
			subprocess.check_call(['git', '-C', self.folder, 'pull'])
			subprocess.check_call(['git', '-C', self.folder, 'submodule', 'update', '--init', '--recursive'])
			print(f'[*] Service {self.name}: updated.')
		else:
			print(f'[-] Service {self.name}: not a git repository')

	def get_build_image(self) -> str:
		return self.ci_config.get('build', {}).get('image', 'saarsec/saarctf-ci-base:latest')

	def get_cached_dir(self) -> str:
		global CACHE_PATH
		return os.path.join(CACHE_PATH, self.name)

	def is_in_cache(self) -> bool:
		global CACHE_PATH
		return os.path.exists(os.path.join(CACHE_PATH, self.name))

	def clean(self, silent: bool = False):
		global CACHE_PATH
		cache = os.path.join(CACHE_PATH, self.name)
		if self.is_in_cache():
			shutil.rmtree(cache)
			if not silent:
				print(f'[*] Cached build for service {self.name} removed.')
		elif not silent:
			print(f'[*] Service {self.name} not cached.')

	def build(self):
		global CACHE_PATH
		# Create cache folder
		cache = os.path.join(CACHE_PATH, self.name)
		image = self.get_build_image()
		self.clean()
		os.makedirs(cache)
		if image.startswith('saarsec/saarctf-ci-base'):
			if not docker_image_exists(image):
				build_ci_base_image(SERVICES[0].folder, image)
		try:
			# Invoke Docker
			build_cmd = ' && '.join([
				'cp -r /opt/input/*.sh /opt/input/service /opt/input/servicename /opt/input/gamelib /opt/output/',
				'(timeout 3 /opt/input/gamelib/ci/buildscripts/test-and-configure-aptcache.sh || echo "no cache found.")',
				'cd /opt/output',
				'./build.sh',
				f'chown -R {os.getuid()} .'
			])
			cmd = ['docker', 'run', '-v', f'{self.folder}/:/opt/input:ro', '-v', f'{cache}/:/opt/output:rw']
			cmd += ['--rm']
			cmd += [self.get_build_image()]
			cmd += ['/bin/sh', '-c', build_cmd]
			print(f'[-] Invoking docker to build {self.name} ...')
			print('>', ' '.join(cmd))
			subprocess.check_call(cmd)
			print(f'[*] Service {self.name} has been built and cached.')
		except:
			shutil.rmtree(cache)
			raise


class VMImage:
	def __init__(self, config: str, imagename: str):
		self.config = config
		self.folder = os.path.dirname(config)
		self.image = os.path.join(self.folder, 'output', imagename)
		self.imagename = imagename
		self.skip_export: bool = False

	def warn_if_image_present(self, imagename):
		output = subprocess.check_output(['vboxmanage', 'list', 'vms'])
		if f'"{imagename}"'.encode() in output:
			print(f'[!] Warning: VM {imagename} already present.')
			if query_yes_no('Delete VM?', 'no'):
				subprocess.check_call(['vboxmanage', 'unregistervm', '--delete', imagename])

	def is_in_cache(self) -> bool:
		return os.path.exists(self.image)

	def clean(self):
		global CACHE_PATH
		if os.path.exists(os.path.dirname(self.image)):
			shutil.rmtree(os.path.dirname(self.image))
			print(f'[*] Image {self.image} has been removed.')
		else:
			print(f'[*] Image {self.image} not cached.')

	def build(self):
		if os.path.exists(os.path.dirname(self.image)) and len(os.listdir(os.path.dirname(self.image))) == 0:
			os.rmdir(os.path.dirname(self.image))
		print(f'[-] Invoking packer to build {self.image} ...')
		subprocess.check_call(['packer', 'build', '-force', self.config], cwd=self.folder)

	def after_build(self):
		if not self.skip_export:
			print(f'[*] Image {self.image} has been built and cached.')
			subprocess.check_call(['du', '-hs', self.image], timeout=3)
		else:
			print(f'[*] Process finished, no image has been built.')


class DebianVMImage(VMImage):
	def clean(self):
		super().clean()
		if os.path.exists(os.path.join(BASEPATH, 'packer_cache')):
			shutil.rmtree(os.path.join(BASEPATH, 'packer_cache'))

	def build(self):
		response = requests.get('http://cdimage.debian.org/cdimage/release/')
		debian_version = re.findall(r'href="(\d+\.\d+.\d+)/"', response.text)[0]
		with open(self.config, 'r') as f:
			config = json.loads(f.read())
		if config['variables']['debian_version'] != debian_version:
			config['variables']['debian_version'] = debian_version
			with open(self.config, 'w') as f:
				f.write(json.dumps(config, indent=2))
			print(f'[-] Updated Debian version to {debian_version}.')
		print('[!] This step might take some time to finish (up to 30min) without any visible progress.')
		super().build()


class MainVMImage(VMImage):
	def __init__(self, config: str, imagename: str):
		super().__init__(config, imagename)
		self.name = '.'.join(os.path.basename(config).split('.')[:-1])
		self.script = BuildScript(config)
		self.image = os.path.join(self.folder, self.script.output_dir, imagename)
		self.skip_export = self.script.skip_export

	def set_services(self, services: List[Service]):
		self.script.configure_services(services)

	def build(self):
		self.warn_if_image_present(self.script.script['builders'][0]['vm_name'])
		self.config = os.path.join(os.path.dirname(self.config), '.tmp-' + self.name + '-build.json')
		self.script.save(self.config)
		try:
			super().build()
		finally:
			if os.path.exists(self.config):
				os.unlink(self.config)
		if self.script.needs_postprocessing():
			self.script.postprocess()
			self.script.export(self.image)


class BuildScript:
	def __init__(self, filename: str):
		self.filename = filename
		with open(self.filename, 'r') as f:
			self.script: Dict = yaml.safe_load(f)
		self.vboxmanage_before_export: List[List[str]] = []
		self.keep_registered: bool = False
		self.export_opts: List[str] = []
		self.vm_name: Optional[str] = None
		self.output_dir: str = 'output'
		self.skip_export: bool = False
		self.preprocess_config()

	def preprocess_config(self):
		for index, provisioner in enumerate(self.script['provisioners']):
			if provisioner['type'] == 'apt-cacher-ng':
				if apt_cacher_ng_present():
					self.script['provisioners'][index] = {
						'type': 'shell',
						'inline_shebang': '/bin/bash -e',
						'inline': [
							'set -eu',
							"IP=$(/sbin/ip route | awk '/default/ { print $3 }')",
							'echo Configuring apt cache, with ip = $IP',
							'echo "Acquire::http { Proxy \\"http://$IP:3142\\"; }" > /etc/apt/apt.conf.d/01proxy',
						]
					}
				else:
					self.script['provisioners'][index] = {'type': 'shell', 'inline': ['true']}
		for builder in self.script['builders']:
			if builder['type'].startswith('virtualbox'):
				if 'keep_registered' in builder:
					self.keep_registered = builder['keep_registered']
				if 'export_opts' in builder:
					self.export_opts = builder['export_opts']
				if 'vm_name' in builder:
					self.vm_name = builder['vm_name']
				if 'vboxmanage' in builder:
					for cmd in builder['vboxmanage']:
						for i, arg in enumerate(cmd):
							if arg == 'ANY_INTERFACE':
								cmd[i] = get_physical_interface()
								print(f'[.] Using bridge interface "{cmd[i]}"')
				if 'vboxmanage_before_export' in builder:
					self.vboxmanage_before_export = builder['vboxmanage_before_export']
					del builder['vboxmanage_before_export']
				if 'output_directory' in builder:
					self.output_dir = builder['output_directory']
				if 'skip_export' in builder:
					self.skip_export = True
				if self.needs_postprocessing():
					builder['keep_registered'] = True
					builder['skip_export'] = True

	def configure_services(self, services: List[Service]):
		config = []
		for service in services:
			# 1. copy scripts/servicename/gamelib -repo to cache
			for shfile in glob.glob(os.path.join(service.folder, '*.sh')):
				shutil.copy(shfile, os.path.join(service.get_cached_dir(), os.path.basename(shfile)))
			if os.path.exists(os.path.join(service.get_cached_dir(), 'gamelib')):
				shutil.rmtree(os.path.join(service.get_cached_dir(), 'gamelib'))
			shutil.copytree(os.path.join(service.folder, 'gamelib'), os.path.join(service.get_cached_dir(), 'gamelib'))
			shutil.copy(os.path.join(service.folder, 'servicename'), os.path.join(service.get_cached_dir(), 'servicename'))
			# 2. upload files
			config.append({'type': 'file', 'source': service.get_cached_dir(), 'destination': f'/dev/shm/'})
			# 3. run install script and cleanup
			config.append({'type': 'shell', 'inline_shebang': '/bin/bash -e', 'inline': [
				f'echo "===== Installing service ${service.name} ... ====="',
				f'cd /dev/shm/{service.name}',
				'. ./gamelib/ci/buildscripts/prepare-install.sh',
				'./install.sh',
				'./gamelib/ci/buildscripts/post-install.sh',
				'cd /',
				f'rm -rf /dev/shm/{service.name}'
			]})
		for index, provisioner in enumerate(self.script['provisioners']):
			if provisioner['type'] == 'services':
				self.script['provisioners'] = self.script['provisioners'][:index] + config + self.script['provisioners'][index + 1:]
				break

	def save(self, filename: str):
		with open(filename, 'w') as f:
			f.write(json.dumps(self.script, indent=2))

	def needs_postprocessing(self) -> bool:
		return len(self.vboxmanage_before_export) > 0

	def postprocess(self):
		if not self.vm_name:
			raise Exception('Please set vm_name!')
		print(f'[.] Post-processing VM "{self.vm_name}" ...')
		for command in self.vboxmanage_before_export:
			command = ['vboxmanage'] + [c.replace('{{.Name}}', self.vm_name) for c in command]
			subprocess.check_call(command)

	def export(self, ova_file: str):
		if not self.vm_name:
			raise Exception('Please set vm_name!')
		print(f'[.] Exporting VM "{self.vm_name}" ...')
		command = ['vboxmanage', 'export', self.vm_name, '-o', ova_file] + self.export_opts
		subprocess.check_call(command)
		if not self.keep_registered:
			# delete ("unregister") VM
			print(f'[.] Unregistering VM ...')
			command = ['vboxmanage', 'unregistervm', self.vm_name, '--delete']
			subprocess.check_call(command)
		print(f'[*] Created image "{ova_file}"')


class PodmanBuilder:
	def __init__(self):
		self.services: List[Service] = []
		self.output = BASEPATH + '/output-podman/vulnbox-image.tar'
		self.output2 = BASEPATH + '/output-podman/vulnbox-image-compressed.tar'

	def set_services(self, services: List[Service]):
		self.services = services

	def build(self):
		with open(BASEPATH + '/podman/template.Dockerfile', 'r') as f:
			dockerfile = f.read()
		# Create dockerfile with added service install commands
		dockerfile2 = []
		for line in dockerfile.split('\n'):
			if not line.startswith('# PATCH'):
				dockerfile2.append(line)
			else:
				for service in self.services:
					dockerfile2.append(f'# Service {service.name}')
					assert (service.get_cached_dir().startswith(BASEPATH + '/'))
					dockerfile2.append(f'COPY {service.get_cached_dir()[len(BASEPATH) + 1:]} /tmp/{os.path.basename(service.get_cached_dir())}')
					commands = [
						f'echo "===== Installing service ${service.name} ... ====="',
						f'cd /tmp/{service.name}',
						'. ./gamelib/ci/buildscripts/prepare-install.sh',
						'./install.sh',
						'./gamelib/ci/buildscripts/post-install.sh',
						'cd /',
						f'rm -rf /tmp/{service.name}'
					]
					dockerfile2.append('RUN bash -c \'\\' + ' && \\\n    '.join(commands) + "'")
		# write final Dockerfile
		with open(BASEPATH + '/podman/final.Dockerfile', 'w') as f:
			f.write('\n'.join(dockerfile2))
		# build with context
		cmd = ['podman', 'build', '-t', 'vulnbox-image', '-f', 'podman/final.Dockerfile', BASEPATH]
		subprocess.check_call(cmd, cwd=BASEPATH)
		os.makedirs(BASEPATH + '/output-podman', exist_ok=True)
		if os.path.exists(self.output):
			os.remove(self.output)
		if os.path.exists(self.output2):
			os.remove(self.output2)
		subprocess.check_call(['podman', 'save', '-o', self.output, 'vulnbox-image'])
		subprocess.check_call(['podman', 'create', '--name=vulnbox-image-tmp', 'vulnbox-image'])
		subprocess.check_call(['podman', 'export', '-o', self.output2, 'vulnbox-image-tmp'])
		# Import: podman import <tarball> <image-name>
		subprocess.check_call(['podman', 'rm', 'vulnbox-image-tmp'])


BASEPATH = os.path.dirname(os.path.abspath(__file__))
SERVICES = [Service(os.path.dirname(f)) for f in glob.glob(os.path.join(BASEPATH, 'services', '*', 'install.sh'))]
SERVICES.sort()
VULNSCRIPT = os.path.join(BASEPATH, 'vulnbox.yaml')
TESTSCRIPT = os.path.join(BASEPATH, 'testbox.yaml')
ROUTERSCRIPT = os.path.join(BASEPATH, 'router.yaml')
# deprecated: VULNHOSTSCRIPT  = os.path.join(BASEPATH, 'vulnhost.yaml')
CACHE_PATH = os.path.join(BASEPATH, '.build_cache')
print('Services:       ' + ', '.join(s.name for s in SERVICES))
print('Script vulnbox: ' + VULNSCRIPT)
print('Script testbox: ' + TESTSCRIPT)
print('Script router:  ' + ROUTERSCRIPT)


def main():
	import argparse
	parser = argparse.ArgumentParser(description='Build a CTF vulnbox.')
	subparsers = parser.add_subparsers(dest='command')

	parser_prepare = subparsers.add_parser('prepare', help='Prepare (build) services')
	parser_prepare.add_argument('services', type=str, nargs='*', help='services to build')
	parser_prepare.add_argument('--rebuild', action='store_true', help='Rebuild service even if cached build exists')

	parser_clean = subparsers.add_parser('clean', help='Clean pre-built services')
	parser_clean.add_argument('services', type=str, nargs='*', help='services to clean')

	parser_pull = subparsers.add_parser('pull', help='Update service repositories')
	parser_pull.add_argument('services', type=str, nargs='*', help='services to update')

	parser_prepare_debian = subparsers.add_parser('prepare-debian', help='Prepare the OS image')
	parser_prepare_debian.add_argument('--rebuild', action='store_true', help='Rebuild image even if cached image exists')

	parser_build = subparsers.add_parser('build', help='Build the vulnbox as VM image')
	parser_build.add_argument('image_name', type=str, nargs='?', default='vulnbox', help='Which box to build (vulnbox, testbox, router)')
	parser_build.add_argument('services', type=str, nargs='*', help='services to include')
	parser_build.add_argument('--rebuild', action='store_true', help='Rebuild services even if cached build exists')
	parser_build.add_argument('--rebuild-debian', action='store_true', help='Rebuild base image even if cached image exists')

	parser_podman = subparsers.add_parser('build-podman', help='Build the vulnbox as podman image')
	parser_podman.add_argument('services', type=str, nargs='*', help='services to include')
	parser_podman.add_argument('--rebuild', action='store_true', help='Rebuild services even if cached build exists')

	args = parser.parse_args()
	# print('Arguments:', args)

	baseimage = DebianVMImage(os.path.join(BASEPATH, 'debian', 'bullseye.json'), 'saarctf-vulnbox-base.ova')
	images = {
		'vulnbox': MainVMImage(VULNSCRIPT, 'saarctf-vulnbox.ova'),
		'testbox': MainVMImage(TESTSCRIPT, 'saarctf-testbox.ova'),
		'router': MainVMImage(ROUTERSCRIPT, 'saarctf-router.ova'),
		# deprecated 'vulnhost': MainVMImage(VULNHOSTSCRIPT, 'vulnhost.ova'),
	}

	if args.command == 'prepare':
		assert_docker()
		services = [s for s in SERVICES if s.name in args.services] if args.services else SERVICES
		for service in services:
			if args.rebuild or not service.is_in_cache():
				service.build()
			else:
				print(f'[*] Service {service.name} cached.')

	elif args.command == 'clean':
		services = [s for s in SERVICES if s.name in args.services] if args.services else SERVICES
		for service in services:
			service.clean()
		if 'debian' in args.services:
			baseimage.clean()

	elif args.command == 'pull':
		services = [s for s in SERVICES if s.name in args.services] if args.services else SERVICES
		for service in services:
			service.pull()

	elif args.command == 'prepare-debian':
		assert_packer()
		assert_virtualbox()
		if args.rebuild or not baseimage.is_in_cache():
			baseimage.build()
			baseimage.after_build()
		else:
			print('[*] Image "debian" already cached.')

	elif args.command == 'build':
		image_name = args.image_name
		if image_name.endswith('.yaml'):
			image_name = image_name[:-5]
		if image_name not in images:
			print(f'Invalid image name: "{image_name}"')
			sys.exit(1)
		image = images[image_name]

		assert_packer()
		assert_virtualbox()
		if image_name == 'vulnbox':
			assert_docker()
			services = [s for s in SERVICES if s.name in args.services] if args.services else SERVICES
			# build services
			for service in services:
				if args.rebuild or not service.is_in_cache():
					service.build()
				else:
					print(f'[*] Service {service.name} cached.')
			image.set_services(services)

		# build base image
		if args.rebuild_debian or not baseimage.is_in_cache():
			baseimage.build()
			baseimage.after_build()
		else:
			print(f'[*] Image "debian" already cached.')

		# build final image
		if image.is_in_cache():
			image.clean()
		image.build()
		image.after_build()
		print('[SUCCESS] Image has been created.')

	elif args.command == 'build-podman':
		assert_packer()
		assert_docker()
		assert_podman()
		services = [s for s in SERVICES if s.name in args.services] if args.services else SERVICES
		# build services
		for service in services:
			if args.rebuild or not service.is_in_cache():
				service.build()
			else:
				print(f'[*] Service {service.name} cached.')
		builder = PodmanBuilder()
		builder.set_services(services)
		builder.build()
		print('[SUCCESS] Podman image has been created.')

	else:
		print(f'Invalid command: {args.command}. Use {sys.argv[0]} --help')
		parser.print_help()
		sys.exit(1)


if __name__ == '__main__':
	main()
