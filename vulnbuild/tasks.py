import os
import sys
from functools import partial
from pathlib import Path
from typing import Callable, Iterator, TypedDict, Literal, Any

from doit import task_params, get_var  # type: ignore
from doit.task import result_dep, clean_targets  # type: ignore
from doit.tools import check_timestamp_unchanged  # type: ignore

from vulnbuild.builds import BuildTask, ServiceBuildTask, Builder
from vulnbuild.config import GlobalConfig
from vulnbuild.converter.cloud_bundle import CloudBundleConverter
from vulnbuild.converter.cloud_bundle_encrypt import CloudBundleEncryptConverter
from vulnbuild.converter.cloud_image import CloudImageConverter, CloudImageTask
from vulnbuild.converter.converter import Converter, ConverterTask
from vulnbuild.converter.ova_encrypt import OvaEncryptConverter
from vulnbuild.converter.upload import UploadConverter, UploadTask
from vulnbuild.project import ProjectConfig
from vulnbuild.services.builder import ServiceBuilder
from vulnbuild.services.clone import ServiceCloneTask, ServiceCloner
from vulnbuild.targets.password import PasswordTask, PasswordBuilder
from vulnbuild.targets.ssh import SshKeyTask, SshKeyBuilder
from vulnbuild.ui import query_yes_no
from vulnbuild.utils.initial_checks import InitialCheckers
from vulnbuild.vmbuilder.build_targets import VmBuildTargetFactory, VmBuildTarget
from vulnbuild.vmbuilder.vmbuilder import VmBuilder


class DoitTask(TypedDict, total=False):
    name: str | None
    basename: str
    doc: str
    verbosity: int
    actions: list[str | Callable | tuple[Callable, list, dict]]
    clean: Literal[True] | list[Callable]
    targets: list[str | Path]
    task_dep: list[str]
    file_dep: list[str | Path]
    uptodate: list[Callable]
    params: list[dict[str, Any]]


class TaskCreator:
    def __init__(self, project: ProjectConfig) -> None:
        self.project = project
        self.services = project.get_services()
        self.service_tasks = [ServiceBuildTask(s.name, project, s) for s in self.services]
        self.service_builder = ServiceBuilder(project)
        self.vm_builder = VmBuilder(project, self.services)
        self.vms = VmBuildTargetFactory.from_project(self.project, self.vm_builder.get_backend().shortname())
        self.converters: list[Converter] = [
            OvaEncryptConverter('vulnbox'),
            CloudBundleConverter('box'),
            CloudBundleEncryptConverter('vulnbox'),
            CloudImageConverter('vulnbox'),
            UploadConverter(),
        ]
        self.converter_tasks: list[ConverterTask] = self._build_converter_tasks()

    def task_builder(self, task: BuildTask) -> Builder:
        if isinstance(task, ServiceBuildTask):
            return self.service_builder
        if isinstance(task, VmBuildTarget):
            return self.vm_builder
        if isinstance(task, PasswordTask):
            return PasswordBuilder()
        if isinstance(task, SshKeyTask):
            return SshKeyBuilder()
        if isinstance(task, ServiceCloneTask):
            return ServiceCloner()
        if isinstance(task, ConverterTask):
            for converter in self.converters:
                if converter.accepts(task):
                    return converter
        raise NotImplementedError(f'task_builder of {type(task)} {task}')

    def _build_converter_tasks(self) -> list[ConverterTask]:
        result: list[ConverterTask] = []
        for converter in self.converters:
            result += converter.get_conversion_targets(PasswordTask(self.project), PasswordBuilder())
            result += converter.get_conversion_targets(SshKeyTask(self.project), SshKeyBuilder())
            for service in self.service_tasks:
                result += converter.get_conversion_targets(service, self.task_builder(service))
            for vm in self.vms.values():
                result += converter.get_conversion_targets(vm, self.task_builder(vm))
            for conversion_target in result:
                result += converter.get_conversion_targets(conversion_target, self.task_builder(conversion_target))
        return result

    def _basic_task(self, build_task: BuildTask) -> DoitTask:
        builder = self.task_builder(build_task)

        task: DoitTask = {
            'name': build_task.name,
            'verbosity': 2,
            'task_dep': [],
            'file_dep': [],
            'uptodate': [partial(builder.is_built, build_task)]
        }

        basename = build_task.task_basename
        if basename is not None:
            task['basename'] = basename

        output = builder.get_output_file(build_task)
        if output is not None:
            task['targets'] = [output]
        for dep in builder.dependencies(build_task):
            task['task_dep'].append(dep.fullname)
            output = self.task_builder(dep).get_output_file(dep)
            if output is not None:
                task['uptodate'].append(check_timestamp_unchanged(str(output)))

        return task

    def get_initial_check_task(self) -> DoitTask:
        return {
            'basename': 'initial_check',
            'verbosity': 2,
            'actions': [InitialCheckers(self.project).check_required_programs]
        }

    def build_service(self, service: ServiceBuildTask, dryrun: bool = False) -> None:
        print(f'[=] Service {service.name}')
        if not dryrun:
            self.service_builder.build(service)
        else:
            print('f[-] Skipping VM build due to dry run.')

    def get_service_version_tasks(self) -> Iterator[DoitTask]:
        for service in sorted(self.service_tasks):
            task: DoitTask = {
                'name': service.name,
                'actions': [f"git -C '{service.service.folder}' rev-parse HEAD"]
            }
            if not service.service.exists:
                task['task_dep'] = [ServiceCloneTask(self.project, self.project.get_service_config(service.name)).fullname]
            yield task

    def get_service_tasks(self) -> Iterator[DoitTask]:
        for service in sorted(self.service_tasks):
            task = self._basic_task(service)
            task['task_dep'] = ['initial_check'] + task['task_dep']
            task['doc'] = f'Build Service {service.name} from ({service.service.folder})'
            task['actions'] = [(self.build_service, [service], {})]
            task['uptodate'].append(result_dep(f'_service_version:{service.name}'))
            task['clean'] = [partial(self.service_builder.clean, service)]
            yield task

    def get_service_pull_tasks(self) -> Iterator[DoitTask]:
        for service in sorted(self.services):
            task: DoitTask = {
                'name': service.name,
                'basename': 'pull-service',
                'verbosity': 2,
                'actions': [partial(self.service_builder.pull, service)]
            }
            if not service.exists:
                task['task_dep'] = [ServiceCloneTask(self.project, self.project.get_service_config(service.name)).fullname]
            yield task
            task = {
                'name': service.name,
                'basename': 'pull-gamelib',
                'verbosity': 2,
                'actions': [partial(self.service_builder.pull_gamelib, service)]
            }
            if not service.exists:
                task['task_dep'] = [ServiceCloneTask(self.project, self.project.get_service_config(service.name)).fullname]
            yield task

    def get_service_clone_tasks(self) -> Iterator[DoitTask]:
        yield {
            'basename': 'clone',
            'name': None,
            'doc': 'Clone all services'
        }
        for sc in self.project.services:
            task: DoitTask = self._simple_task(ServiceCloneTask(self.project, sc), doc=f'Clone service {sc.name}')
            yield task

    def build_vm(self, vm: VmBuildTarget, dryrun: bool = False, force: bool = False) -> None:
        print(f'[.] Building VM {vm.name} ...')
        if not dryrun:
            if self.vm_builder.get_backend().is_registered(vm.name):
                print(f'[!] Warning: VM {vm.name} already present.')
                if force or query_yes_no('Delete VM?', 'no'):
                    self.vm_builder.get_backend().unregister(vm.name)
            self.vm_builder.build(vm)
        else:
            print('f[-] Skipping VM build due to dry run.')

    def get_vm_tasks(self) -> Iterator[DoitTask]:
        for vm_name, vm in sorted(self.vms.items()):
            task = self._basic_task(vm)
            task['task_dep'] = ['initial_check', 'sshkey'] + task['task_dep']
            task['doc'] = f'Build VM {vm.name} (from file {vm.packer_template})'
            task['actions'] = [(self.build_vm, [vm], {})]
            task['params'] = [{'name': 'force', 'long': 'force', 'type': bool, 'default': False}]
            task['clean'] = [partial(self.vm_builder.clean, vm)]
            yield task

    def _simple_task(self, target: BuildTask, doc: str | None = None) -> DoitTask:
        builder = self.task_builder(target)
        task = self._basic_task(target)
        task['actions'] = [(builder.build, [target], {})]
        task['clean'] = [partial(builder.clean, target)]
        if target.task_basename is None and task['name'] is not None:
            task['basename'] = task['name']
            del task['name']
        if doc:
            task['doc'] = doc
        return task

    def get_simple_tasks(self) -> Iterator[DoitTask]:
        yield self._simple_task(PasswordTask(self.project), doc='Create password for encrypted vulnbox archives')
        yield self._simple_task(SshKeyTask(self.project), doc='Create orga SSH key')

    def get_converter_tasks(self) -> Iterator[DoitTask]:
        for target in self.converter_tasks:
            task = self._simple_task(target, doc=target.doc)
            if isinstance(target, CloudImageTask) or isinstance(target, UploadTask):
                del task['uptodate']
            yield task


