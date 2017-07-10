from _base import _RUN_GENERIC_SCRIPT
from _base import _file_exists
from _base import Platform
from _base import set_env
from _base import parse_deploy_args
import os
import stat
import argparse
import pytest
import platform
import sys


def _create_dummy_script():
    name = "/tmp/dummyscript"
    with open(name, "w") as temp:
        temp.write('''#!/usr/bin/env python
import sys

sys.stdout.write("stdout_msg")
sys.stderr.write("stderr_msg")
        ''')
        temp.flush()
    st = os.stat(name)
    os.chmod(name, st.st_mode | stat.S_IEXEC)
    return name


def _create_empty_file():
    name = "/tmp/emptyfile"
    with open(name, "w") as temp:
        temp.write("")
        temp.flush()
    return name


###############################################################################
# Tests
###############################################################################
def test_run_generic_script():
    script = _create_dummy_script()

    out, err = _RUN_GENERIC_SCRIPT(script, async=False)
    assert out == "stdout_msg"
    assert err == "stderr_msg"

    out, err = _RUN_GENERIC_SCRIPT(script, async=True)
    assert out == ""
    assert err == ""


def test_set_env():
    set_env("WEBTIER_TESTING", "123")
    assert os.environ["WEBTIER_TESTING"] == "123"
    os.environ["WEBTIER_TESTING"] == ""


def test_platform():
    myplatform = Platform()
    myplatform.detect()
    assert myplatform.system == platform.system().lower()
    assert myplatform.type == os.name


def test_file_exists():
    file = _create_empty_file()
    assert _file_exists(file) == file

    with pytest.raises(argparse.ArgumentTypeError) as excinfo:
        _file_exists("")
    assert excinfo.match("Please specify an input filename")

    with pytest.raises(argparse.ArgumentTypeError) as excinfo:
        _file_exists("blabla")
    assert excinfo.match("Please use a valid filename")


def test_parse_deploy_args(capsys):
    file = _create_empty_file()

    sys.argv = ["./deploy", "-s", file]
    config = parse_deploy_args()
    assert config == file

    sys.argv = ["./deploy", "--setup", file]
    config = parse_deploy_args()
    assert config == file

    with pytest.raises(SystemExit) as excinfo:
        sys.argv = ["./deploy", "-s"]
        config = parse_deploy_args()
    out, err = capsys.readouterr()
    assert err.startswith("usage: ")

    with pytest.raises(SystemExit) as excinfo:
        sys.argv = ["./deploy", "--setup"]
        config = parse_deploy_args()
    out, err = capsys.readouterr()
    assert err.startswith("usage: ")

    with pytest.raises(SystemExit) as excinfo:
        sys.argv = ["./deploy", "-randomparameter"]
        config = parse_deploy_args()
    out, err = capsys.readouterr()
    assert err.startswith("usage: ")

    with pytest.raises(SystemExit) as excinfo:
        sys.argv = ["./deploy"]
        config = parse_deploy_args()
    out, err = capsys.readouterr()
    assert err.startswith("usage: ")


