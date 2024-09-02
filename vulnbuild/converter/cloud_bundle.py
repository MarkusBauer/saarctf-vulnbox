import io
import os
import shutil
import subprocess
import sys
import tarfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence, IO, Literal

from vulnbuild.builds import BuildTask, Builder
from vulnbuild.config import GlobalConfig
from vulnbuild.converter.converter import ConverterTask, Converter
from vulnbuild.utils.sudo import SudoHelper
from vulnbuild.vmbuilder.build_targets import VmBuildTarget


@dataclass
class CloudBundleTask(ConverterTask):
    ova_file: Path

    @property
    def doc(self) -> str:
        return f'Create a .tar.gz for cloud deployment out of {self.ova_file.name} (requires sudo)'


class CloudBundleConverter(Converter[CloudBundleTask]):
    def __init__(self, name: str = '') -> None:
        self._contains_name = name
        self._compression: Literal['gz', 'xz'] = 'xz'

    def get_conversion_targets(self, task: BuildTask, builder: Builder) -> Sequence[CloudBundleTask]:
        if isinstance(task, VmBuildTarget):
            ova = builder.get_output_file(task)
            if ova and ova.suffix == '.ova' and self._contains_name in ova.name:
                return [CloudBundleTask(name=f'vm:{task.name}:cloudbundle', project=task.project, base=task, ova_file=ova)]
        return []

    @classmethod
    def accepts(cls, task: BuildTask) -> bool:
        return isinstance(task, CloudBundleTask)

    def is_built(self, task: CloudBundleTask) -> bool:
        return self.get_output_file(task).exists()

    def get_output_file(self, task: CloudBundleTask) -> Path:
        return task.ova_file.parent / f'{task.ova_file.name[:-4]}.tar.{self._compression}'

    def build(self, task: CloudBundleTask) -> Any:
        print(f'[.] Creating cloud bundle archive from {task.ova_file.name}.')
        print(f'[!] This process might require sudo, be prepared to enter your password if asked')
        print(f'[!] No virtualbox VM must be running during conversion.')
        tmp_folder = Path('/dev/shm/ovafun')
        tmp_folder.mkdir(parents=True, exist_ok=True)
        image_archive = tmp_folder / 'image.tar'
        try:
            SudoHelper.run_as_root(self._extract_image, task.ova_file, image_archive)
            ArchiveCloudConverter(image_archive, self.get_output_file(task), tmp_folder).convert()
        finally:
            shutil.rmtree(tmp_folder)
        print(f'[*] Created cloud bundle {self.get_output_file(task).name}')

    def _extract_image(self, image: Path, output_archive: Path) -> None:
        OvaExtractor(image, output_archive, output_archive.parent).extract()
        if output_archive.exists():
            os.chown(output_archive, SudoHelper.original_uid, SudoHelper.original_gid)

    def clean(self, task: CloudBundleTask) -> None:
        self.get_output_file(task).unlink(missing_ok=True)


def _print_filesize(fname: str | Path) -> None:
    sys.stdout.write('    ')
    sys.stdout.flush()
    subprocess.check_call(['du', '-hs', str(fname)])


class OvaExtractor:
    excludes_root = ('proc', 'dev', 'tmp', 'run', 'sys', 'lost+found')
    excludes: list[str] = ['--exclude', 'root/setup-network.py', '--exclude', 'etc/dhcp/dhclient-exit-hooks.d/setupnetwork']

    def __init__(self, input_file: Path, output_file: Path, tmp_folder: Path) -> None:
        self.input_file = input_file.absolute()
        self.output_file = output_file.absolute()
        self._tmp_folder = tmp_folder
        self._mnt_folder = self._tmp_folder / 'mnt'

    def extract(self) -> None:
        vmdk_file = self._extract_ova()
        try:
            self._mount_vmdk(vmdk_file)
            try:
                self._pack_archive()
            finally:
                self._umount()
        finally:
            vmdk_file.unlink(missing_ok=True)

    def _extract_ova(self) -> Path:
        print('[.] Extract vmdk from ova file ...')
        subprocess.check_call(['tar', '--no-same-owner', '-xf', str(self.input_file)], cwd=self._tmp_folder)
        vmdk_file: Path = [f for f in self._tmp_folder.iterdir() if f.name.endswith('.vmdk')][0]
        _print_filesize(vmdk_file)
        return vmdk_file

    def _mount_vmdk(self, vmdk: Path) -> None:
        # sudo LIBGUESTFS_BACKEND=direct guestmount -a saarctf-testbox-disk001.vmdk -i --ro /mnt/tmp
        self._mnt_folder.mkdir(parents=True, exist_ok=True)
        if (self._mnt_folder / 'etc').exists():
            print('[.] already mounted?')
        else:
            print(f'[.] Mount {vmdk} ...')
            env = dict(os.environ.items())
            env['LIBGUESTFS_BACKEND'] = 'direct'
            subprocess.check_call(['guestmount', '-a', str(vmdk), '-i', '--ro', str(self._mnt_folder)], env=env)

    def _umount(self) -> None:
        subprocess.check_call(['umount', str(self._mnt_folder)])
        if self._mnt_folder.exists():
            self._mnt_folder.rmdir()

    def _pack_archive(self) -> None:
        # pack stuff into the archive
        print('[.] Pack image archive ...')
        filelist = [fname for fname in os.listdir(self._mnt_folder) if fname not in self.excludes_root]
        subprocess.check_call(['tar', '--xattrs', '--numeric-owner'] + self.excludes + ['-cpf', str(self.output_file)] + filelist,
                              cwd=self._mnt_folder)