class TaskCreatorFactory:
    def __init__(self) -> None:
        self._creator: TaskCreator | None = None

    def _get_task_creator(self) -> TaskCreator:
        if not self._creator:
            project_name: str = get_var('project', os.environ.get('PROJECT_NAME', ''))
            if not project_name or not (GlobalConfig.projects / project_name).exists():
                print(f'[!] No project named "{project_name}"')
                print('    Use \'vulnbuild project=abc\' or \'PROJECT_NAME=abc vulnbuild\' to set a project.')
                print('')
                raise FileNotFoundError(GlobalConfig.projects / project_name)
            else:
                project = ProjectConfig.from_path(GlobalConfig.projects / project_name)
                self._creator = TaskCreator(project)
                self._print_project(project)
        return self._creator

    def with_project(self, f: Callable[[TaskCreator], DoitTask | Iterator[DoitTask]]) -> Callable[[], DoitTask | Iterator[DoitTask]]:
        def task_creator() -> DoitTask | Iterator[DoitTask]:
            return f(self._get_task_creator())

        return task_creator

    def get_task_builders(self) -> dict[str, Callable[[], DoitTask | Iterator[DoitTask]] | dict]:
        return {
            'task_initial_check': self.with_project(TaskCreator.get_initial_check_task),
            'task_vm': self.with_project(TaskCreator.get_vm_tasks),
            'task_pull-service': self.with_project(TaskCreator.get_service_pull_tasks),
            'task_service': self.with_project(TaskCreator.get_service_tasks),
            'task__service_version': self.with_project(TaskCreator.get_service_version_tasks),
            'task_clone': self.with_project(TaskCreator.get_service_clone_tasks),
            'task_simple': self.with_project(TaskCreator.get_simple_tasks),
            'task_converter': self.with_project(TaskCreator.get_converter_tasks),

            'DOIT_CONFIG': {
                # 'default_tasks': ['list']
            }
        }

    def _print_project(self, project: ProjectConfig) -> None:
        print(f'[*] Project "{project.name}"')
        print(f'    Builder: {project.vm_builder}')
        for service in project.get_services():
            if service.exists:
                print(f'    - Service {service.name}')
            else:
                print(f'    - [!] Service {service.name}  (not cloned yet)')
        sys.stdout.flush()
