import os
import pickle
import subprocess
import sys
from base64 import b64encode, b64decode
from typing import Any, TypeVar, ParamSpec, TypeAlias, Callable

RT = TypeVar('RT')
P = ParamSpec('P')


class SudoHelper:
    _result_prefix = b'[[RESULT]]:'

    original_uid = os.getuid()
    original_gid = os.getgid()

    @classmethod
    def run_as_root(cls, target: Callable[P, RT], *args: P.args, **kwargs: P.kwargs) -> RT:
        if os.getuid() == 0:
            return target(*args, **kwargs)
        else:
            return cls._run_with_sudo(target, *args, **kwargs)

    @classmethod
    def _run_with_sudo(cls, target: Callable[P, RT], *args: P.args, **kwargs: P.kwargs) -> RT:
        data = pickle.dumps((target, args, kwargs, cls.original_uid, cls.original_gid))
        cmd = ['sudo', '-E', '--', sys.executable, '-u', __file__, b64encode(data).decode()]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)

        last_line: bytes = b''
        with os.fdopen(sys.stdout.fileno(), "wb", closefd=False) as stdout:
            while True:
                line: bytes = proc.stdout.readline()  # type: ignore
                if not line:
                    break
                if not line.startswith(cls._result_prefix):
                    stdout.write(line)
                    stdout.flush()
                last_line = line
        return_code = proc.wait()
        if return_code != 0:
            raise Exception('sudo process failed')

        if not last_line.startswith(cls._result_prefix):
            raise Exception('sudo process returned no result')
        success, result = pickle.loads(b64decode(last_line.strip()[len(cls._result_prefix):]))
        if success:
            return result
        else:
            raise result

    @classmethod
    def child_process(cls, data: bytes) -> None:
        target, args, kwargs, cls.original_uid, cls.original_gid = pickle.loads(data)
        try:
            result = (True, target(*args, **kwargs))
        except Exception as e:
            result = (False, e)
        data = cls._result_prefix + b64encode(pickle.dumps(result))
        print(data.decode())


if __name__ == '__main__':
    SudoHelper.child_process(b64decode(sys.argv[1]))
