import re
import subprocess
from pathlib import Path

from vulnbuild.project import ProjectConfig
from vulnbuild.vmbuilder.backends.backend import VmBuilderBackend
from vulnbuild.vmbuilder.build_targets import VmBuildTarget
from vulnbuild.config import GlobalConfig
from vulnbuild.hcl.hcl import HclFile
from vulnbuild.utils.initial_checks import cache_result


@cache_result
def get_physical_interface() -> str:
    links = subprocess.check_output(['ip', 'link'])
    interfaces = re.findall(r'\d+: ([A-Za-z0-9-_]+):', links.decode())
    for iface in interfaces:
        if iface.startswith('e'):
            return iface
    for iface in interfaces:
        if iface.startswith('w'):
            return iface
    return interfaces[0]


class VirtualboxBackend(VmBuilderBackend):
    def __init__(self, project: ProjectConfig) -> None:
        super().__init__(project)
        self._base_image_target = VmBuildTarget.from_hcl(
            'debian',
            self._project,
            GlobalConfig.default_targets_dir / 'debian-virtualbox' / 'source.pkr.hcl'
        )

    def shortname(self) -> str:
        return 'virtualbox'

    def dependencies(self, target: VmBuildTarget) -> list[VmBuildTarget]:
        if target.name == 'debian':
            return []
        return [self._base_image_target]

    def _output_file(self, target: VmBuildTarget) -> Path:
        return target.project.output_dir / target.name / f'{target.name}.ova'

    def get_output_file(self, task: VmBuildTarget) -> Path | None:
        return self._output_file(task)

    def is_registered(self, name: str) -> bool:
        output = subprocess.check_output(['vboxmanage', 'list', 'vms'])
        return f'"{name}"'.encode() in output

    def unregister(self, name: str) -> None:
        subprocess.check_call(['vboxmanage', 'unregistervm', '--delete', name])

    def is_built(self, target: VmBuildTarget) -> bool:
        return self._output_file(target).exists()

    def clean(self, target: VmBuildTarget) -> None:
        fname: Path = self._output_file(target)
        fname.unlink(missing_ok=True)
        if fname.parent.is_dir() and not any(fname.parent.iterdir()):
            fname.parent.rmdir()

    def export(self, target: VmBuildTarget) -> Path | str:
        raise NotImplementedError()

    def _packer_variables(self, target: VmBuildTarget, hcl: HclFile) -> dict[str, str]:
        variables = super()._packer_variables(target, hcl)
        variables['physical_interface'] = get_physical_interface()
        variables['debian_ova_file'] = str(self._output_file(self._base_image_target))
        return variables

    def _process_hcl(self, target: VmBuildTarget, hcl: HclFile) -> HclFile:
        for source in hcl.get_blocks('source'):
            if source.labels[0] in ('virtualbox-iso', 'virtualbox-ovf'):
                # set output file
                f = self._output_file(target)
                source.set_argument('output_directory', str(f.parent))
                source.set_argument('output_filename', str(f.name)[:-4])
        return hcl

    def build(self, target: VmBuildTarget, hcl: HclFile) -> Path | str | None:
        if target.name == 'debian':
            print('[!] This step might take some time to finish (up to 30min) without any visible progress.')
        super().build(target, hcl)
        return self._output_file(target)
