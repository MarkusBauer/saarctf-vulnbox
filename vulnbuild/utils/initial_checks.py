import functools
import subprocess
import sys
from typing import ParamSpec, TypeVar, Callable

import requests

from vulnbuild.project import ProjectConfig

Param = ParamSpec("Param")
RetType = TypeVar("RetType")


def cache_result(func: Callable[Param, RetType]) -> Callable[Param, RetType]:
    result: list[RetType] = []

    @functools.wraps(func)
    def cached_func(*args: Param.args, **kwargs: Param.kwargs) -> RetType:
        if not result:
            result.append(func(*args, **kwargs))
        return result[0]

    return cached_func


@cache_result
def assert_docker() -> None:
    try:
        subprocess.check_call(['docker', 'ps'], stdout=subprocess.DEVNULL, timeout=10)
    except subprocess.CalledProcessError:
        print('Docker is required in order to build the services. Please install docker.', file=sys.stderr)
        raise Exception('Tool missing: Docker')


@cache_result
def assert_podman() -> None:
    try:
        subprocess.check_call(['podman', 'ps'], stdout=subprocess.DEVNULL, timeout=10)
    except subprocess.CalledProcessError:
        print('Podman is required in order to build this image. Please podman docker.', file=sys.stderr)
        raise Exception('Tool missing: Podman')


@cache_result
def assert_packer() -> None:
    try:
        subprocess.check_call(['packer', '--version'], stdout=subprocess.DEVNULL, timeout=10)
    except subprocess.CalledProcessError:
        print('Packer (https://packer.io) is required in order to build the vulnbox. Please install packer.', file=sys.stderr)
        raise Exception('Tool missing: Packer')


@cache_result
def assert_virtualbox() -> None:
    try:
        subprocess.check_call(['vboxmanage', '--version'], stdout=subprocess.DEVNULL, timeout=10)
    except subprocess.CalledProcessError:
        print('Virtualbox is required in order to build the vulnbox. Please install Virtualbox.', file=sys.stderr)
        raise Exception('Tool missing: Virtualbox')


@cache_result
def apt_cacher_ng_present() -> bool:
    try:
        response = requests.get('http://localhost:3142/', timeout=1)
        if 'Apt-Cacher' in response.text:
            print('[*] Local apt-cacher-ng will be used to speed up build')
            return True
    except requests.RequestException:
        print('[!] Hint: Install apt-cacher-ng to speed up builds')
    return False


class InitialCheckers:
    def __init__(self, project: ProjectConfig) -> None:
        self.project = project

    def check_required_programs(self) -> None:
        assert_docker()
        match self.project.vm_builder:
            case 'virtualbox':
                assert_packer()
                assert_virtualbox()
            case 'podman':
                assert_packer()
                assert_podman()
            case _:
                assert_packer()
