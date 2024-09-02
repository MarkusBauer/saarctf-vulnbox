import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from vulnbuild.builds import BuildTask, Builder
from vulnbuild.converter.cloud_bundle import CloudBundleTask
from vulnbuild.converter.converter import ConverterTask, Converter
from vulnbuild.targets.password import PasswordTask


@dataclass
class CloudBundleEncryptTask(ConverterTask):
    bundle_file: Path

    @property
    def doc(self) -> str:
        return f'Encrypt Cloud Bundle {self.bundle_file.name}'


class CloudBundleEncryptConverter(Converter[CloudBundleEncryptTask]):
    def __init__(self, name: str = '') -> None:
        self._contains_name = name

    def get_conversion_targets(self, task: BuildTask, builder: Builder) -> Sequence[CloudBundleEncryptTask]:
        if isinstance(task, CloudBundleTask):
            bundle = builder.get_output_file(task)
            if bundle and (bundle.name.endswith('.tar.gz') or bundle.name.endswith('.tar.xz')) and self._contains_name in bundle.name:
                return [CloudBundleEncryptTask(name=f'{task.name}:gpg', project=task.project, base=task, bundle_file=bundle)]
        return []

    @classmethod
    def accepts(cls, task: BuildTask) -> bool:
        return isinstance(task, CloudBundleEncryptTask)

    def is_built(self, task: CloudBundleEncryptTask) -> bool:
        return self.get_output_file(task).exists()

    def get_output_file(self, task: CloudBundleEncryptTask) -> Path:
        return task.bundle_file.parent / f'{task.bundle_file.name}.gpg'

    def dependencies(self, task: CloudBundleEncryptTask) -> list[BuildTask]:
        return super().dependencies(task) + [PasswordTask(task.project)]

    def build(self, task: CloudBundleEncryptTask) -> Any:
        print(f'[.] Encrypting file {task.bundle_file.name} ...')

        output = self.get_output_file(task)
        output.parent.mkdir(parents=True, exist_ok=True)
        passwd = PasswordTask(task.project).get_password()
        subprocess.check_call(['gpg', '--batch', '--passphrase', passwd, '--no-options', '-c', str(task.bundle_file)])

        print(f'[.] Created file {output.name} ...')
        return str(output)

    def clean(self, task: CloudBundleEncryptTask) -> None:
        self.get_output_file(task).unlink(missing_ok=True)
