# Ansible Role: pimp-my-shell

[![CI](https://github.com/mr-pmillz/ansible-role-pimp-my-shell/actions/workflows/ci.yml/badge.svg)](https://github.com/mr-pmillz/ansible-role-pimp-my-shell/actions/workflows/ci.yml)

Pimp your terminal on Linux and macOS. This role configures:

- **zsh** — [oh-my-zsh](https://ohmyz.sh/) with [powerlevel10k](https://github.com/romkatv/powerlevel10k), zsh-autosuggestions, zsh-syntax-highlighting, curated aliases, and a templated `~/.zshrc`
- **Nerd Fonts** — the four MesloLGS NF faces powerlevel10k recommends
- **tmux** — [oh-my-tmux](https://github.com/gpakosz/.tmux) plus [TPM](https://github.com/tmux-plugins/tpm) with plugins pre-installed
- **vim** — [awesome-vimrc](https://github.com/amix/vimrc) with 12 extra plugins (YouCompleteMe, vim-go, vim-airline, fzf.vim, …) and a `dark_mode`-aware config
- **CLI tools** — [bat](https://github.com/sharkdp/bat) config and [fzf](https://github.com/junegunn/fzf) installed from git
- **Boot console** — UTF-8 charmap so powerlevel10k glyphs render on the Linux boot console
- **Terminal profiles** — GNOME Terminal (Ubuntu/Debian/Mint), XFCE Terminal (Kali), MATE Terminal (Parrot), and Terminal.app (macOS), light or dark

## Supported platforms

| OS | Architectures |
|----|---------------|
| Ubuntu | amd64, arm64 |
| Debian | amd64, arm64 |
| Linux Mint | amd64, arm64 |
| Kali Linux | amd64, arm64 |
| Parrot OS | amd64, arm64 |
| macOS (13+) | amd64 (Intel), arm64 (Apple Silicon) |

The CPU architecture is detected dynamically from `ansible_facts['architecture']` and normalized to `amd64`/`arm64`; unsupported distributions or architectures fail fast with a clear message. On macOS the Homebrew prefix is selected per-architecture (`/opt/homebrew` on Apple Silicon, `/usr/local` on Intel). Downstream installers (fzf, YouCompleteMe, vim-go) detect or compile for the host architecture on their own.

## Requirements

- Ansible **2.15+** and the `community.general` collection (see `requirements.yml`)
- **Linux**: `sudo` privileges (run plays with `-K` or passwordless sudo) — used only to install prerequisite packages and configure the boot console
- **macOS**: [Homebrew](https://brew.sh) must already be installed (the role refuses to install it because that requires an interactive sudo prompt). Homebrew tasks run as the login user, not root.

Prerequisite packages (zsh, git, curl, tmux, vim, bat, fontconfig, dconf-cli, build tooling for YouCompleteMe, …) are installed automatically via **apt** on Linux and **Homebrew** on macOS — and only the packages the selected components actually need. Set `install_prerequisites: false` to skip this if another role already provides them.

A Go toolchain is **optional**: when `go` is present, vim-go binaries are installed; otherwise that step is skipped cleanly.

## Role dependencies

[`gantsign.oh-my-zsh`](https://galaxy.ansible.com/gantsign/oh-my-zsh) is declared in `meta/main.yml` and runs automatically before this role **on Linux** (it installs zsh and oh-my-zsh and sets the default shell). On macOS it is skipped and this role bootstraps oh-my-zsh with the official installer script instead.

```bash
ansible-galaxy install -r requirements.yml
```

## Role variables

Defaults from `defaults/main.yml`:

| Variable | Default | Description |
|----------|---------|-------------|
| `install_prerequisites` | `true` | Install required apt/Homebrew packages before configuring |
| `dark_mode` | `false` | Dark theme for bat, vim colorscheme, and terminal profiles |
| `oh_my_zsh_users` | `[{username: <ansible_user_id>}]` | Users passed to gantsign.oh-my-zsh on Linux |
| `oh_my_zsh_theme` | `powerlevel10k/powerlevel10k` | zsh theme |
| `oh_my_zsh_plugins` | `[ansible, git, golang, docker, …]` | oh-my-zsh plugins to load |
| `oh_my_zsh_update_mode` | `reminder` | `disabled`, `auto`, or `reminder` |
| `oh_my_zsh_update_frequency` | `7` | Days between oh-my-zsh update checks |
| `oh_my_zsh_write_zshrc` | `true` | Whether gantsign.oh-my-zsh writes an initial `~/.zshrc` |

### Selective installation

By default every component runs. Setting any `only_*` flag narrows the run to just the flags you set (flags union):

| Flag | Component |
|------|-----------|
| `only_nerdfonts` | MesloLGS Nerd Fonts |
| `only_zsh` | oh-my-zsh plugins, powerlevel10k, `~/.zshrc` |
| `only_console_setup` | UTF-8 boot console charmap (Linux) |
| `only_tmux` | oh-my-tmux, TPM plugins, `~/.tmux.conf.local` |
| `only_cli_tools` | bat config and fzf |
| `only_vim` | awesome-vimrc, vim plugins, `~/.vimrc` |
| `only_bashrc` | `~/.bashrc` |
| `only_terminal_profiles` | OS-specific terminal profiles |

```bash
ansible-playbook playbook.yml -K -e only_vim=true -e only_tmux=true
```

Flags are independent — `only_vim` does not pull in `only_nerdfonts`, even though the vim config renders glyphs that want a Nerd Font. Advanced callers can bypass the flags by passing `pimp_my_shell_components` directly as a role parameter, e.g. `pimp_my_shell_components: [vim, tmux]`.

## Example playbook

```yaml
---
- name: Pimp my shell
  hosts: localhost
  connection: local
  roles:
    - role: mr_pmillz.pimp_my_shell
      dark_mode: true
```

With a `requirements.yml` in your project:

```yaml
---
roles:
  - name: mr_pmillz.pimp_my_shell
    src: https://github.com/mr-pmillz/ansible-role-pimp-my-shell.git
    scm: git
    version: main

collections:
  - name: community.general
```

```bash
ansible-galaxy install -r requirements.yml
ansible-playbook playbook.yml -K
```

## Testing

Linting and container tests (macOS cannot be tested in containers; test it on a real host or VM):

```bash
yamllint .
ansible-lint
pip install molecule "molecule-plugins[docker]"
molecule converge   # Ubuntu, Debian, Kali, Parrot, and Mint containers
molecule destroy
```

The Linux Mint image is published for amd64 only; on an arm64 host it needs qemu/binfmt emulation (`docker run --privileged tonistiigi/binfmt --install amd64`). All other images are multi-arch.

## License

Apache-2.0

## Author

[mr-pmillz](https://github.com/mr-pmillz) — Black Hills Information Security

Extracted from the `customize-terminal` role in [ansible-role-kali-parrot](https://github.com/mr-pmillz/ansible-role-kali-parrot) and generalized for Ubuntu, Debian, Linux Mint, Kali, Parrot, and macOS.
