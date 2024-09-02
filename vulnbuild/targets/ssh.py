import subprocess
from dataclasses import dataclass
from pathlib import Path

from vulnbuild.builds import BuildTask, Builder
from vulnbuild.config import GlobalConfig
from vulnbuild.project import ProjectConfig


@dataclass
class SshKeyTask(BuildTask):
    def __init__(self, project: ProjectConfig) -> None:
        super().__init__('sshkey', project)

    @property
    def private_key_file(self) -> Path:
        return self.project.output_dir / 'ssh_vulnbox'

    @property
    def public_key_file(self) -> Path:
        return self.project.output_dir / 'ssh_vulnbox.pub'


class SshKeyBuilder(Builder[SshKeyTask]):
    @classmethod
    def accepts(cls, task: BuildTask) -> bool:
        return isinstance(task, SshKeyTask)

    def is_built(self, task: SshKeyTask) -> bool:
        return task.private_key_file.exists() and task.public_key_file.exists()

    def get_output_file(self, task: SshKeyTask) -> Path:
        return task.private_key_file

    def build(self, task: SshKeyTask) -> str:
        if not task.private_key_file.exists():
            self._generate_keypair(task.private_key_file)
        else:
            print('[.] Using existing SSH key')
        return str(task.private_key_file)

    def clean(self, task: SshKeyTask) -> None:
        print(f'[.] Not removing ssh keypair ({self.get_output_file(task).relative_to(GlobalConfig.base)}), remove manually to recreate.')
        pass

    def _generate_keypair(self, f: Path) -> None:
        f.parent.mkdir(parents=True, exist_ok=True)
        pubkey = f.parent / f'{f.name}.pub'
        pubkey.unlink(missing_ok=True)

        # might be '-t ed25519' in the future
        subprocess.check_call(['ssh-keygen', '-t', 'rsa', '-b', '2048', '-f', str(f.absolute()), '-N', '', '-C', 'CTF Orga'])
        print(f'[*] Generated new SSH keys ({f.relative_to(GlobalConfig.base)})')
