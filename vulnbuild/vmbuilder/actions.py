from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from vulnbuild.config import GlobalConfig
from vulnbuild.hcl.hcl import HclBlock, HclArgument
from vulnbuild.hcl.parser import HclParser
from vulnbuild.project import ProjectConfig
from vulnbuild.services.services import Service
from vulnbuild.utils.initial_checks import apt_cacher_ng_present


@dataclass
class Action(ABC):
    @abstractmethod
    def provisioners(self, **kwargs: Any) -> list[HclBlock]:
        raise NotImplementedError()


@dataclass
class ScriptAction(Action):
    script: Path

    def provisioners(self, **kwargs: Any) -> list[HclBlock]:
        return [HclBlock(
            'provisioner', ['shell'], list(HclArgument.from_dict({
                'scripts': [str(self.script)]
            }))
        )]

    def __str__(self) -> str:
        return f'Script {self.script.relative_to(GlobalConfig.projects)}'


@dataclass
class PackerAction(Action):
    name: str
    provisioner_blocks: list[HclBlock]

    def provisioners(self, **kwargs: Any) -> list[HclBlock]:
        return self.provisioner_blocks

    @classmethod
    def from_file(cls, filename: Path) -> 'PackerAction':
        # with open(filename, 'r') as f:
        # return PackerAction(filename.name, yaml.safe_load(f))
        return PackerAction(filename.name, HclParser.parse(filename.read_text()).get_blocks('provisioner'))

    def __str__(self) -> str:
        return f'Packer commands {self.name}'

    def required_ssh_keypair(self) -> bool:
        return any('ssh_vulnbox' in block.to_string() for block in self.provisioner_blocks)


@dataclass
class AnsibleAction(Action):
    playbook: Path

    def provisioners(self, **kwargs: Any) -> list[HclBlock]:
        return [HclBlock(
            'provisioner', ['ansible'], list(HclArgument.from_dict({
                'playbook_file': str(self.playbook)
            }))
        )]

    def __str__(self) -> str:
        return f'Ansible playbook {self.playbook.relative_to(GlobalConfig.projects)}'


@dataclass
class AptCacherNgAction(Action):

    def provisioners(self, **kwargs: Any) -> list[HclBlock]:
        if apt_cacher_ng_present():
            return [HclBlock(
                'provisioner', ['shell'], list(HclArgument.from_dict({
                    'inline_shebang': '/bin/bash -e',
                    'inline': [
                        'set -eu',
                        "IP=$(/sbin/ip route | awk '/default/ { print $3 }')",
                        'echo Configuring apt cache, with ip = $IP',
                        'echo "Acquire::http { Proxy \\"http://$IP:3142\\"; }" > /etc/apt/apt.conf.d/01proxy',
                    ]
                }))
            )]
        else:
            return []

    def __str__(self) -> str:
        return 'Configure apt-cacher-ng if available'


@dataclass
class AptCacherNgScriptAction(ScriptAction):
    def provisioners(self, **kwargs: Any) -> list[HclBlock]:
        if apt_cacher_ng_present():
            return super().provisioners(**kwargs)
        else:
            return []

    def __str__(self) -> str:
        return 'Configure apt-cacher-ng if available'


@dataclass
class ServiceAction(Action):
    service: Service
    build_dir: Path

    def provisioners(self, tmp_dir: str = '/dev/shm', **kwargs: Any) -> list[HclBlock]:
        return [
            # Upload built files
            HclBlock(
                'provisioner', ['file'], list(HclArgument.from_dict({
                    'source': str(self.build_dir),
                    'destination': f'{tmp_dir}/'
                }))
            ),
            # Install
            HclBlock(
                'provisioner', ['shell'], list(HclArgument.from_dict({
                    'inline_shebang': '/bin/bash -e',
                    'inline': [
                        f'echo "===== Installing service {self.service.name} ... ====="',
                        f'cd {tmp_dir}/{self.service.name}',
                        '. ./gamelib/ci/buildscripts/prepare-install.sh',
                        './install.sh',
                        './gamelib/ci/buildscripts/post-install.sh',
                        'cd /',
                        f'rm -rf {tmp_dir}/{self.service.name}'
                    ],
                    'environment_vars': ['NO_DOCKER_SYSTEMD=1']
                }))
            )]

    def __str__(self) -> str:
        return f'Install service {self.service.name}'


class ActionFactory:
    def __init__(self, project: ProjectConfig, services: list[Service]) -> None:
        self.project = project
        self.services = services

    def create(self, f: Path) -> list[Action]:
        if f.suffix == '.sh':
            return [ScriptAction(f)]
        if f.name.endswith('.pkr.hcl'):
            return [PackerAction.from_file(f)]
        if f.name.endswith('.ansible.yaml'):
            return [AnsibleAction(f)]
        if f.name.endswith('_apt_cacher_ng'):
            return [AptCacherNgAction()]
        if f.name.endswith('_apt_cacher_ng.sh'):
            return [AptCacherNgScriptAction(f)]
        if f.name.endswith('_services'):
            return [ServiceAction(service, self.project.service_build_cache / service.name) for service in self.services]
        return []

    def create_many(self, files: list[Path]) -> list[Action]:
        result: list[Action] = []
        for file in files:
            result += self.create(file)
        return result
