"""Run Kitty tasks against local installer/theme fixtures in temporary homes."""

import os
from pathlib import Path
import shlex
import subprocess
import tempfile

import yaml


def check_kitty(root: Path, os_family: str) -> None:
    repo = Path(__file__).resolve().parents[1]
    source = root / "themes"
    (source / "themes").mkdir(parents=True)

    def git(*args: str) -> None:
        subprocess.run(
            ["git", "-C", str(source), *args], check=True, capture_output=True
        )

    git("init", "--initial-branch=main")
    git("config", "user.name", "Kitty regression test")
    git("config", "user.email", "test@example.invalid")
    installer = root / "installer.sh"
    binary_path = "Contents/MacOS" if os_family == "Darwin" else "bin"
    desktop_files = {
        "kitty.desktop": (
            "[Desktop Entry]\nType=Application\nName=kitty\nIcon=kitty\n"
            "Exec=kitty\nActions=New;\n\n[Desktop Action New]\n"
            "Name=New window\nExec=kitty --single-instance\n"
        ),
        "kitty-open.desktop": (
            "[Desktop Entry]\nType=Application\nName=kitty open\n"
            "Icon=kitty\nExec=kitty +open %U\n"
        ),
    }

    def release(version: str) -> None:
        (source / "themes/Blazer.conf").write_text(f"# {version}\nbackground #0d1925\n")
        git("add", ".")
        git("commit", "-m", version)
        # The fixture checks the official installer's arguments, then provides
        # realistic app/launcher layouts without downloading or launching Kitty.
        script = (
            '#!/bin/sh\nset -eu\n[ "$#" = 2 ]\n[ "$1" = launch=n ]\n'
            'case "$2" in dest=*) parent=${2#dest=} ;; *) exit 1 ;; esac\n'
            f'bin="$parent/kitty.app/{binary_path}"\n'
            'mkdir -p "$bin"\n'
            'printf "installed\\n" >> "$parent/kitty-installs"\n'
        )
        for name in ("kitty", "kitten"):
            executable = f"#!/bin/sh\necho '{name} {version}'\n"
            script += f'printf %s {shlex.quote(executable)} > "$bin/{name}"\n'
            script += f'chmod +x "$bin/{name}"\n'
        if os_family != "Darwin":
            script += 'apps="$parent/kitty.app/share/applications"\nmkdir -p "$apps"\n'
            for name, content in desktop_files.items():
                script += f'printf %s {shlex.quote(content)} > "$apps/{name}"\n'
            script += (
                'icons="$parent/kitty.app/share/icons/hicolor/256x256/apps"\n'
                'mkdir -p "$icons"\ntouch "$icons/kitty.png"\n'
            )
        installer.write_text(script)

    release("1")
    tasks = root / "kitty.yml"
    tasks.write_text(
        (repo / "tasks/kitty.yml")
        .read_text()
        .replace("https://sw.kovidgoyal.net/kitty/installer.sh", installer.as_uri())
        .replace("https://github.com/dexpota/kitty-themes.git", source.as_uri())
    )
    userdir = root / "user with spaces"
    userdir.mkdir()
    config = userdir / ".config/kitty"
    install_parent = userdir / ("Applications" if os_family == "Darwin" else ".local")
    app = install_parent / "kitty.app"
    playbook = root / "playbook.yml"
    playbook.write_text(
        yaml.safe_dump(
            [
                {
                    "name": "Check Kitty provisioning",
                    "hosts": "localhost",
                    "connection": "local",
                    "gather_facts": False,
                    "vars": {
                        "ansible_facts": {
                            "env": {"HOME": str(userdir)},
                            "os_family": os_family,
                        },
                    },
                    "tasks": [
                        {
                            "name": "Run the actual Kitty component",
                            "ansible.builtin.include_tasks": str(tasks),
                        }
                    ],
                }
            ],
            sort_keys=False,
        )
    )

    def run(
        name: str,
        version: str = "1",
        installs: int = 1,
        upgrade: bool = False,
        unchanged: bool = False,
        check: bool = False,
        expected_config: str = "font_size 13\ninclude ./theme.conf\n",
    ) -> None:
        result = subprocess.run(
            [
                "ansible-playbook",
                str(playbook),
                "-e",
                f"upgrade_components={str(upgrade).lower()}",
                *(["--check"] if check else []),
            ],
            env={**os.environ, "ANSIBLE_HOME": str(root / "ansible")},
            capture_output=True,
            text=True,
        )
        output = result.stdout + result.stderr
        assert result.returncode == 0, output
        if installs == 0:
            assert not list(userdir.iterdir()), list(userdir.iterdir())
        else:
            assert (install_parent / "kitty-installs").read_text().splitlines() == [
                "installed"
            ] * installs
            for binary in ("kitty", "kitten"):
                link = userdir / ".local/bin" / binary
                assert link.is_symlink() and link.resolve() == app / binary_path / binary
                assert subprocess.check_output([str(link)], text=True) == f"{binary} {version}\n"
            assert (config / "theme.conf").readlink() == Path("kitty-themes/themes/Blazer.conf")
            assert (config / "theme.conf").read_text().startswith(f"# {version}\n")
            assert (config / "kitty.conf").read_text() == expected_config
            assert (config / "kitty-themes/.git/shallow").is_file()
            if os_family == "Darwin":
                assert not (userdir / ".local/share/applications").exists()
                assert not (userdir / ".config/xdg-terminals.list").exists()
            else:
                for filename, content in desktop_files.items():
                    expected = content.replace(
                        "Icon=kitty", f"Icon={app}/share/icons/hicolor/256x256/apps/kitty.png"
                    ).replace("Exec=kitty", f'Exec="{app}/bin/kitty"')
                    actual = userdir / ".local/share/applications" / filename
                    assert actual.read_text() == expected, actual.read_text()
                assert (userdir / ".config/xdg-terminals.list").read_text() == "kitty.desktop\n"
        if unchanged:
            assert "changed=0 " in output, output
        print(f"PASS ({os_family}): {name}", flush=True)

    run("fresh check mode does not install or write files", installs=0, check=True)
    config.mkdir(parents=True)
    (config / "kitty.conf").write_text("font_size 13\n")
    (config / "theme.conf").write_text("old theme\n")
    run("install, desktop integration, theme selection, and config preservation")
    run("normal rerun is idempotent", unchanged=True)
    run("installed check mode is idempotent", unchanged=True, check=True)
    release("2")
    run("normal rerun preserves installed binaries and themes", unchanged=True)
    run("explicit upgrade refreshes binaries and themes", version="2", installs=2, upgrade=True)
    run("rerun after upgrade is idempotent", version="2", installs=2, unchanged=True)
    (userdir / ".local/bin/kitty").unlink()
    (config / "theme.conf").unlink()
    if os_family != "Darwin":
        (userdir / ".local/share/applications/kitty.desktop").unlink()
    # Config edits and link/launcher repair should not reinstall Kitty.
    (config / "kitty.conf").write_text("font_size 13\ninclude theme.conf\n")
    run("repair links, launchers, and theme include", version="2", installs=2)
    (app / binary_path / "kitten").unlink()
    run("repair a missing kitten executable", version="2", installs=3)
    (config / "kitty.conf").unlink()
    run(
        "create a missing Kitty configuration",
        version="2",
        installs=3,
        expected_config="include ./theme.conf\n",
    )


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="pimp-my-shell-kitty-") as directory:
        for family in ("Debian", "Darwin"):
            root = Path(directory) / family
            root.mkdir()
            check_kitty(root, family)
