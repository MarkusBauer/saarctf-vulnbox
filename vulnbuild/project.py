from pathlib import Path

from dataclasses import dataclass, field

import yaml

from vulnbuild.config import GlobalConfig
from vulnbuild.services.services import Service


@dataclass
class UploadConfig:
    task: str
    host: str
    path: str
    chmod: int | None = None

    @classmethod
    def from_dict(cls, uc: dict) -> 'UploadConfig':
        return cls(**uc)


@dataclass
class ServiceConfig:
    name: str
    remote: str

    @classmethod
    def from_dict(cls, sc: dict) -> 'ServiceConfig':
        return cls(**sc)


@dataclass
class ProjectConfig:
    root: Path
    name: str = ''
    title: str = ''
    version: str = ''
    vm_builder: str = ''
    uploads: list[UploadConfig] = field(default_factory=list)
    services: list[ServiceConfig] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.name == '':
            self.name = self.root.name
        for i, uc in enumerate(self.uploads):
            if isinstance(uc, dict):
                self.uploads[i] = UploadConfig.from_dict(uc)
        for i, sc in enumerate(self.services):
            if isinstance(sc, dict):
                self.services[i] = ServiceConfig.from_dict(sc)

    @classmethod
    def from_dict(cls, root: Path, d: dict) -> 'ProjectConfig':
        return ProjectConfig(root=root, **d)

    @classmethod
    def from_path(cls, path: Path) -> 'ProjectConfig':
        if not path.exists():
            raise FileNotFoundError(path)
        config = path / 'vulnbuild.yaml'
        if config.exists():
            with open(config, 'r') as f:
                d = yaml.safe_load(f)
            return ProjectConfig.from_dict(path, d)
        else:
            return ProjectConfig(name=path.name, root=path)

    @property
    def service_dir(self) -> Path:
        return self.root / 'services'

    @property
    def scripts_dir(self) -> Path:
        return self.root / 'scripts'

    @property
    def targets_dir(self) -> Path:
        return self.root / 'targets'

    @property
    def service_build_cache(self) -> Path:
        return GlobalConfig.base / ".build_cache" / self.root.name

    @property
    def output_dir(self) -> Path:
        return GlobalConfig.base / 'output' / self.root.name

    def get_services(self) -> list[Service]:
        services = {}
        for sc in self.services:
            services[sc.name] = Service(sc.name, self.service_dir / sc.name)
        if self.service_dir.is_dir():
            for d in self.service_dir.iterdir():
                s = Service.from_folder(d.resolve())
                services[s.name] = s
        return list(services.values())

    def get_service_config(self, name: str) -> ServiceConfig:
        for sc in self.services:
            if sc.name == name:
                return sc
        raise KeyError(f'Service {name} not configured')
