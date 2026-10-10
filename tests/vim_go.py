"""Exercise vim-go provisioning, failures, and deadlines without opening Vim.

Run with --real to build the complete upstream tool set in a temporary directory.
"""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

import yaml


def process_status(pid: int) -> list[str] | None:
    try:
        # The process name may itself contain spaces and closing parentheses.
        return Path(f"/proc/{pid}/stat").read_text().rsplit(") ", 1)[1].split()
    except (FileNotFoundError, ProcessLookupError):
        return None


def wait_for_process_exit(pid: int, start_time: str, timeout: float = 10) -> None:
    """Allow asynchronous teardown, but never accept a surviving build child."""
    deadline = time.monotonic() + timeout
    while True:
        status = process_status(pid)
        # Field 22 (index 19 after removing pid/comm) identifies this process.
        # A runner may have already reaped it and reused the PID for another job.
        if status is None or status[19] != start_time or status[0] in ("Z", "X", "x"):
            return
        if time.monotonic() >= deadline:
            raise AssertionError(
                f"build child {pid} still running after {timeout}s: "
                f"state={status[0]} ppid={status[1]} pgid={status[2]} "
                f"session={status[3]} start_time={status[19]}"
            )
        time.sleep(0.05)


def check_process_waiter() -> None:
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    try:
        start_time = process_status(child.pid)[19]
        try:
            wait_for_process_exit(child.pid, start_time, timeout=0.1)
        except AssertionError as error:
            assert f"build child {child.pid} still running" in str(error), str(error)
        else:
            raise AssertionError("cleanup check accepted a live child")
        # A different start time represents a reused PID, not a surviving child.
        wait_for_process_exit(child.pid, str(int(start_time) - 1), timeout=0)
    finally:
        child.kill()
        child.wait()
    wait_for_process_exit(child.pid, start_time, timeout=0)

    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(0.2)"])
    try:
        wait_for_process_exit(child.pid, process_status(child.pid)[19], timeout=5)
    finally:
        if child.poll() is None:
            child.kill()
        child.wait()
    print("PASS: cleanup check waits for exit and rejects surviving children", flush=True)


