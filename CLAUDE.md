# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with this repository.

## Purpose

Standalone Ansible role (`mr_pmillz.pimp_my_shell`) that configures zsh (oh-my-zsh + powerlevel10k), tmux (oh-my-tmux + TPM), vim (awesome-vimrc + 12 plugins), bat, fzf, Nerd Fonts, the UTF-8 boot console, and OS-specific terminal profiles. Extracted from the `customize-terminal` role in `ansible-role-kali-parrot` and generalized.

Supported: Ubuntu, Debian, Linux Mint, Kali, Parrot, macOS — amd64 and arm64, detected dynamically (`pimp_my_shell_arch` fact set in `tasks/main.yml` from `pimp_my_shell_arch_map` in `vars/main.yml`).

## Architecture

- **Platform gate first**: `tasks/main.yml` asserts distribution ∈ `pimp_my_shell_supported_distributions` and arch ∈ {amd64, arm64} before anything runs.
- **Prerequisites are self-satisfied**: `tasks/prereqs-debian.yml` (apt, become) / `tasks/prereqs-macos.yml` (Homebrew, no become). The package list is computed from the selected components via `map('extract', pimp_my_shell_<os>_component_packages)` — only what the run needs gets installed. Toggle with `install_prerequisites`.
- **oh-my-zsh** comes from the `gantsign.oh-my-zsh` meta dependency on Linux (see `meta/main.yml`, skipped on Darwin) and from the official installer script on macOS. The `oh_my_zsh_*` defaults are shared with the gantsign role by design — do not rename them.
- **macOS Homebrew prefix** is arch-derived: `/opt/homebrew` (arm64) vs `/usr/local` (amd64), in `tasks/prereqs-macos.yml`. The role fails with a clear message if brew is missing; it never installs Homebrew itself.

### Selective installation

Public flags are deliberately unnamespaced (`only_vim`, not `pimp_my_shell_only_vim`) — this is the requested API. Mechanism in `vars/main.yml`:

- `pimp_my_shell_all_components` — canonical component list, execution order.
- `pimp_my_shell_selected_components` — components whose `only_*` flag is true (flags union).
- `pimp_my_shell_components` — selection if non-empty, else all. **Every task gate in `main.yml` reads this list.**

Adding a component means touching four places: an `only_*` default, `pimp_my_shell_all_components`, a line in `pimp_my_shell_selected_components`, the `when:` on the include — plus (optionally) a package list entry in `pimp_my_shell_<os>_component_packages`.

## Key patterns

- **Component gating is on `include_tasks`, not inside task files** — task files stay independently usable.
- **Installation guard files** (`~/fzf_is_installed.txt`, `~/vim_awesome_is_installed.txt`, …) prevent expensive re-runs (fzf install, YCM build, vim-go binaries).
- **`update: false` on git clones** — clones don't re-pull on later runs; `latest[git]` lint is noqa'd deliberately.
- **Go is optional**: vim-go binaries install only if `command -v go` succeeds (checked with an extended PATH covering /usr/local/go/bin, ~/go/bin, and Homebrew).
- **Facts, not bare vars**: use `ansible_facts['distribution']` / `['env']['HOME']` / `['user_id']` / `['user_gid']` — bare `ansible_*` fact vars are deprecated (removal in ansible-core 2.24).
- **Parrot vs Kali terminal split**: Parrot uses MATE terminal dconf dumps (needs D-Bus; Xvfb started only under Molecule/GitHub Actions). Kali is a plain XFCE `terminalrc` copy, dark/light chosen by `dark_mode`.

## Testing

```bash
yamllint .
ansible-lint            # config in .ansible-lint; var-naming skip is intentional
molecule converge       # ubuntu, debian, kali, parrot, mint containers
molecule destroy
```

Molecule Dockerfiles are deliberately minimal (python3/sudo/golang/desktop terminal only) so the role's prereq installation is actually exercised. The Mint image is amd64-only (needs binfmt on arm64 hosts). macOS is not container-testable — verify on real hardware.

## Gotchas

- `.bashrc` is a static copy (not templated), so `dark_mode` has no effect on bash sessions.
- `only_*` flags are independent, not dependency-resolved: `only_vim` won't pull in `nerdfonts`; `only_zsh` still assumes oh-my-zsh exists (meta dep on Linux / bootstrap on macOS provides it).
- The gantsign.oh-my-zsh meta dependency runs whenever the role runs on Linux, even for narrowed `only_*` runs.
- The Xvfb tasks fire-and-forget (`async: 10, poll: 0`); on real desktops the `dbus-run-session -- dconf load` works headlessly regardless.
