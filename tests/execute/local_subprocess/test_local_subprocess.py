from __future__ import annotations

# import json
import locale
import logging

# import os
# import shutil
# import stat
# import subprocess
import sys
from io import TextIOWrapper
from pathlib import Path
from typing import TYPE_CHECKING

# from unittest.mock import MagicMock, create_autospec
from unittest.mock import MagicMock

# import psutil
import pytest
from colorama import Fore

# from tox.execute.api import ExecuteOptions, Outcome
from tox.execute.api import Outcome

# from tox.execute.local_sub_process import SIG_INTERRUPT, LocalSubProcessExecuteInstance, LocalSubProcessExecutor
from tox.execute.local_sub_process import LocalSubProcessExecutor

# from tox.execute.local_sub_process.read_via_thread_unix import ReadViaThreadUnix
from tox.execute.request import ExecuteRequest, StdinSource

# from tox.execute.stream import SyncWrite
from tox.report import NamedBytesIO

# from psutil import AccessDenied


if TYPE_CHECKING:
    # from pytest_mock import MockerFixture

    # from tox.pytest import CaptureFixture, LogCaptureFixture, MonkeyPatch
    from tox.pytest import LogCaptureFixture


class FakeOutErr:
    def __init__(self) -> None:
        self.out_err = (
            TextIOWrapper(
                NamedBytesIO("out"), encoding=locale.getpreferredencoding(False)
            ),
            TextIOWrapper(
                NamedBytesIO("err"), encoding=locale.getpreferredencoding(False)
            ),
        )

    def read_out_err(self) -> tuple[str, str]:
        out_got = self.out_err[0].buffer.getvalue().decode(self.out_err[0].encoding)  # type: ignore[attr-defined]
        err_got = self.out_err[1].buffer.getvalue().decode(self.out_err[1].encoding)  # type: ignore[attr-defined]
        return out_got, err_got


@pytest.mark.parametrize("color", [True, False], ids=["color", "no_color"])
@pytest.mark.parametrize(
    ("out", "err"), [("out", "err"), ("", "")], ids=["simple", "nothing"]
)
@pytest.mark.parametrize("show", [True, False], ids=["show", "no_show"])
def test_local_execute_basic_pass(  # noqa: PLR0913
    caplog: LogCaptureFixture,
    os_env: dict[str, str],
    out: str,
    err: str,
    show: bool,
    color: bool,
) -> None:
    caplog.set_level(logging.NOTSET)
    executor = LocalSubProcessExecutor(colored=color)
    code = (
        f"import sys; print({out!r}, end=''); print({err!r}, end='', file=sys.stderr)"
    )
    request = ExecuteRequest(
        cmd=[sys.executable, "-c", code],
        cwd=Path(),
        env=os_env,
        stdin=StdinSource.OFF,
        run_id="",
    )
    out_err = FakeOutErr()
    with executor.call(
        request, show=show, out_err=out_err.out_err, env=MagicMock()
    ) as status:
        while status.exit_code is None:  # pragma: no branch
            status.wait()
    assert status.out == out.encode()
    assert status.err == err.encode()
    outcome = status.outcome
    assert outcome is not None
    assert bool(outcome) is True, outcome
    assert outcome.exit_code == Outcome.OK
    assert outcome.err == err
    assert outcome.out == out
    assert outcome.request == request

    out_got, err_got = out_err.read_out_err()
    if show:
        assert out_got == out
        expected = (f"{Fore.RED}{err}{Fore.RESET}" if color else err) if err else ""
        assert err_got == expected
    else:
        assert not out_got
        assert not err_got
    assert not caplog.records
