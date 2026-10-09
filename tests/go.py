"""Exercise the real Go installer in scratch directories, including a native build.

Requires network access to the official Go downloads. No user tools are modified.
"""

import os
from pathlib import Path
import platform
import subprocess
import tempfile

import yaml


def check_go(root: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    defaults = yaml.safe_load((repo / "defaults/main.yml").read_text())
    version = defaults["go_version"]
    arch = {"aarch64": "arm64", "arm64": "arm64", "x86_64": "amd64"}[
        platform.machine()
    ]
    userdir = root / "user"
    userdir.mkdir()
    mockdir = root / "mock"
    mockdir.mkdir()
    # Hide the caller's real Go until the task installs its user-local symlink.
    (mockdir / "go").write_text("#!/bin/sh\nexit 127\n")
    (mockdir / "go").chmod(0o755)
    playbook = root / "go.yml"
    playbook.write_text(
        yaml.safe_dump(
            [
                {
                    "name": "Check Go provisioning and explicit upgrades",
                    "hosts": "localhost",
                    "connection": "local",
                    "gather_facts": False,
                    "vars_files": [str(repo / "defaults/main.yml")],
                    "vars": {
                        "pimp_my_shell_arch": arch,
                        "ansible_facts": {
                            "env": {
                                "HOME": str(userdir),
                                "PATH": f"{mockdir}:{os.environ['PATH']}",
                            },
                            "os_family": (
                                "Darwin" if platform.system() == "Darwin" else "Debian"
                            ),
                        },
                    },
                    "tasks": [
                        {
                            "name": "Run Go provisioning tasks",
                            "ansible.builtin.include_tasks": str(repo / "tasks/go.yml"),
                        }
                    ],
                }
            ],
            sort_keys=False,
        )
    )
    env = {
        **os.environ,
        "ANSIBLE_HOME": str(root / "ansible"),
        "GOTOOLCHAIN": "local",
        "GOENV": "off",
        "GOROOT": "",
        "GOCACHE": str(root / "go-cache"),
        "GOPATH": str(root / "go-path"),
    }
    executable = userdir / ".local/bin/go"

    def run(name: str, upgrade: bool, expected: str, unchanged: bool = False) -> None:
        result = subprocess.run(
            [
                "ansible-playbook",
                str(playbook),
                "-e",
                f"upgrade_components={str(upgrade).lower()}",
            ],
            env=env,
            capture_output=True,
            text=True,
        )
        output = result.stdout + result.stderr
        assert result.returncode == 0, output
        actual = subprocess.check_output(
            [str(executable), "version"], env=env, text=True
        )
        assert f"go version go{expected} " in actual, actual
        if unchanged:
            assert "changed=0 " in output, output
        print(f"PASS: {name}", flush=True)

    def simulate_existing(existing_version: str) -> None:
        mock = mockdir / f"go-{existing_version}"
        mock.write_text(
            f"#!/bin/sh\nprintf 'go version go{existing_version} linux/{arch}\\n'\n"
        )
        mock.chmod(0o755)
        executable.unlink()
        executable.symlink_to(mock)

    run("missing Go installs the configured release", False, version)
    source = root / "main.go"
    source.write_text('package main\nfunc main() { println("toolchain works") }\n')
    compiled = subprocess.run(
        [str(executable), "run", str(source)], env=env, capture_output=True, text=True
    )
    assert compiled.returncode == 0, compiled.stderr
    assert "toolchain works" in compiled.stderr, compiled.stderr
    print("PASS: installed Go compiles and runs a native program", flush=True)
    run("Go rerun is idempotent", False, version, unchanged=True)
    major, minor, _ = map(int, version.split("."))
    older = f"{major}.{minor - 1}.0"
    simulate_existing(older)
    run("normal rerun retains older Go", False, older, unchanged=True)
    run("explicit upgrade activates the configured Go", True, version)
    run("Go upgrade rerun is idempotent", True, version, unchanged=True)
    newer = f"{major}.{minor + 1}.0"
    simulate_existing(newer)
    run("explicit upgrade never downgrades newer Go", True, newer, unchanged=True)


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="pimp-my-shell-go-") as directory:
        check_go(Path(directory))
