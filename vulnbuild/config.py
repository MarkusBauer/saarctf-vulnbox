from dataclasses import dataclass
from pathlib import Path


class GlobalConfig:
    base: Path = Path(__file__).absolute().parent.parent
    resources: Path = base / 'resources'  # everything that might end up in an image
    projects = base / 'projects'
    default_scripts_dir: Path = projects / 'default' / 'scripts'
    default_targets_dir: Path = projects / 'default' / 'targets'
