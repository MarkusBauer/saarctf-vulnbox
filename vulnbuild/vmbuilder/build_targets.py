from dataclasses import dataclass
from pathlib import Path

from vulnbuild.builds import BuildTask
from vulnbuild.config import GlobalConfig
from vulnbuild.hcl.hcl import HclFile
from vulnbuild.hcl.parser import HclParser
from vulnbuild.project import ProjectConfig


@dataclass
class VmBuildTarget(BuildTask):
    packer_template: Path
    packer_script: HclFile | None = None

    @property
    def fullname(self) -> str:
        return 'vm:' + self.name

    @property
    def task_basename(self) -> str | None:
        return 'vm'

    def __str__(self) -> str:
        return f'BuildTarget(name={self.name}, packer_template={self.packer_template})'

    @classmethod
    def from_hcl(cls, name: str, project: ProjectConfig, f: Path) -> 'VmBuildTarget':
        return VmBuildTarget(name, project, f, packer_script=HclParser.parse(f.read_text()))


class VmBuildTargetFactory:
    @classmethod
    def from_dir(cls, d: Path, project: ProjectConfig, builder: str) -> list['VmBuildTarget']:
        if not d.is_dir():
            return []
        suffix = f'-{builder}.pkr.hcl'
        result = []
        for f in d.iterdir():
            if f.is_file() and f.name.endswith(suffix) and not f.name.startswith('temp-'):
                name = f.name[:-len(suffix)]
                result.append(VmBuildTarget.from_hcl(name, project, f))
            elif f.is_dir() and f.name.endswith(f'-{builder}'):
                f2 = f / 'source.pkr.hcl'
                if f2.exists() and f2.is_file():
                    name = f.name[:-len(builder) - 1]
                    result.append(VmBuildTarget.from_hcl(name, project, f2))
        return result

    @classmethod
    def from_project(cls, project: ProjectConfig, builder: str) -> dict[str, VmBuildTarget]:
        targets = {t.name: t for t in cls.from_dir(GlobalConfig.default_targets_dir, project, builder)}
        targets.update({t.name: t for t in cls.from_dir(project.targets_dir, project, builder)})
        return targets
