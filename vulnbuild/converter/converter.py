from abc import abstractmethod
from dataclasses import dataclass
from typing import TypeVar, Generic, Sequence

from vulnbuild.builds import Builder, BuildTask


@dataclass
class ConverterTask(BuildTask):
    base: BuildTask

    @property
    def doc(self) -> str | None:
        return None


_BuildTaskT = TypeVar('_BuildTaskT', bound=ConverterTask)


class Converter(Builder[_BuildTaskT], Generic[_BuildTaskT]):
    @abstractmethod
    def get_conversion_targets(self, task: BuildTask, builder: Builder) -> Sequence[_BuildTaskT]:
        """offer existing targets, get new ones back"""
        raise NotImplementedError()

    def dependencies(self, task: _BuildTaskT) -> list[BuildTask]:
        return [task.base]
