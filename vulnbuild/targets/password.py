import secrets
import string
from dataclasses import dataclass
from pathlib import Path

from vulnbuild.builds import BuildTask, Builder
from vulnbuild.config import GlobalConfig
from vulnbuild.project import ProjectConfig


@dataclass
class PasswordTask(BuildTask):
    def __init__(self, project: ProjectConfig) -> None:
        super().__init__('password', project)

    @property
    def password_file(self) -> Path:
        return self.project.output_dir / 'password.txt'

    def get_password(self) -> str:
        """Read the current password IF this task has already been built"""
        return self.password_file.read_text(encoding='utf-8').strip()


class PasswordBuilder(Builder[PasswordTask]):
    _password_chars = ''.join(c for c in string.ascii_letters + string.digits if c not in {'O', 'o', '0', 'l', 'I'})

    @classmethod
    def accepts(cls, task: BuildTask) -> bool:
        return isinstance(task, PasswordTask)

    def is_built(self, task: PasswordTask) -> bool:
        return task.password_file.exists()

    def get_output_file(self, task: PasswordTask) -> Path:
        return task.password_file

    def build(self, task: PasswordTask) -> str:
        try:
            passwd = task.get_password()
            print('[.] Using existing password.txt')
            return passwd
        except FileNotFoundError:
            task.password_file.parent.mkdir(parents=True, exist_ok=True)
            passwd = self._generate_password()
            task.password_file.write_text(passwd, encoding='utf-8')
            print(f'[*] Generated new password ({self.get_output_file(task).relative_to(GlobalConfig.base)})')
            return passwd

    def clean(self, task: PasswordTask) -> None:
        print(f'[.] Not removing password ({self.get_output_file(task).relative_to(GlobalConfig.base)}), remove manually to recreate.')
        pass

    def _generate_password(self) -> str:
        return ''.join(secrets.choice(self._password_chars) for _ in range(16))
