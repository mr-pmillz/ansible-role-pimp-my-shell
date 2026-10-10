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
            "name": "Record dependency inputs",
            "ansible.builtin.copy": {
                "content": "{{ users | to_json }}",
                "dest": "{{ ansible_facts['env']['HOME'] }}/.dependency-users",
                "mode": "0600",
            },
        },
        {
            "name": "Simulate the shell dependency's write",
            "ansible.builtin.copy": {
                "content": "dependency ran\n",
                "dest": "{{ ansible_facts['env']['HOME'] }}/.zshrc",
                "mode": "0644",
            },
            "loop": "{{ users }}",
            "when": (
                "(item.oh_my_zsh | default({})).write_zshrc "
                "| default(oh_my_zsh_write_zshrc)"
            ),
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
        ("kitty only", {"only_kitty": True}, False),
        ("kitty and tmux", {"only_kitty": True, "only_tmux": True}, False),
        ("vim only", {"only_vim": True}, False),
        ("both editors", {"only_vim": True, "only_neovim": True}, False),
        ("neovim and zsh", {"only_neovim": True, "only_zsh": True}, True),
        ("default selects everything", {}, True),
        (
            "legacy write override",
            {
                "only_zsh": True,
                "oh_my_zsh_write_zshrc": True,
                "oh_my_zsh_users": [
                    {
                        "username": "fixture",
                        "oh_my_zsh": {"write_zshrc": True, "theme": "custom"},
                    }
                ],
            },
            True,
        ),
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
        assert (userdir / ".zshrc").read_text() == "existing customization\n", name
        dependency_users = userdir / ".dependency-users"
        assert dependency_users.exists() == shell_selected, name
        if shell_selected:
            users = yaml.safe_load(dependency_users.read_text())
            assert all(user["oh_my_zsh"]["write_zshrc"] is False for user in users)
            if name == "legacy write override":
                assert users[0]["oh_my_zsh"]["theme"] == "custom"
        if name in ("neovim only", "kitty only", "kitty and tmux"):
            for filename in protected:
                assert (
                    userdir / filename
                ).read_text() == "existing customization\n", filename
            assert sorted(
                p.name for p in userdir.iterdir() if not p.name.startswith(".")
            ) == {
                "neovim only": ["neovim"],
                "kitty only": ["kitty"],
                "kitty and tmux": ["kitty", "ohmytmux"],
            }[name]
        if flags and not flags.get("only_kitty"):
            assert not (userdir / "kitty").exists(), name
        if not flags:
            for task in (
                "neovim",
                "vim",
                "ohmyzsh",
                "ohmytmux",
                "nerdfonts",
                "cli-tools",
                "kitty",
                "terminal-profiles-ubuntu",
            ):
                assert (userdir / task).exists(), task
        print(f"PASS: {name}", flush=True)


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="pimp-my-shell-selection-") as directory:
        check_selection(Path(directory))
