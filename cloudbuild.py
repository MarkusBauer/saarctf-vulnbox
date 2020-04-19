#!/usr/bin/env python3

# REQUIRES ROOT!
# USAGE: cloudbuild.py <ova-file> <output-archive> [<password>]
# Script can't run if any virtualbox machine is running

import io
import os
import shutil
import subprocess
import sys
import tarfile

excludes_root = ('proc', 'dev', 'tmp', 'run', 'sys', 'lost+found')
excludes = ['--exclude', 'root/setup-network.py', '--exclude', 'etc/dhcp/dhclient-exit-hooks.d/setupnetwork']
new_iptables_rules = ['-A INPUT -p tcp --dport 22 -j ACCEPT', '-A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT', '-A INPUT -i eth0 -j DROP']


def print_filesize(fname: str):
	sys.stdout.write('    ')
	sys.stdout.flush()
	subprocess.check_call(['du', '-hs', fname])


def filter_bash_profile(member: tarfile.TarInfo, r: io.BufferedReader) -> io.BytesIO:
	lines = r.read().decode().split('\n')
	lines = [l if 'setup-network.py' not in l else '/root/setup-password.py --check' for l in lines]
	data = '\n'.join(lines).encode()
	member.size = len(data)
	return io.BytesIO(data)


def filter_crontab(member: tarfile.TarInfo, r: io.BufferedReader) -> io.BytesIO:
	lines = r.read().decode().split('\n')
	lines += ['@reboot root /cloudscripts/install-hetzner-cloud.sh']
	data = '\n'.join(lines).encode() + b'\n'
	member.size = len(data)
	return io.BytesIO(data)


def filter_iptables(member: tarfile.TarInfo, r: io.BufferedReader) -> io.BytesIO:
	content = r.read().decode()
	content = content.replace('COMMIT', '\n'.join(new_iptables_rules) + '\nCOMMIT')
	data = content.encode()
	member.size = len(data)
	return io.BytesIO(data)


def filter_resume(member: tarfile.TarInfo, r: io.BufferedReader) -> io.BytesIO:
	data = b'RESUME=none\n'
	member.size = len(data)
	return io.BytesIO(data)


def filter_tar_archive(input_file: str, output_file: str):
	pack_dependencies('/dev/shm/tmp.tar')
	with tarfile.open(input_file, 'r') as fi:
		with tarfile.open(output_file, 'w', format=fi.format) as fo:
			for member in fi.getmembers():
				if member.isdir() and not member.issym():
					extracted = fi.extractfile(member)
					fo.addfile(member, extracted)
				elif member.isfile() and not member.issym():
					extracted = fi.extractfile(member)
					if member.name == 'root/.bash_profile':
						extracted = filter_bash_profile(member, extracted)
					elif member.name == 'etc/crontab':
						extracted = filter_crontab(member, extracted)
					elif member.name == 'etc/iptables/rules.v4':
						extracted = filter_iptables(member, extracted)
					elif member.name == 'etc/initramfs-tools/conf.d/resume':
						extracted = filter_resume(member, extracted)
					fo.addfile(member, extracted)
				else:
					fo.addfile(member)
			with tarfile.open('/dev/shm/tmp.tar', 'r') as fi2:
				for member in fi2.getmembers():
					if (member.isdir() or member.isfile()) and not member.issym():
						extracted = fi2.extractfile(member)
						member.uid = 0
						member.gid = 0
						member.uname = 'root'
						member.gname = 'root'
						fo.addfile(member, extracted)
					else:
						fo.addfile(member)
	os.remove('/dev/shm/tmp.tar')


def pack_dependencies(fname: str):
	subprocess.check_call(['tar', '--numeric-owner', '-cpf', fname, 'cloudscripts'], cwd=os.path.dirname(os.path.abspath(__file__)))


def ova_to_archive(ova_file: str, output: str):
	tmp_folder = '/dev/shm/ovafun'
	mnt_folder = os.path.join(tmp_folder, 'mnt')
	output = os.path.abspath(output)
	os.makedirs(tmp_folder, exist_ok=True)
	os.makedirs(mnt_folder, exist_ok=True)
	print('[.] Extract ova file ...')
	subprocess.check_call(['tar', '--no-same-owner', '-xf', os.path.abspath(ova_file)], cwd=tmp_folder)
	vmdk_file = [os.path.join(tmp_folder, fname) for fname in os.listdir(tmp_folder) if fname.endswith('.vmdk')][0]
	print_filesize(vmdk_file)

	# sudo LIBGUESTFS_BACKEND=direct guestmount -a saarctf-testbox-disk001.vmdk -i --ro /mnt/tmp
	if os.path.exists(os.path.join(mnt_folder, 'etc')):
		print('[.] already mounted?')
	else:
		print('[.] Mount ' + vmdk_file + ' ...')
		env = dict(os.environ.items())
		env['LIBGUESTFS_BACKEND'] = 'direct'
		subprocess.check_call(['guestmount', '-a', vmdk_file, '-i', '--ro', mnt_folder], env=env)

	# pack stuff into the archive
	print('[.] Pack archive ...')
	filelist = [fname for fname in os.listdir(mnt_folder) if fname not in excludes_root]
	tmp_archive = os.path.join(tmp_folder, 'tmp.tar')
	tmp_archive2 = os.path.join(tmp_folder, 'tmp2.tar')
	subprocess.check_call(['tar', '--xattrs', '--numeric-owner'] + excludes + ['-cpf', tmp_archive] + filelist, cwd=mnt_folder)
	subprocess.check_call(['umount', mnt_folder])
	# Filter archive
	filter_tar_archive(tmp_archive, tmp_archive2)
	os.remove(tmp_archive)
	# Compress archive
	if output.endswith('.tar.gz'):
		print('[.] Compressing ...')
		subprocess.check_call(['gzip', tmp_archive2])
		tmp_archive2 += '.gz'
	elif output.endswith('.tar.xz'):
		print('[.] Compressing ...')
		subprocess.check_call(['xz', '-T', '0', tmp_archive2])
		tmp_archive2 += '.xz'
	if os.path.exists(output):
		os.remove(output)
	shutil.move(tmp_archive2, output)
	print_filesize(output)

	print('[.] Cleanup ...')
	shutil.rmtree(tmp_folder)

	print('[*] Done!')


def encrypt_file(fname, passwd):
	subprocess.check_call(['gpg', '--batch', '--passphrase', passwd, '--no-options', '-c', fname])
	with open(fname + '.pass.txt', 'w') as f:
		f.write(f'Password for {fname}:\n{passwd}\n')


def namespace_magic():
	import unshare
	uid = os.getuid()
	gid = os.getgid()
	unshare.unshare(unshare.CLONE_NEWUSER | unshare.CLONE_NEWNS)
	with open('/proc/self/uid_map', 'w') as f:
		f.write(f'0 {uid} 1')
	# with open('/proc/self/gid_map', 'w') as f:
	#	f.write(f'0 {gid} 1')
	os.system('id')


if __name__ == '__main__':
	# filter_tar_archive('/dev/shm/bundle.tar', '/dev/shm/mod.tar')
	output_file = sys.argv[2]
	if output_file.endswith('.gpg'):
		output_file = output_file[:-4]
	ova_to_archive(sys.argv[1], output_file)
	if len(sys.argv) > 3:
		encrypt_file(output_file, sys.argv[3])
	pass
