from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TypeVar, Any, Generic, Type

from vulnbuild.project import ProjectConfig
from vulnbuild.services.services import Service


@dataclass
class BuildTask(ABC):
    name: str
    project: ProjectConfig

    @property
    def fullname(self) -> str:
        return self.name

    @property
    def task_basename(self) -> str | None:
        return None

    def __lt__(self, other: 'BuildTask') -> bool:
        return self.name < other.name


@dataclass
class ServiceBuildTask(BuildTask):
    service: Service

    @property
    def fullname(self) -> str:
        return 'service:' + self.name

    @property
    def task_basename(self) -> str:
        return 'service'


_BuildTaskType = TypeVar('_BuildTaskType', bound=BuildTask)


class Builder(ABC, Generic[_BuildTaskType]):
    @classmethod
    @abstractmethod
    def accepts(cls, task: BuildTask) -> bool:
        raise NotImplementedError

    @abstractmethod
    def is_built(self, task: _BuildTaskType) -> bool:
        raise NotImplementedError

    @abstractmethod
    def get_output_file(self, task: _BuildTaskType) -> Path | None:
        raise NotImplementedError

    def dependencies(self, task: _BuildTaskType) -> list[BuildTask]:
        return []

    @abstractmethod
    def build(self, task: _BuildTaskType) -> Any:
        raise NotImplementedError

    @abstractmethod
    def clean(self, task: _BuildTaskType) -> None:
        raise NotImplementedError
