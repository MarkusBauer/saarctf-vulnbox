from dataclasses import dataclass
from pathlib import Path

import yaml

from vulnbuild.services.git import GitRepo


@dataclass
class Service:
    name: str
    folder: Path
    ci_config: dict | None = None

    def __post_init__(self) -> None:
        if not self.name or self.name != self.folder.name:
            raise ValueError(f'Invalid service name: {repr(self.name)}')

    @property
    def exists(self) -> bool:
        return self.folder.exists()

    def get_ci_config(self) -> dict | None:
        if self.ci_config is None:
            try:
                with open(self.folder / '.gitlab-ci.yml', 'r') as f:
                    self.ci_config = yaml.safe_load(f)
            except FileNotFoundError:
                pass
        return self.ci_config

    @classmethod
    def from_folder(cls, folder: Path) -> 'Service':
        return Service(name=folder.name, folder=folder)

    def __lt__(self, other: 'Service') -> bool:
        return self.name.lower() < other.name.lower()

    def __gt__(self, other: 'Service') -> bool:
        return self.name.lower() > other.name.lower()

    def get_build_image(self) -> str:
        return (self.get_ci_config() or {}).get('build', {}).get('image', 'saarsec/saarctf-ci-base:latest')

    def get_git_repo(self) -> GitRepo | None:
        if GitRepo.is_git(self.folder):
            return GitRepo(self.folder)
        return None

    def get_gamelib_git_repo(self) -> GitRepo | None:
        if GitRepo.is_git(self.folder / 'gamelib'):
            return GitRepo(self.folder / 'gamelib')
        return None

