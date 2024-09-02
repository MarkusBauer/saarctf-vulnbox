import os
import shutil
import subprocess
from pathlib import Path

from vulnbuild.builds import ServiceBuildTask, BuildTask, Builder
from vulnbuild.project import ProjectConfig
from vulnbuild.services.base_image import DefaultCiBaseImage
from vulnbuild.services.services import Service


class ServiceBuilder(Builder[ServiceBuildTask]):
    def __init__(self, project: ProjectConfig) -> None:
        self.project = project

    @classmethod
    def accepts(cls, task: BuildTask) -> bool:
        return isinstance(task, ServiceBuildTask)

    def pull(self, service: Service) -> None:
        repo = service.get_git_repo()
        if repo:
            print(f'[-] Service {service.name}: pull ...')
            repo.pull()
            repo.update_submodules()
            print(f'[*] Service {service.name}: updated.')
        else:
            print(f'[-] Service {service.name}: not a git repository')

    def pull_gamelib(self, service: Service) -> None:
        repo = service.get_gamelib_git_repo()
        if repo:
            print(f'[-] Service {service.name}: pull gamelib ...')
            repo.checkout('master')
            repo.pull()
            print(f'[*] Service {service.name}: gamelib updated.')
        else:
            print(f'[-] Service {service.name}: gamelib is not a git repository')

    def _cache_dir(self, service: Service) -> Path:
        return self.project.service_build_cache / service.name

    def get_output_file(self, task: ServiceBuildTask) -> Path | None:
        return self._cache_dir(task.service)

    def dependencies(self, task: ServiceBuildTask) -> list[BuildTask]:
        return []

    def is_built(self, task: ServiceBuildTask) -> bool:
        return self._cache_dir(task.service).exists()

    def clean(self, service: ServiceBuildTask, silent: bool = False) -> None:
        cache = self._cache_dir(service.service)
        if cache.exists():
            shutil.rmtree(cache)
            if not silent:
                print(f'[*] Cached build for service {service.name} removed.')
        elif not silent:
            print(f'[*] Service {service.name} not cached.')

    def build(self, task: ServiceBuildTask) -> None:
        # Create cache folder
        cache = self._cache_dir(task.service)
        image = task.service.get_build_image()
        self.clean(task)
        cache.mkdir(parents=True, exist_ok=True)
        cache.chmod(0o777)

        # ensure base image exists
        if image.startswith('saarsec/saarctf-ci-base'):
            img = DefaultCiBaseImage()
            if not img.exists():
                img.build(task.service)

        try:
            # Invoke Docker to build
            build_cmd = ' && '.join([
                'cp -r /opt/input/*.sh /opt/input/service /opt/input/servicename /opt/input/gamelib /opt/output/',
                '(timeout 3 /opt/input/gamelib/ci/buildscripts/test-and-configure-aptcache.sh || echo "no cache found.")',
                'cd /opt/output',
                './build.sh',
                f'chown -R {os.getuid()} .'
            ])
            cmd = ['docker', 'run', '-v', f'{task.service.folder}/:/opt/input:ro', '-v', f'{cache}/:/opt/output:rw', '--rm']
            cmd += [image]
            cmd += ['/bin/sh', '-c', build_cmd]
            print(f'[-] Invoking docker to build {task.service.name} ...')
            print('>', ' '.join(cmd))
            subprocess.check_call(cmd)
            print(f'[*] Service {task.service.name} has been built and cached.')
        except:
            shutil.rmtree(cache)
            raise
