import json
import os
import sys
from typing import Iterable

import doit  # type: ignore

from vulnbuild.config import GlobalConfig
from vulnbuild.tasks import TaskCreatorFactory


def import_credentials() -> None:
    try:
        data = (GlobalConfig.base / 'credentials.json').read_text()
    except FileNotFoundError:
        return
    for k, v in json.loads(data).items():
        if k not in os.environ:
            os.environ[k] = v


class CliChecker:
    def get_targets(self, args: list[str]) -> list[str]:
        return [a for a in args if '=' not in a and not a.startswith('-')]

    def _earliest_of(self, targets: list[str], prefixes: Iterable[str]) -> int | None:
        for i, target in enumerate(targets):
            if any(prefix for prefix in prefixes if target.startswith(prefix)):
                return i
        return None

    def ensure_valid_args(self, args: list[str]) -> None:
        targets = self.get_targets(args)
        self._check_service_build_order(targets)
        self._check_clone_order(targets)

    def _check_service_build_order(self, targets: list[str]) -> None:
        # pull commands must come before any service/vm command
        earliest_build = self._earliest_of(targets, {'service', 'vm', 'upload'})
        if earliest_build is not None:
            for target in targets[earliest_build:]:
                if target.startswith('pull-service') or target.startswith('pull-gamelib'):
                    raise ValueError(f'Target {repr(target)} must come before any service-building target!')

    def _check_clone_order(self, targets: list[str]) -> None:
        earliest_build_or_pull = self._earliest_of(targets, {'service', 'vm', 'upload', 'pull-'})
        if earliest_build_or_pull is not None:
            for target in targets[earliest_build_or_pull:]:
                if target.startswith('clone'):
                    raise ValueError(f'Target {repr(target)} must come before any service targets!')


def main() -> None:
    import_credentials()
    try:
        CliChecker().ensure_valid_args(sys.argv[1:])
    except ValueError as e:
        print(f'[!] {str(e)}', file=sys.stderr)
        sys.exit(1)
    doit.run(TaskCreatorFactory().get_task_builders())


if __name__ == '__main__':
    main()
