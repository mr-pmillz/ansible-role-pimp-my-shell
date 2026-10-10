"""Exercise vim-go provisioning, failures, and deadlines without opening Vim.

Run with --real to build the complete upstream tool set in a temporary directory.
"""

import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time

import yaml


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
            "    (root / 'child.pid').write_text(str(child.pid))\n"
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
    run("terminate a stuck Go build at its deadline", deadline=2,
        error="Timeout exceeded")
    pid = int((root / "child.pid").read_text())
    status = Path(f"/proc/{pid}/stat")
    if status.exists():
        assert status.read_text().split(') ', 1)[1].startswith('Z '), "build child still running"
    assert not marker.exists()

    behavior.write_text("ok")
    run("recover cleanly after a timed-out build")
    run("repaired installation is idempotent", unchanged=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--real", action="store_true")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="pimp-my-shell-vim-go-") as directory:
        print(f"Test directory: {directory}", flush=True)
        check_installer(Path(directory), args.real)
