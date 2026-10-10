# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with this repository.

## Purpose

Standalone Ansible role (`mr_pmillz.pimp_my_shell`) that configures zsh (oh-my-zsh + powerlevel10k), tmux (oh-my-tmux + TPM), Vim (awesome-vimrc + 12 plugins), Neovim (LazyVim + custom language extras + Tree-sitter), bat, fzf, Nerd Fonts, the UTF-8 boot console, and OS-specific terminal profiles. Extracted from the `customize-terminal` role in `ansible-role-kali-parrot` and generalized.

Supported: Ubuntu, Debian, Linux Mint, Kali, Parrot, macOS — amd64 and arm64, detected dynamically (`pimp_my_shell_arch` fact set in `tasks/main.yml` from `pimp_my_shell_arch_map` in `vars/main.yml`).

## Architecture

- **Platform gate first**: `tasks/main.yml` asserts distribution ∈ `pimp_my_shell_supported_distributions` and arch ∈ {amd64, arm64} before anything runs.
- **Prerequisites are self-satisfied**: `tasks/prereqs-debian.yml` (apt, become) / `tasks/prereqs-macos.yml` (Homebrew, no become). The package list is computed from the selected components via `map('extract', pimp_my_shell_<os>_component_packages)` — only what the run needs gets installed. Toggle with `install_prerequisites`.
- **oh-my-zsh** comes from the `gantsign.oh-my-zsh` meta dependency on Linux only when zsh is selected (see `meta/main.yml`, skipped on Darwin) and from the official installer script on macOS. The `oh_my_zsh_*` defaults are shared with the gantsign role by design — do not rename them.
- **macOS Homebrew prefix** is arch-derived: `/opt/homebrew` (arm64) vs `/usr/local` (amd64), in `tasks/prereqs-macos.yml`. The role fails with a clear message if brew is missing; it never installs Homebrew itself.

### Selective installation

Public flags are deliberately unnamespaced (`only_vim`, not `pimp_my_shell_only_vim`) — this is the requested API. Mechanism in `vars/main.yml`:

- `pimp_my_shell_all_components` — canonical component list, execution order.
- `pimp_my_shell_selected_components` — components whose `only_*` flag is true (flags union).
- `pimp_my_shell_components` — selection if non-empty, else all. **Every task gate in `main.yml` reads this list.**

Adding a component means touching four places: an `only_*` default, `pimp_my_shell_all_components`, a line in `pimp_my_shell_selected_components`, the `when:` on the include — plus (optionally) a package list entry in `pimp_my_shell_<os>_component_packages`.

## Key patterns

- **Component gating is on `include_tasks`, not inside task files** — task files stay independently usable.
- **Installation guard files** still cover fzf and the existing Vim installers. Neovim setup checks actual plugin/parser state, waits for builds, verifies queries, and returns failures instead of recording a permanent success marker.
- **`update: false` on git clones** — clones don't re-pull on later runs; `latest[git]` lint is noqa'd deliberately.
- **Neovim**: `only_neovim` selects `neovim`; `only_vim` continues to select the independent awesome-vimrc `vim` component. Both run by default and use separate config/data directories and commands. Linux builds a compatible Neovim if necessary; Homebrew provides macOS Neovim. The shared `files/nvim/highlight.sh` installs Rust/Cargo if missing, tree-sitter-cli, Lazy plugins, and all supported parsers. Either editor provisions missing Go through `tasks/go.yml`, using checksum-verified upstream archives and user-local symlinks.
- **Upgrades**: `upgrade_components: false` preserves existing versions on normal reruns. Opting in updates selected package/Git dependencies, Go, and the Neovim Rust/Lazy/Tree-sitter setup; newer installed Go/Neovim/Tree-sitter releases are not downgraded.
- **Fuzzy search**: `tasks/neovim-fzf.yml` repairs missing or incompatible fzf using upstream's Git checkout and `install --bin`, even for `only_neovim`, without editing shell files. CLI-tools uses `install --all` for shell integration. Neither apt nor Homebrew installs fzf. The picker prefers `~/.local/bin/fzf`, then `~/.fzf/bin/fzf`, over distro PATH entries. `tests/fzf.py` checks installation, repairs, upgrades, and shell preservation. `tests/pickers.lua` exercises real file and live-grep results; run it with the installed config, not `-u NONE` or `-l`.
- **Bundled config**: `files/nvim` contains source configuration only. Custom Go-template parsers are generated on the target. `files/nvim-lazy-lock.json` seeds new installs without overwriting user plugin updates. Keep the upstream grammar license and provenance in `files/nvim/README.md`.
- **Facts, not bare vars**: use `ansible_facts['distribution']` / `['env']['HOME']` / `['user_id']` / `['user_gid']` — bare `ansible_*` fact vars are deprecated (removal in ansible-core 2.24).
- **Parrot vs Kali terminal split**: Parrot uses MATE terminal dconf dumps (needs D-Bus; Xvfb started only under Molecule/GitHub Actions). Kali is a plain XFCE `terminalrc` copy, dark/light chosen by `dark_mode`.

## Testing

```bash
yamllint .
ansible-lint            # config in .ansible-lint; var-naming skip is intentional
molecule converge       # ubuntu, debian, kali, parrot, mint containers
molecule destroy
```

Molecule Dockerfiles are deliberately minimal (python3/sudo/desktop terminal only) so the role's prereq installation, including Go, is actually exercised. CI uses five Linux matrix jobs: `MOLECULE_PLATFORM_NAME` filters image downloads and `molecule test --platform-name` filters the entire container lifecycle. The Mint image is amd64-only (needs binfmt on arm64 hosts). `MOLECULE_GLOB=molecule/darwin/molecule.yml molecule test -s darwin` tests macOS directly on a native host; CI uses a separate `macos-15` runner and sets that glob for every step. Keep discovery restricted: `list -s darwin` can otherwise load the Linux scenario and require its Docker driver. The Darwin scenario shares the full-role converge and editor verification playbooks and adds macOS-specific checks. Both scenarios limit Cargo and parser builds to two workers.

## Gotchas

- `.bashrc` is a static copy (not templated), so `dark_mode` has no effect on bash sessions.
- `only_*` flags are independent, not dependency-resolved: `only_vim` won't pull in `nerdfonts`; `only_zsh` still assumes oh-my-zsh exists (meta dep on Linux / bootstrap on macOS provides it).
- The gantsign.oh-my-zsh meta dependency uses the same zsh selection gate as the parent and forces every user's `write_zshrc` false. The macOS installer uses `--keep-zshrc`. `tasks/zshrc.yml` backs up and merges a single marked block, preserves existing content and permissions, validates syntax, and suppresses secrets in logs/diffs. Keep user additions outside the markers. `tests/zshrc.py` exercises preservation, updates, startup, and backups.
- The Xvfb tasks fire-and-forget (`async: 10, poll: 0`); on real desktops the `dbus-run-session -- dconf load` works headlessly regardless.
