import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from vulnbuild.builds import BuildTask, Builder
from vulnbuild.converter.converter import ConverterTask, Converter
from vulnbuild.targets.password import PasswordTask
from vulnbuild.vmbuilder.build_targets import VmBuildTarget


@dataclass
class OvaEncryptTask(ConverterTask):
    ova_file: Path

    @property
    def doc(self) -> str:
        return f'Encrypt VM image {self.ova_file.name}'


class OvaEncryptConverter(Converter[OvaEncryptTask]):
    def __init__(self, name: str = '') -> None:
        self._contains_name = name

    def get_conversion_targets(self, task: BuildTask, builder: Builder) -> Sequence[OvaEncryptTask]:
        if isinstance(task, VmBuildTarget):
            ova = builder.get_output_file(task)
            if ova and ova.suffix == '.ova' and self._contains_name in ova.name:
                return [OvaEncryptTask(name=f'vm:{task.name}:7z', project=task.project, base=task, ova_file=ova)]
        return []

    @classmethod
    def accepts(cls, task: BuildTask) -> bool:
        return isinstance(task, OvaEncryptTask)

    def is_built(self, task: OvaEncryptTask) -> bool:
        return self.get_output_file(task).exists()

    def get_output_file(self, task: OvaEncryptTask) -> Path:
        return task.ova_file.parent / f'{task.ova_file.name[:-4]}.7z'

    def dependencies(self, task: OvaEncryptTask) -> list[BuildTask]:
        return super().dependencies(task) + [PasswordTask(task.project)]

    def build(self, task: OvaEncryptTask) -> Any:
        print(f'[.] Encrypting file {task.ova_file.name} ...')

        output = self.get_output_file(task)
        output.parent.mkdir(parents=True, exist_ok=True)
        passwd = PasswordTask(task.project).get_password()
        subprocess.run(['7z', 'a', '-mx9', f'-p{passwd}', str(output), str(task.ova_file)])

        print(f'[.] Created file {output.name} ...')
        return str(output)

    def clean(self, task: OvaEncryptTask) -> None:
        self.get_output_file(task).unlink(missing_ok=True)
