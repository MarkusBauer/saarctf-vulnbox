import subprocess
from pathlib import Path


class GitRepo:
    def __init__(self, folder: Path) -> None:
        self.folder = folder

    @classmethod
    def clone(cls, folder: Path, remote: str) -> 'GitRepo':
        subprocess.check_call(['git', 'clone', remote, str(folder)])
        return cls(folder)

    @classmethod
    def is_git(cls, folder: Path) -> bool:
        return (folder / '.git').exists()

    def execute(self, cmd: list[str]) -> None:
        subprocess.check_call(['git'] + cmd, cwd=self.folder)

    def pull(self) -> None:
        self.execute(['pull'])

    def update_submodules(self) -> None:
        self.execute(['submodule', 'update', '--init', '--recursive'])

    def checkout(self, branch: str) -> None:
        self.execute(['checkout', branch])
