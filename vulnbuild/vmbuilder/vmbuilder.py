from pathlib import Path

from vulnbuild.builds import BuildTask, ServiceBuildTask, Builder
from vulnbuild.config import GlobalConfig
from vulnbuild.hcl.hcl import HclFile, HclBlock
from vulnbuild.hcl.parser import concat_lists
from vulnbuild.project import ProjectConfig
from vulnbuild.services.services import Service
from vulnbuild.targets.password import PasswordTask
from vulnbuild.vmbuilder.actions import Action, ActionFactory, ServiceAction, PackerAction
from vulnbuild.vmbuilder.backends.backend import VmBuilderBackend
from vulnbuild.vmbuilder.backends.containers import PodmanBackend, DockerBackend
from vulnbuild.vmbuilder.backends.virtualbox import VirtualboxBackend
from vulnbuild.vmbuilder.build_targets import VmBuildTarget


def builder_backend_factory(project: ProjectConfig) -> VmBuilderBackend:
    match project.vm_builder:
        case 'virtualbox':
            return VirtualboxBackend(project)
        case 'docker':
            return DockerBackend(project)
        case 'podman':
            return PodmanBackend(project)
        case _:
            raise ValueError(f'Invalid project vm_builder: {project.vm_builder}')


class VmBuilder(Builder[VmBuildTarget]):
    # get pre-built services
    # generate a list of actions from the scripts
    # select a backend
    # run it

    def __init__(self, project: ProjectConfig, services: list[Service]) -> None:
        self.project = project
        self.services = services
        self._backend: VmBuilderBackend | None = None

    @classmethod
    def accepts(cls, task: BuildTask) -> bool:
        return isinstance(task, ServiceBuildTask)

    def get_backend(self) -> VmBuilderBackend:
        if self._backend is None:
            self._backend = builder_backend_factory(self.project)
        return self._backend

    def get_build_order(self, target: VmBuildTarget) -> list[VmBuildTarget]:
        """Resolve dependencies recursively"""
        backend = self.get_backend()
        result = [target]
        unresolved = 1
        while unresolved > 0:
            new_targets = backend.dependencies(result[unresolved - 1])
            for target in new_targets:
                if target not in result:
                    result = [target] + result
                    unresolved += 1
            unresolved -= 1
        return result

    def _files_from_dir(self, d: Path) -> dict[str, Path]:
        if not d.is_dir():
            return {}
        return {f.name: f for f in d.iterdir() if f.is_file()}

    def _files_for_target(self, target: VmBuildTarget) -> list[Path]:
        """
        Scripts, deduplicated by filename.
        <project-dir>/scripts has precedence over global scripts.
        scripts/vulbox-vbox/ before scripts/vulnbox/ before scripts/vbox/ before scripts/
        """
        backend = self.get_backend()
        files: dict[str, Path] = {}
        files.update(self._files_from_dir(GlobalConfig.default_scripts_dir))
        files.update(self._files_from_dir(GlobalConfig.default_scripts_dir / backend.shortname()))
        files.update(self._files_from_dir(GlobalConfig.default_scripts_dir / target.name))
        files.update(self._files_from_dir(GlobalConfig.default_scripts_dir / f'{target.name}-{backend.shortname()}'))
        files.update(self._files_from_dir(self.project.scripts_dir))
        files.update(self._files_from_dir(self.project.scripts_dir / backend.shortname()))
        files.update(self._files_from_dir(self.project.scripts_dir / target.name))
        files.update(self._files_from_dir(self.project.scripts_dir / f'{target.name}-{backend.shortname()}'))
        return [files[n] for n in sorted(files.keys())]

    def find_actions(self, target: VmBuildTarget) -> list[Action]:
        files: list[Path] = self._files_for_target(target)
        return ActionFactory(self.project, self.services).create_many(files)

    def _hcl_buildscript(self, target: VmBuildTarget) -> HclFile:
        if not target.packer_script:
            raise ValueError('No packer script found')
        script: HclFile = target.packer_script.clone()

        # add custom provisioners
        for build_block in script.get_blocks('build'):
            i = 0
            while i < len(build_block.children):
                b = build_block.children[i]
                if isinstance(b, HclBlock) and b.type == 'vulnbuild':
                    build_block.children = build_block.children[:i] + self._hcl_provisioners(target, b) + build_block.children[i + 1:]
                i += 1

        return script

    def _hcl_provisioners(self, target: VmBuildTarget, b: HclBlock) -> list[HclBlock]:
        if b.labels[0] == 'actions':
            actions = self.find_actions(target)
            vars = self.get_backend().action_variables()
            return concat_lists(a.provisioners(**vars) for a in actions)
        else:
            raise KeyError(f'Unknown vulnbuild type: {b.labels}')

    def build(self, target: VmBuildTarget) -> None:
        print(f'[-] Invoking packer to build {target.name} ...')
        backend = self.get_backend()
        result = backend.build(target, self._hcl_buildscript(target))
        if result is None:
            result = backend.export(target)
        print(f'[*] Created {result}')

    def is_built(self, target: VmBuildTarget) -> bool:
        return self.get_backend().is_built(target)

    def get_output_file(self, task: VmBuildTarget) -> Path | None:
        return self.get_backend().get_output_file(task)

    def dependencies(self, task: VmBuildTarget) -> list[BuildTask]:
        dependencies: list[BuildTask] = list(self.get_backend().dependencies(task))
        for action in self.find_actions(task):
            if isinstance(action, ServiceAction):
                dependencies.append(ServiceBuildTask(action.service.name, self.project, action.service))
            elif isinstance(action, PackerAction):
                if action.required_ssh_keypair():
                    dependencies.append(PasswordTask(self.project))
        return dependencies

    def clean(self, task: VmBuildTarget) -> None:
        self.get_backend().clean(task)
