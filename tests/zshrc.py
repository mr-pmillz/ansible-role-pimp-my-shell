"""Exercise the real Zsh merge with scratch files and harmless startup fixtures."""

import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tempfile

import yaml


BEGIN = "# BEGIN ANSIBLE MANAGED BLOCK: pimp-my-shell\n"
END = "# END ANSIBLE MANAGED BLOCK: pimp-my-shell\n"
SECRET = "fixture-only-secret-not-for-ansible-output"


def check_zshrc(root: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    role = root / "roles/zsh_merge"
    for directory in ("defaults", "templates", "files/zsh"):
        shutil.copytree(repo / directory, role / directory)
    (role / "tasks").mkdir()
    shutil.copy2(repo / "tasks/zshrc.yml", role / "tasks/main.yml")
    playbook = root / "playbook.yml"

    def run(userdir: Path, *, theme="powerlevel10k/powerlevel10k", check=False,
            fails=False, unchanged=False, tasks=None, environment=None) -> str:
        play = {
            "name": "Check Zsh preservation",
            "hosts": "localhost",
            "connection": "local",
            "gather_facts": False,
            "vars": {
                "oh_my_zsh_theme": theme,
                "ansible_facts": {
                    "env": {"HOME": str(userdir)},
                    "distribution": "MacOSX",
                },
                "pimp_my_shell_components": ["zsh"],
            },
        }
        if tasks is None:
            play["roles"] = ["zsh_merge"]
        else:
            play["tasks"] = tasks
            play["environment"] = environment or {}
        playbook.write_text(yaml.safe_dump([play], sort_keys=False))
        result = subprocess.run(
            ["ansible-playbook", str(playbook), "--diff", "-vvv",
             *(["--check"] if check else [])],
            env={**os.environ, "ANSIBLE_HOME": str(root / "ansible")},
            capture_output=True, text=True,
        )
        output = result.stdout + result.stderr
        assert SECRET not in output, "Existing secrets appeared in Ansible output"
        assert (result.returncode != 0) == fails, output
        if unchanged:
            assert re.search(r"changed=0\s", output), output
        return output

    original = (
        "# Keep my comments, settings, and spacing.\n"
        f"export FIXTURE_API_KEY='{SECRET}'\n"
        "export FIXTURE_LITERAL='{{ do_not_template_this }}'\n"
        "export ZSH=\"$HOME/.oh-my-zsh\"\n"
        "ZSH_THEME='my-custom-theme'\n"
        "plugins=(git local-custom)\n"
        "zstyle ':omz:update' mode disabled\n"
        'source "$ZSH/oh-my-zsh.sh"\n'
        "alias keep_me='printf personal'\n"
        "fixture_function() { print personal; }\n"
        "export GOPATH=/fixture/custom-go\n"
    )
    cases = {
        "existing custom settings": original,
        "new file": None,
        "empty file": "",
        "no trailing newline": "export FIXTURE_EXISTING=preserved",
        "symlink": original,
        "empty theme": "ZSH_THEME=''\nplugins=(git)\n",
        "stock theme": "ZSH_THEME=robbyrussell\nplugins=(git)\n",
        "nounset": "setopt nounset\n",
    }
    homes = {}
    for name, content in cases.items():
        userdir = root / name
        userdir.mkdir()
        homes[name] = userdir
        path = userdir / ".zshrc"
        if name == "symlink":
            target = userdir / "dotfiles/zshrc"
            target.parent.mkdir()
            target.write_text(content)
            path.symlink_to(target)
        elif content is not None:
            path.write_text(content)
        if content is not None:
            path.chmod(0o640 if name == "symlink" else 0o600)

        run(userdir, check=True)
        assert path.exists() == (content is not None)
        if content is not None:
            assert path.read_text() == content
        run(userdir)
        merged = path.read_text()
        assert merged.count(BEGIN) == merged.count(END) == 1
        prefix = content or ""
        if prefix and not prefix.endswith("\n"):
            prefix += "\n"
        assert merged.split(BEGIN)[0] == prefix, name
        expected_mode = 0o640 if name == "symlink" else 0o600
        assert stat.S_IMODE(path.stat().st_mode) == expected_mode
        if name == "symlink":
            assert path.is_symlink() and target.read_text() == merged
        backups = [p for p in userdir.rglob("*~") if p.is_file()]
        if content is not None:
            assert len(backups) == 1 and backups[0].read_text() == content, backups
            assert stat.S_IMODE(backups[0].stat().st_mode) == expected_mode
        else:
            assert not backups
        modified = path.stat().st_mtime_ns
        run(userdir, unchanged=True)
        assert path.stat().st_mtime_ns == modified
        assert [p for p in userdir.rglob("*~") if p.is_file()] == backups
        print(f"PASS: preserve, back up, and rerun {name}", flush=True)

    userdir = homes["existing custom settings"]
    path = userdir / ".zshrc"
    after = "\n# User additions after the block\nexport FIXTURE_AFTER=kept\n"
    path.write_text(path.read_text() + after)
    before = path.read_text()
    run(userdir, theme="updated-role-theme")
    updated = path.read_text()
    assert updated.startswith(original + BEGIN) and updated.endswith(END + after)
    assert updated.count(BEGIN) == 1 and "updated-role-theme" in updated
    assert before in [p.read_text() for p in userdir.rglob("*~")]
    run(userdir, theme="updated-role-theme", unchanged=True)
    print("PASS: update only the managed block and preserve later additions", flush=True)

    invalid = root / "invalid syntax"
    invalid.mkdir()
    invalid_file = invalid / ".zshrc"
    invalid_content = f"export FIXTURE_API_KEY='{SECRET}'\nif then\n"
    invalid_file.write_text(invalid_content)
    run(invalid, fails=True)
    assert invalid_file.read_text() == invalid_content
    print("PASS: syntax validation rejects writes without exposing secrets", flush=True)

    for name in ("existing custom settings", "new file", "empty theme", "stock theme", "nounset"):
        userdir = homes[name]
        omz = userdir / ".oh-my-zsh"
        omz.mkdir()
        (omz / "oh-my-zsh.sh").write_text(
            '(( fixture_omz_loads += 1 ))\n'
            "alias keep_me='printf from-role'\n"
            "omz() {\n"
            '  if [[ "$1 $2" == "plugin load" ]]; then\n'
            '    fixture_loaded_plugins+=("${@:3}")\n'
            "    alias keep_me='printf from-plugin'\n"
            "  fi\n"
            "}\n"
        )
        secret_file = userdir / ".zsh_secrets"
        if name != "empty theme":
            secret_file.write_text("export FIXTURE_SECRET_LOADED=yes\n")
        (userdir / ".p10k.zsh").write_text("export FIXTURE_P10K_LOADED=yes\n")
        # Redirect only home references in the execution fixture; never change
        # the process HOME or source the developer's actual personal files.
        runtime = (userdir / ".zshrc").read_text().replace("${HOME}", "${PIMP_TEST_HOME}")
        runtime = runtime.replace("$HOME", "${PIMP_TEST_HOME}")
        (userdir / "runtime.zsh").write_text(runtime)
        (userdir / "block.zsh").write_text(runtime.split(BEGIN)[1].split(END)[0])
        driver = r'''
setopt errexit
unset ZSH ZSH_THEME GOPATH SSH_AUTH_SOCK POWERLEVEL9K_INSTANT_PROMPT
typeset -i fixture_omz_loads=0
typeset -a fixture_loaded_plugins
fixture_loaded_plugins=()
ssh-agent() {
  print called >> "$PIMP_TEST_HOME/agent-calls"
  print 'export SSH_AUTH_SOCK=/fixture/agent.sock; export SSH_AGENT_PID=12345;'
}
if [[ "$PIMP_TEST_CASE" == 'existing custom settings' ]]; then
  export SSH_AUTH_SOCK=/fixture/forwarded.sock
fi
source "$PIMP_TEST_HOME/runtime.zsh"
[[ "$CLAUDE_CODE_DISABLE_ALTERNATE_SCREEN" == 1 ]]
[[ "$CLAUDE_CODE_DISABLE_MOUSE_CLICKS" == 1 ]]
[[ "$TERM" == fixture-term ]]
[[ "$(bindkey '^U')" == *backward-kill-line ]]
[[ "$(bindkey $'\033[1~')" == *beginning-of-line ]]
[[ "$(bindkey $'\033[4~')" == *end-of-line ]]
(( fixture_omz_loads == 1 ))
(( ${plugins[(Ie)git]} && ${plugins[(Ie)zsh-syntax-highlighting]} ))
if [[ "$PIMP_TEST_CASE" == 'existing custom settings' ]]; then
  [[ "$FIXTURE_API_KEY" == "$PIMP_TEST_SECRET" ]]
  [[ "$FIXTURE_LITERAL" == '{{ do_not_template_this }}' ]]
  [[ "$aliases[keep_me]" == 'printf personal' ]]
  [[ "$(fixture_function)" == personal ]]
  [[ "$GOPATH" == /fixture/custom-go ]]
  [[ "$ZSH_THEME" == my-custom-theme ]]
  [[ "$SSH_AUTH_SOCK" == /fixture/forwarded.sock ]]
  (( ${plugins[(Ie)local-custom]} ))
  (( ! ${fixture_loaded_plugins[(Ie)git]} ))
  zstyle -s ':omz:update' mode fixture_mode
  [[ "$fixture_mode" == disabled ]]
  [[ "${FIXTURE_P10K_LOADED:-}" == '' ]]
elif [[ "$PIMP_TEST_CASE" == 'empty theme' ]]; then
  [[ "$ZSH_THEME" == '' && "${FIXTURE_P10K_LOADED:-}" == '' ]]
else
  [[ "$ZSH_THEME" == powerlevel10k/powerlevel10k ]]
  [[ "$FIXTURE_P10K_LOADED" == yes ]]
fi
if [[ "$PIMP_TEST_CASE" == 'empty theme' ]]; then
  [[ "${FIXTURE_SECRET_LOADED:-}" == '' ]]
else
  [[ "$FIXTURE_SECRET_LOADED" == yes ]]
fi
fixture_plugins_before="${(j:,:)plugins}"
source "$PIMP_TEST_HOME/block.zsh"
(( fixture_omz_loads == 1 ))
[[ "${(j:,:)plugins}" == "$fixture_plugins_before" ]]
'''
        result = subprocess.run(
            ["zsh", "-f", "-c", driver], capture_output=True, text=True,
            env={**os.environ, "PIMP_TEST_HOME": str(userdir), "PIMP_TEST_CASE": name,
                 "PIMP_TEST_SECRET": SECRET, "TERM": "fixture-term",
                 "XDG_CACHE_HOME": str(userdir / ".cache")},
        )
        assert result.returncode == 0, name + "\n" + result.stdout + result.stderr
        calls = userdir / "agent-calls"
        if name == "existing custom settings":
            assert not calls.exists(), "Must preserve a forwarded/existing agent"
        else:
            assert calls.read_text() == "called\n", "Must start only one agent"
        print(f"PASS: startup, plugin merge, agent, and secrets for {name}", flush=True)

    # Exercise the real macOS bootstrap command against an installer fixture.
    # The fixture simulates the installer's destructive default if the keep
    # option is ever lost, without accessing the network or the real HOME.
    mac = root / "mac bootstrap"
    mac.mkdir()
    (mac / ".zshrc").write_text(original)
    bin_dir = mac / "bin"
    bin_dir.mkdir()
    installer = '''set -eu
keep=false
for argument in "$@"; do
  [ "$argument" != --keep-zshrc ] || keep=true
done
if [ "$keep" != true ]; then
  printf 'clobbered\\n' > "$PIMP_TEST_HOME/.zshrc"
fi
mkdir -p "$PIMP_TEST_HOME/.oh-my-zsh"
'''
    (mac / "installer.sh").write_text(installer)
    curl = bin_dir / "curl"
    curl.write_text('#!/bin/sh\ncat "$PIMP_TEST_HOME/installer.sh"\n')
    curl.chmod(0o755)
    mac_tasks = [task for task in yaml.safe_load((repo / "tasks/main.yml").read_text())
                 if task["name"].endswith("(macOS)")]
    run(mac, tasks=mac_tasks, environment={
        "PATH": str(bin_dir) + os.pathsep + os.environ["PATH"],
        "PIMP_TEST_HOME": str(mac),
    })
    assert (mac / ".zshrc").read_text() == original
    assert (mac / ".oh-my-zsh").is_dir()
    print("PASS: macOS bootstrap preserves the existing .zshrc", flush=True)


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="pimp-my-shell-zshrc-") as directory:
        check_zshrc(Path(directory))
