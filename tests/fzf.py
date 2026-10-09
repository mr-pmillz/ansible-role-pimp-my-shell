"""Exercise the Neovim fzf installer against a disposable local Git upstream."""

import os
from pathlib import Path
import subprocess
import tempfile

import yaml


def check_fzf(root: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    source = root / "upstream"
    source.mkdir()

    def git(*args: str) -> None:
        subprocess.run(
            ["git", "-C", str(source), *args], check=True, capture_output=True
        )

    git("init", "--initial-branch=main")
    git("config", "user.name", "Fzf regression test")
    git("config", "user.email", "test@example.invalid")
    (source / "install").write_text(
        "#!/usr/bin/env bash\nset -euo pipefail\n"
        '[ "$#" = 1 ] && [ "$1" = --bin ]\n'
        'cd -- "$(dirname -- "$0")"\n'
        "mkdir -p bin\n"
        "printf '#!/bin/sh\\necho \"%s (fixture)\"\\n' "
        '"$(cat VERSION)" > bin/fzf\n'
        "chmod +x bin/fzf\n"
    )
    (source / ".gitignore").write_text("/bin/\n")
    for version in ("0.74.4", "0.75.0"):
        (source / "VERSION").write_text(version + "\n")
        git("add", ".")
        git("commit", "-m", version)
        git("tag", "v" + version)

    tasks = root / "fzf.yml"
    tasks.write_text(
        (repo / "tasks/neovim-fzf.yml")
        .read_text()
        .replace("https://github.com/junegunn/fzf.git", source.as_uri())
    )
    userdir = root / "user"
    userdir.mkdir()
    protected = [".zshrc", ".bashrc", ".p10k.zsh", ".fzf.zsh", ".fzf.bash"]
    for filename in protected:
        (userdir / filename).write_text("existing customization\n")
    old_bin = root / "distro-bin"
    old_bin.mkdir()
    distro_fzf = old_bin / "fzf"
    distro_fzf.write_text("#!/bin/sh\nexit 127\n")
    distro_fzf.chmod(0o755)
    playbook = root / "playbook.yml"
    playbook.write_text(
        yaml.safe_dump(
            [
                {
                    "name": "Check the Neovim fuzzy finder",
                    "hosts": "localhost",
                    "connection": "local",
                    "gather_facts": False,
                    "vars": {
                        "neovim_fzf_minimum_version": "0.53.0",
                        "ansible_facts": {
                            "env": {
                                "HOME": str(userdir),
                                "PATH": f"{old_bin}:/usr/bin:/bin",
                            }
                        },
                    },
                    "tasks": [
                        {
                            "name": "Run the actual installer tasks",
                            "ansible.builtin.include_tasks": str(tasks),
                        }
                    ],
                }
            ],
            sort_keys=False,
        )
    )
    env = {**os.environ, "ANSIBLE_HOME": str(root / "ansible")}

    def run(
        name: str,
        target: str,
        expected: str,
        upgrade: bool = False,
        unchanged: bool = False,
    ) -> None:
        result = subprocess.run(
            [
                "ansible-playbook",
                str(playbook),
                "-e",
                f"neovim_fzf_version={target} upgrade_components={str(upgrade).lower()}",
            ],
            env=env,
            capture_output=True,
            text=True,
        )
        output = result.stdout + result.stderr
        assert result.returncode == 0, output
        binary = userdir / ".local/bin/fzf"
        actual = subprocess.check_output([str(binary), "--version"], text=True)
        assert actual.startswith(expected + " "), actual
        for filename in protected:
            assert (
                userdir / filename
            ).read_text() == "existing customization\n", filename
        if unchanged:
            assert "changed=0 " in output, output
        print(f"PASS: {name}", flush=True)

    run(
        "missing fzf installs through Git without touching shell files",
        "0.74.4",
        "0.74.4",
    )
    run("normal rerun is idempotent", "0.74.4", "0.74.4", unchanged=True)
    run(
        "new configured release requires explicit upgrade",
        "0.75.0",
        "0.74.4",
        unchanged=True,
    )
    run("explicit upgrade installs the new release", "0.75.0", "0.75.0", upgrade=True)
    run("upgrade rerun is idempotent", "0.75.0", "0.75.0", upgrade=True, unchanged=True)
    run(
        "newer installed release is retained",
        "0.74.4",
        "0.75.0",
        upgrade=True,
        unchanged=True,
    )
    (userdir / ".fzf/bin/fzf").unlink()
    distro_fzf.write_text("#!/bin/sh\necho '0.44.1 (distro)'\n")
    run("old distro fzf is repaired without the upgrade flag", "0.75.0", "0.75.0")


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="pimp-my-shell-fzf-") as directory:
        check_fzf(Path(directory))