def check_installer(root: Path, real: bool) -> None:
    repo = Path(__file__).resolve().parents[1]
    userdir = root / "user"
    userdir.mkdir()
    bindir = root / "go-bin"
    log = root / "installs.jsonl"
    behavior = root / "behavior"
    behavior.write_text("ok")
    mockdir = root / "mock"
    mockdir.mkdir()
    if not real:
        go = mockdir / "go"
        go.write_text(
            "#!/usr/bin/env python3\n"
            "import json, os, pathlib, subprocess, sys\n"
            "root = pathlib.Path(os.environ['PMS_VIM_GO_TEST'])\n"
            "if sys.argv[1] == 'env':\n"
            "    print(json.dumps({'GOBIN': os.environ['GOBIN'],\n"
            "        'GOPATH': os.environ['GOPATH'], 'GOHOSTOS': 'linux',\n"
            "        'GOHOSTARCH': 'arm64'}))\n"
            "    sys.exit(0)\n"
            "assert sys.argv[1:5] == ['install', '-v', '-p', '2'], sys.argv\n"
            "assert os.environ['GOOS'] == 'linux'\n"
            "assert os.environ['GOARCH'] == 'arm64'\n"
            "assert os.environ['GOMAXPROCS'] == '2'\n"
            "assert os.environ['GIT_TERMINAL_PROMPT'] == '0'\n"
            "assert os.environ['GO111MODULE'] == 'on'\n"
            "name = sys.argv[-1].split('@')[0].split('/')[-1]\n"
            "with (root / 'installs.jsonl').open('a') as output:\n"
            "    output.write(json.dumps(name) + '\\n')\n"
            "behavior = (root / 'behavior').read_text()\n"
            "if behavior == 'fail':\n"
            "    print('simulated download failure', file=sys.stderr)\n"
            "    sys.exit(42)\n"
            "if behavior == 'hang':\n"
            "    child = subprocess.Popen(['sleep', '120'])\n"
            "    status = pathlib.Path(f'/proc/{child.pid}/stat').read_text()\n"
            "    (root / 'child.json').write_text(json.dumps({\n"
            "        'pid': child.pid, 'start_time': status.rsplit(') ', 1)[1].split()[19]}))\n"
            "    child.wait()\n"
            "if behavior != 'missing':\n"
            "    binary = pathlib.Path(os.environ['GOBIN']) / name\n"
            "    binary.write_text('#!/bin/sh\\nexit 0\\n')\n"
            "    binary.chmod(0o755)\n"
        )
        go.chmod(0o755)
        vim = mockdir / "vim"
        vim.write_text("#!/bin/sh\necho 'Interactive Vim must not run' >&2\nexit 99\n")
        vim.chmod(0o755)

    variables = {
        "role_path": str(repo),
        "ansible_async_dir": str(root / "async"),
        "ansible_facts": {
            "env": {"HOME": str(userdir), "PATH": f"{mockdir}:{os.environ['PATH']}"}
        },
    }
    if not real:
        defaults = yaml.safe_load((repo / "defaults/main.yml").read_text())
        variables["vim_go_tools"] = {
            name: defaults["vim_go_tools"][name] for name in ("iferr", "gopls")
        }

    playbook = root / "vim-go.yml"
    playbook.write_text(
        yaml.safe_dump(
            [{
                "name": "Check noninteractive vim-go provisioning",
                "hosts": "localhost",
                "connection": "local",
                "gather_facts": False,
                "vars_files": [str(repo / "defaults/main.yml")],
                "vars": variables,
                "tasks": [{
                    "name": "Run the real vim-go tasks",
                    "ansible.builtin.include_tasks": str(repo / "tasks/vim-go.yml"),
                }],
            }],
            sort_keys=False,
        )
    )
    env = {
        **os.environ,
        "ANSIBLE_HOME": str(root / "ansible"),
        "PMS_VIM_GO_TEST": str(root),
        "GOBIN": str(bindir),
        "GOPATH": str(root / "go-path"),
        "GOCACHE": str(root / "go-cache"),
        "GOENV": "off",
        "GOROOT": "",
        "GOOS": "windows",  # Provisioning must build tools for the host instead.
        "GOARCH": "amd64",
    }

    def run(name: str, *, upgrade=False, error=None, deadline=900, unchanged=False):
        started = time.monotonic()
        extra = {"upgrade_components": upgrade, "vim_go_install_timeout": deadline}
        if not real:
            # Extra vars override the playbook's vars_files, just as -e does
            # for callers selecting a smaller tool set.
            extra["vim_go_tools"] = variables["vim_go_tools"]
        with (root / "last-run.log").open("w") as output_file:
            result = subprocess.run(
                ["ansible-playbook", "-i", "localhost,", str(playbook), "-e",
                 json.dumps(extra)],
                env=env, stdout=output_file, stderr=subprocess.STDOUT,
                text=True, timeout=5400 if real else 60,
            )
        output = (root / "last-run.log").read_text()
        if error is None:
            assert result.returncode == 0, output
            if unchanged:
                assert "changed=0 " in output, output
        else:
            assert result.returncode != 0, output
            assert error in output, output
        print(f"PASS: {name} ({time.monotonic() - started:.1f}s)", flush=True)

    marker = userdir / "vim_go_is_installed.txt"
    marker.touch()  # A legacy marker must not hide missing binaries.
    run("install actual tools despite a stale completion marker")
    assert not marker.exists()
    run("normal rerun is idempotent", unchanged=True)
    if real:
        for binary in bindir.iterdir():
            subprocess.run(["go", "version", "-m", str(binary)], check=True, env=env)
        return

    def installed():
        return [json.loads(line) for line in log.read_text().splitlines()]

    assert installed() == ["iferr", "gopls"]
    (bindir / "iferr").unlink()
    run("repair only a missing executable")
    assert installed() == ["iferr", "gopls", "iferr"]
    (bindir / "gopls").chmod(0o644)
    run("repair a nonexecutable tool")
    assert installed()[-1] == "gopls"
    run("explicit upgrades work without a plugin Git change", upgrade=True)
    assert installed()[-2:] == ["iferr", "gopls"]

    (bindir / "iferr").unlink()
    behavior.write_text("fail")
    count = len(installed())
    run("surface Go failures and stop before the next tool", upgrade=True,
        error="simulated download failure")
    assert len(installed()) == count + 1
    assert not marker.exists()
    assert not (bindir / "iferr").exists()

    behavior.write_text("missing")
    run("reject success without an installed executable", error="did not create")
    assert not marker.exists()

    behavior.write_text("hang")
    run("report a stuck Go build timeout", deadline=2,
        error="Timeout exceeded")
    child = json.loads((root / "child.json").read_text())
    wait_for_process_exit(child["pid"], child["start_time"])
    print("PASS: timed-out build child was terminated", flush=True)
    assert not marker.exists()

    behavior.write_text("ok")
    run("recover cleanly after a timed-out build")
    run("repaired installation is idempotent", unchanged=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--real", action="store_true")
    args = parser.parse_args()
    if not args.real:
        check_process_waiter()
    with tempfile.TemporaryDirectory(prefix="pimp-my-shell-vim-go-") as directory:
        print(f"Test directory: {directory}", flush=True)
        check_installer(Path(directory), args.real)
