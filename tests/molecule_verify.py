"""Check each real Molecule verification play with an empty Ansible fact cache."""

import copy
import os
from pathlib import Path
import subprocess
import tempfile

import yaml


def verification_plays(path: Path):
    for play in yaml.safe_load(path.read_text()):
        imported = play.get("ansible.builtin.import_playbook")
        if imported:
            yield from verification_plays((path.parent / imported).resolve())
        else:
            yield path, play


def check_verification(root: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    seen = set()
    for scenario in ("default", "darwin"):
        for source, original in verification_plays(repo / "molecule" / scenario / "verify.yml"):
            identity = (source, original["name"])
            if identity in seen:
                continue
            seen.add(identity)
            play = copy.deepcopy(original)
            # Preserve the actual play/task environments and fact gathering.
            # Run each play in its own process so an earlier play cannot hide
            # a reference to facts that have not yet been collected.
            play["connection"] = "local"
            for index, filename in enumerate(play.get("vars_files", [])):
                play["vars_files"][index] = str((source.parent / filename).resolve())
            playbook = root / f"verify-{len(seen)}.yml"
            playbook.write_text(yaml.safe_dump([play], sort_keys=False))
            result = subprocess.run(
                [
                    "ansible-playbook", "-i", "localhost,", str(playbook),
                    # Gathering Facts has the always tag. Verification tasks
                    # stay skipped: no editors, Homebrew, or containers needed.
                    "--check", "--tags", "molecule-facts-only",
                ],
                env={
                    **os.environ,
                    "ANSIBLE_HOME": str(root / "ansible"),
                    "ANSIBLE_REMOTE_TEMP": str(root / "remote"),
                    "ANSIBLE_CACHE_PLUGIN": "memory",
                    "ANSIBLE_GATHERING": "explicit",
                },
                capture_output=True,
                text=True,
            )
            output = result.stdout + result.stderr
            assert result.returncode == 0, output
            assert "TASK [Gathering Facts]" in output, output
            assert output.count("TASK [") == 1, output
            print(f"PASS: fresh facts for {original['name']}", flush=True)


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="pimp-my-shell-verify-") as directory:
        check_verification(Path(directory))
