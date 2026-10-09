"""Test the real CLI tasks with a local fzf upstream; no user files or network."""

import os
from pathlib import Path
import pwd
import subprocess
import tempfile

import yaml


def check_upgrades(root: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    source = root / "upstream"
    source.mkdir()

    def git(*args: str) -> None:
        subprocess.run(
            ["git", "-C", str(source), *args], check=True, capture_output=True
        )

    git("init", "--initial-branch=main")
    git("config", "user.name", "Upgrade regression test")
    git("config", "user.email", "test@example.invalid")
    (source / "VERSION").write_text("1\n")
    (source / "install").write_text(
        "#!/usr/bin/env bash\nset -euo pipefail\n"
        'source_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)\n'
        'cp "$source_dir/VERSION" "$source_dir/../fzf-version"\n'
    )
    (source / "install").chmod(0o755)
    git("add", "VERSION", "install")
    git("commit", "-m", "Initial fixture version")

    # Only substitute the upstream endpoint. Git insteadOf rewriting makes
    # Ansible report remote_url_changed on every run, invalidating the test.
    tasks = root / "cli-tools.yml"
    tasks.write_text(
        (repo / "tasks/cli-tools.yml")
        .read_text()
        .replace("https://github.com/junegunn/fzf", source.as_uri())
    )
    userdir = root / "user"
    userdir.mkdir()
    playbook = root / "upgrade.yml"
    playbook.write_text(
        yaml.safe_dump(
            [
                {
                    "name": "Check explicit component upgrades",
                    "hosts": "localhost",
                    "connection": "local",
                    "gather_facts": False,
                    "vars": {
                        "role_path": str(repo),
                        "dark_mode": False,
                        "ansible_facts": {
                            "env": {"HOME": str(userdir)},
                            "user_id": pwd.getpwuid(os.getuid()).pw_name,
                            "user_gid": os.getgid(),
                            "os_family": "Debian",
                        },
                    },
                    "tasks": [
                        {
                            "name": "Run CLI component tasks",
                            "ansible.builtin.include_tasks": str(tasks),
                        }
                    ],
                }
            ],
            sort_keys=False,
        )
    )
    env = {**os.environ, "ANSIBLE_HOME": str(root / "ansible")}

    def run(name: str, upgrade: bool, version: str, unchanged: bool = False) -> None:
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
        assert (userdir / "fzf-version").read_text().strip() == version, name
        if unchanged:
            assert "changed=0 " in output, output
        print(f"PASS: {name}", flush=True)

    run("first install", False, "1")
    run("normal rerun is idempotent", False, "1", unchanged=True)
    (source / "VERSION").write_text("2\n")
    git("add", "VERSION")
    git("commit", "-m", "New upstream version")
    run("normal rerun keeps installed version", False, "1", unchanged=True)
    run("explicit upgrade installs the new version", True, "2")
    run("upgrade rerun is idempotent", True, "2", unchanged=True)


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="pimp-my-shell-upgrades-") as directory:
        check_upgrades(Path(directory))
