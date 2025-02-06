import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from vulnbuild.builds import BuildTask, Builder
from vulnbuild.config import GlobalConfig
from vulnbuild.converter.cloud_bundle import CloudBundleTask
from vulnbuild.converter.converter import ConverterTask, Converter


@dataclass
class CloudImageTask(ConverterTask):
    bundle_file: Path

    @property
    def doc(self) -> str:
        return f'Create Hetzner Cloud Image from {self.bundle_file.name}'


class CloudImageConverter(Converter[CloudImageTask]):
    def __init__(self, name: str = '') -> None:
        self._contains_name = name

    def get_conversion_targets(self, task: BuildTask, builder: Builder) -> Sequence[CloudImageTask]:
        if isinstance(task, CloudBundleTask):
            bundle = builder.get_output_file(task)
            if bundle and (bundle.name.endswith('.tar.gz') or bundle.name.endswith('.tar.xz')) and self._contains_name in bundle.name:
                return [CloudImageTask(name=f'{task.name}:hetzner', project=task.project, base=task, bundle_file=bundle)]
        return []

    @classmethod
    def accepts(cls, task: BuildTask) -> bool:
        return isinstance(task, CloudImageTask)

    def is_built(self, task: CloudImageTask) -> bool:
        return False

    def get_output_file(self, task: CloudImageTask) -> None:
        return None

    def build(self, task: CloudImageTask) -> Any:
        print(f'[.] Building cloud image from {task.bundle_file.name} ...')
        if 'HCLOUD_TOKEN' not in os.environ:
            print('[!] You should have set the environment variable "HCLOUD_TOKEN"')
            raise Exception('Missing Hetzner Token (HCLOUD_TOKEN=...)')

        subprocess.check_call(['packer', 'build', '-var', f'archive_file={task.bundle_file.absolute()}', 'vulnbox-cloud.json'],
                              cwd=GlobalConfig.base)

        print(f'[*] Created cloud image.')

    def clean(self, task: CloudImageTask) -> None:
        pass