class ArchiveCloudConverter:
    new_iptables_rules: list[str] = [
        '-A INPUT -p tcp --dport 22 -j ACCEPT',
        '-A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT',
        '-A INPUT -i eth0 -j DROP',
        '-A INPUT -i ens1 -j DROP',
    ]
    new_iptables6_rules: list[str] = [
        '-A INPUT -p tcp --dport 22 -j ACCEPT',
        '-A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT',
        '-A INPUT -j DROP',
    ]

    def __init__(self, image_archive: Path, output_file: Path, tmp_folder: Path) -> None:
        self.image_archive = image_archive.absolute()
        self.output_file = output_file.absolute()
        self._tmp_folder = tmp_folder

    def convert(self) -> None:
        self._tmp_folder.mkdir(parents=True, exist_ok=True)
        tmp2 = self._filter_archive(self.image_archive)
        self.image_archive.unlink(missing_ok=True)
        self.output_file.unlink(missing_ok=True)
        shutil.move(self._compress(tmp2), self.output_file)
        _print_filesize(self.output_file)

    def _compress(self, archive: Path) -> Path:
        if self.output_file.name.endswith('.tar.gz'):
            print('[.] Compressing ...')
            subprocess.check_call(['gzip', str(archive)])
            return archive.parent / f'{archive.name}.gz'
        elif self.output_file.name.endswith('.tar.xz'):
            print('[.] Compressing ...')
            subprocess.check_call(['xz', '-T', '0', str(archive)])
            return archive.parent / f'{archive.name}.xz'
        else:
            raise ValueError(f'Unknown compression format for {self.output_file.name}')

    def _filter_archive(self, archive: Path) -> Path:
        output = self._tmp_folder / 'tmp2.tar'
        dependencies_archive = self._pack_dependencies()
        with tarfile.open(archive, 'r') as fi:
            with tarfile.open(output, 'w', format=fi.format) as fo:
                for member in fi.getmembers():
                    if member.isdir() and not member.issym():
                        extracted = fi.extractfile(member)
                        fo.addfile(member, extracted)
                    elif member.isfile() and not member.issym():
                        extracted = fi.extractfile(member)
                        if extracted is None:
                            raise Exception('Could not extract file')
                        if member.name == 'root/.bash_profile':
                            extracted = self.filter_bash_profile(member, extracted)
                        elif member.name == 'etc/crontab':
                            extracted = self.filter_crontab(member, extracted)
                        elif member.name == 'etc/iptables/rules.v4':
                            extracted = self.filter_iptables(member, extracted)
                        elif member.name == 'etc/iptables/rules.v6':
                            extracted = self.filter_iptables6(member, extracted)
                        elif member.name == 'etc/initramfs-tools/conf.d/resume':
                            extracted = self.filter_resume(member, extracted)
                        fo.addfile(member, extracted)
                    else:
                        fo.addfile(member)
                with tarfile.open(dependencies_archive, 'r') as fi2:
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

        return output

    def _pack_dependencies(self) -> Path:
        output = self._tmp_folder / 'tmp3.tar'
        subprocess.check_call(['tar', '--numeric-owner', '-cpf', str(output), 'cloud-scripts'],
                              cwd=GlobalConfig.resources)
        return output

    def filter_bash_profile(self, member: tarfile.TarInfo, r: IO[bytes]) -> io.BytesIO:
        # Remove setup-network
        # Add setup-password --check
        lines = r.read().decode().split('\n')
        lines = [l if 'setup-network.py' not in l else '/root/setup-password.py --check' for l in lines]
        data = '\n'.join(lines).encode()
        member.size = len(data)
        return io.BytesIO(data)

    def filter_crontab(self, member: tarfile.TarInfo, r: IO[bytes]) -> io.BytesIO:
        # A cronjob is going to install Hetzner packages on the system on first boot
        lines = r.read().decode().split('\n')
        lines += ['@reboot root /cloud-scripts/install-hetzner-cloud.sh']
        data = '\n'.join(lines).encode() + b'\n'
        member.size = len(data)
        return io.BytesIO(data)

    def filter_iptables(self, member: tarfile.TarInfo, r: IO[bytes]) -> io.BytesIO:
        content = r.read().decode()
        content = content.replace('COMMIT', '\n'.join(self.new_iptables_rules) + '\nCOMMIT')
        data = content.encode()
        member.size = len(data)
        return io.BytesIO(data)

    def filter_iptables6(self, member: tarfile.TarInfo, r: IO[bytes]) -> io.BytesIO:
        content = r.read().decode()
        content = content.replace('COMMIT', '\n'.join(self.new_iptables6_rules) + '\nCOMMIT')
        data = content.encode()
        member.size = len(data)
        return io.BytesIO(data)

    def filter_resume(self, member: tarfile.TarInfo, r: IO[bytes]) -> io.BytesIO:
        data = b'RESUME=none\n'
        member.size = len(data)
        return io.BytesIO(data)
