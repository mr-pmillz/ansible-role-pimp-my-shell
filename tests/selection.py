"""Exercise the real role/dependency selection with harmless component fixtures."""

import os
from pathlib import Path
import pwd
import shutil
import subprocess
import tempfile

import yaml


def check_selection(root: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    roles = root / "roles"
    role = roles / "mr_pmillz.pimp_my_shell"
    # Keep the actual entry point, metadata, defaults, and selection expressions.
    # Replace component bodies and the external dependency with scratch writes.
    for directory in ("defaults", "vars", "meta"):
        shutil.copytree(repo / directory, role / directory)
    (role / "tasks").mkdir()
    shutil.copy2(repo / "tasks/main.yml", role / "tasks/main.yml")
    (role / "files").mkdir()
    shutil.copy2(repo / "files/.bashrc", role / "files/.bashrc")
    (roles / "gantsign.oh-my-zsh/tasks").mkdir(parents=True)
    dependency = [
        {
            "name": "Simulate the shell dependency's write",
            "ansible.builtin.copy": {
                "content": "dependency ran\n",
                "dest": "{{ ansible_facts['env']['HOME'] }}/.zshrc",
                "mode": "0644",
            },
        }
    ]
    (roles / "gantsign.oh-my-zsh/tasks/main.yml").write_text(yaml.safe_dump(dependency))
    for task in (repo / "tasks").glob("*.yml"):
        if task.name == "main.yml":
            continue
        stub = [
            {
                "name": "Record selected component",
                "ansible.builtin.copy": {
                    "content": "selected\n",
                    "dest": "{{ ansible_facts['env']['HOME'] }}/" + task.stem,
                    "mode": "0644",
                },
            }
        ]
        (role / "tasks" / task.name).write_text(yaml.safe_dump(stub))

    cases = [
        ("neovim only", {"only_neovim": True}, False),
        ("vim only", {"only_vim": True}, False),
        ("both editors", {"only_vim": True, "only_neovim": True}, False),
        ("neovim and zsh", {"only_neovim": True, "only_zsh": True}, True),
        ("default selects everything", {}, True),
    ]
    for name, flags, shell_selected in cases:
        userdir = root / name.replace(" ", "-")
        userdir.mkdir()
        protected = [".zshrc", ".p10k.zsh", ".vimrc", ".bashrc", ".tmux.conf"]
        for filename in protected:
            (userdir / filename).write_text("existing customization\n")
        play = [
            {
                "name": "Check component isolation",
                "hosts": "localhost",
                "connection": "local",
                "gather_facts": False,
                "vars": {
                    "install_prerequisites": False,
                    **flags,
                    "ansible_facts": {
                        "env": {"HOME": str(userdir)},
                        "os_family": "Debian",
                        "distribution": "Linux Mint",
                        "distribution_version": "22",
                        "architecture": "x86_64",
                        "user_id": pwd.getpwuid(os.getuid()).pw_name,
                        "user_gid": os.getgid(),
                    },
                },
                "roles": ["mr_pmillz.pimp_my_shell"],
            }
        ]
        playbook = root / "selection.yml"
        playbook.write_text(yaml.safe_dump(play, sort_keys=False))
        result = subprocess.run(
            ["ansible-playbook", str(playbook)],
            capture_output=True,
            text=True,
            env={
                **os.environ,
                "ANSIBLE_ROLES_PATH": str(roles),
                "ANSIBLE_HOME": str(root / "ansible"),
            },
        )
        assert result.returncode == 0, result.stdout + result.stderr
        expected = "dependency ran\n" if shell_selected else "existing customization\n"
        assert (userdir / ".zshrc").read_text() == expected, name
        if name == "neovim only":
            for filename in protected:
                assert (
                    userdir / filename
                ).read_text() == "existing customization\n", filename
            assert sorted(
                p.name for p in userdir.iterdir() if not p.name.startswith(".")
            ) == ["neovim"]
        if not flags:
            for task in (
                "neovim",
                "vim",
                "ohmyzsh",
                "ohmytmux",
                "nerdfonts",
                "cli-tools",
                "terminal-profiles-ubuntu",
            ):
                assert (userdir / task).exists(), task
        print(f"PASS: {name}", flush=True)


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="pimp-my-shell-selection-") as directory:
        check_selection(Path(directory))
