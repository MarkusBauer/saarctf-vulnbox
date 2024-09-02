import re
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import requests

from vulnbuild.config import GlobalConfig
from vulnbuild.hcl.hcl import HclFile
from vulnbuild.project import ProjectConfig
from vulnbuild.utils.initial_checks import cache_result
from vulnbuild.vmbuilder.build_targets import VmBuildTarget


@cache_result
def get_current_debian_version() -> str:
    response = requests.get('http://cdimage.debian.org/cdimage/release/')
    return re.findall(r'href="(\d+\.\d+.\d+)/"', response.text)[0]


class VmBuilderBackend(ABC):
    def __init__(self, project: ProjectConfig) -> None:
        self._project = project

    @abstractmethod
    def shortname(self) -> str:
        raise NotImplementedError()

    def dependencies(self, target: VmBuildTarget) -> list[VmBuildTarget]:
        return []

    @abstractmethod
    def is_registered(self, name: str) -> bool:
        """Return true if a registered VM/container/whatever could prevent the build"""
        raise NotImplementedError()

    @abstractmethod
    def unregister(self, name: str) -> None:
        raise NotImplementedError()

    @abstractmethod
    def is_built(self, target: VmBuildTarget) -> bool:
        raise NotImplementedError()

    @abstractmethod
    def clean(self, target: VmBuildTarget) -> None:
        raise NotImplementedError()

    @abstractmethod
    def export(self, target: VmBuildTarget) -> Path | str:
        raise NotImplementedError()

    @abstractmethod
    def get_output_file(self, task: VmBuildTarget) -> Path|None:
        raise NotImplementedError

    def action_variables(self) -> dict[str, Any]:
        return {}

    def _packer_variables(self, target: VmBuildTarget, hcl: HclFile) -> dict[str, str]:
        variables = {
            'project_name': self._project.name,
            'project_version': self._project.version,
            'target_name': target.name,
            'base': str(GlobalConfig.base),
            'project_output_dir': str(target.project.output_dir)
        }
        if target.packer_script and target.packer_script.get_variable('debian_version'):
            variables['debian_version'] = get_current_debian_version()
        return variables

    def _filter_known_variables(self, hcl: HclFile, variables: dict[str, str]) -> dict[str, str]:
        known_variables = set(b.labels[0] for b in hcl.get_blocks('variable'))
        return {k: v for k, v in variables.items() if k in known_variables}

    def _process_hcl(self, target: VmBuildTarget, hcl: HclFile) -> HclFile:
        return hcl

    def build(self, target: VmBuildTarget, hcl: HclFile) -> Path | str | None:
        hcl = self._process_hcl(target, hcl)
        variables = self._filter_known_variables(hcl, self._packer_variables(target, hcl))
        hcl_file: Path = target.packer_template.parent / f'temp-{target.packer_template.name}'
        hcl_file.write_text(hcl.to_string())

        subprocess.check_call(['packer', 'init', str(hcl_file)])
        cmd: list[str] = ['packer', 'build', '-force']
        for k, v in variables.items():
            cmd.append('-var')
            cmd.append(f'{k}={v}')
        cmd.append(str(hcl_file))
        subprocess.check_call(cmd, cwd=str(hcl_file.parent))

        hcl_file.unlink(missing_ok=True)

        return None


