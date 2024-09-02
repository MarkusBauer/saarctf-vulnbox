import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from vulnbuild.builds import BuildTask, Builder
from vulnbuild.config import GlobalConfig
from vulnbuild.converter.cloud_bundle import CloudBundleTask
from vulnbuild.converter.converter import ConverterTask, Converter
from vulnbuild.project import UploadConfig


@dataclass
class UploadTask(ConverterTask):
    base_file: Path
    upload_config: UploadConfig

    @property
    def fullname(self) -> str:
        return 'upload:' + self.name

    @property
    def task_basename(self) -> str | None:
        return 'upload'

    @property
    def doc(self) -> str:
        return f'Upload {self.base_file.name} to {self.upload_config.host}'


class UploadConverter(Converter[UploadTask]):
    def __init__(self) -> None:
        pass

    def get_conversion_targets(self, task: BuildTask, builder: Builder) -> Sequence[UploadTask]:
        result = []
        output = builder.get_output_file(task)
        if output:
            for uc in task.project.uploads:
                if uc.task == task.fullname:
                    result.append(
                        UploadTask(name=f'{task.name}:{uc.host}', project=task.project, base=task, base_file=output, upload_config=uc)
                    )
        return result

    @classmethod
    def accepts(cls, task: BuildTask) -> bool:
        return isinstance(task, UploadTask)

    def is_built(self, task: UploadTask) -> bool:
        return False

    def get_output_file(self, task: UploadTask) -> None:
        return None

    def build(self, task: UploadTask) -> Any:
        print(f'[.] Uploading {task.base_file.name} to {task.upload_config.host} ...')

        subprocess.check_call(['rsync', '-apP', str(task.base_file), f'{task.upload_config.host}:{task.upload_config.path}'])

        if task.upload_config.chmod:
            output = task.upload_config.path
            if task.upload_config.path.endswith('/'):
                output += '/' + task.base_file.name
            subprocess.check_call(['ssh', task.upload_config.host, 'chmod', oct(task.upload_config.chmod).replace('o', ''), output])

        print(f'[*] Uploaded {task.base_file.name} to {task.upload_config.host}.')

    def clean(self, task: UploadTask) -> None:
        pass
