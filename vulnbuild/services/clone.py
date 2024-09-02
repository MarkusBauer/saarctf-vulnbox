from dataclasses import dataclass
from pathlib import Path
from typing import Any

from vulnbuild.builds import BuildTask, Builder
from vulnbuild.config import GlobalConfig
from vulnbuild.project import ServiceConfig, ProjectConfig
from vulnbuild.services.git import GitRepo


@dataclass
class ServiceCloneTask(BuildTask):
    config: ServiceConfig

    def __init__(self, project: ProjectConfig, sc: ServiceConfig) -> None:
        super().__init__(sc.name, project)
        self.config = sc

    @property
    def fullname(self) -> str:
        return f'clone:{self.name}'

    @property
    def task_basename(self) -> str | None:
        return 'clone'


class ServiceCloner(Builder[ServiceCloneTask]):
    @classmethod
    def accepts(cls, task: BuildTask) -> bool:
        return isinstance(task, ServiceCloneTask)

    def is_built(self, task: ServiceCloneTask) -> bool:
        return self.get_output_file(task).exists()

    def get_output_file(self, task: ServiceCloneTask) -> Path:
        return task.project.service_dir / task.config.name

    def build(self, task: ServiceCloneTask) -> Any:
        print(f'[.] Cloning service {task.name} ...')
        task.project.service_dir.mkdir(parents=True, exist_ok=True)
        repo = GitRepo.clone(self.get_output_file(task), task.config.remote)
        repo.update_submodules()
        print(f'[*] Cloned service {task.name} to {repo.folder.relative_to(GlobalConfig.base)}')
        return str(repo.folder)

    def clean(self, task: ServiceCloneTask) -> None:
        pass
