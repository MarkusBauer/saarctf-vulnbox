from pathlib import Path
from typing import Any

from vulnbuild.hcl.hcl import HclFile
from vulnbuild.vmbuilder.backends.backend import VmBuilderBackend
from vulnbuild.vmbuilder.build_targets import VmBuildTarget


class ContainerBackend(VmBuilderBackend):
    def get_output_file(self, task: VmBuildTarget) -> Path:
        return task.project.output_dir / f'{self.shortname()}-image-{task.name}.tar'

    def is_registered(self, name: str) -> bool:
        return False

    def unregister(self, name: str) -> None:
        raise NotImplementedError()

    def is_built(self, target: VmBuildTarget) -> bool:
        return self.get_output_file(target).exists()

    def clean(self, target: VmBuildTarget) -> None:
        fname: Path = self.get_output_file(target)
        fname.unlink(missing_ok=True)

    def export(self, target: VmBuildTarget) -> Path | str:
        raise NotImplementedError()

    def action_variables(self) -> dict[str, Any]:
        return {'tmp_dir': '/tmp'}

    def _process_hcl(self, target: VmBuildTarget, hcl: HclFile) -> HclFile:
        for source in hcl.get_blocks('source'):
            if source.labels[0] == self.shortname():
                # set output file
                source.set_argument('export_path', str(self.get_output_file(target)))
        return hcl

    def build(self, target: VmBuildTarget, hcl: HclFile) -> Path | str | None:
        super().build(target, hcl)
        return self.get_output_file(target)


class PodmanBackend(ContainerBackend):
    def shortname(self) -> str:
        return 'podman'


class DockerBackend(ContainerBackend):
    def shortname(self) -> str:
        return 'docker'
