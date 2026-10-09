# Ansible Role: pimp-my-shell

[![CI](https://github.com/mr-pmillz/ansible-role-pimp-my-shell/actions/workflows/ci.yml/badge.svg)](https://github.com/mr-pmillz/ansible-role-pimp-my-shell/actions/workflows/ci.yml)

Pimp your terminal on Linux and macOS. This role configures:

- **zsh** — [oh-my-zsh](https://ohmyz.sh/) with [powerlevel10k](https://github.com/romkatv/powerlevel10k), zsh-autosuggestions, zsh-syntax-highlighting, curated aliases, and a templated `~/.zshrc`
- **Nerd Fonts** — the four MesloLGS NF faces powerlevel10k recommends
- **tmux** — [oh-my-tmux](https://github.com/gpakosz/.tmux) plus [TPM](https://github.com/tmux-plugins/tpm) with plugins pre-installed
- **Vim** — [awesome-vimrc](https://github.com/amix/vimrc) with YouCompleteMe, vim-go, vim-airline, fzf.vim, and the existing `dark_mode`-aware configuration
- **Neovim** — [LazyVim](https://www.lazyvim.org/) with the customized [my-nvim](https://github.com/ImpostorKeanu/my-nvim) configuration, the default Tokyo Night colorscheme, language extras, and all supported Tree-sitter highlighters
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

The CPU architecture is detected dynamically from `ansible_facts['architecture']` and normalized to `amd64`/`arm64`; unsupported distributions or architectures fail fast with a clear message. On macOS the Homebrew prefix is selected per-architecture (`/opt/homebrew` on Apple Silicon, `/usr/local` on Intel). Neovim and Tree-sitter compile for the host architecture on Linux; macOS uses Homebrew Neovim.

## Requirements

- Ansible **2.15+** and the `community.general` collection (see `requirements.yml`)
- **Linux**: `sudo` privileges (run plays with `-K` or passwordless sudo) — used only to install prerequisite packages and configure the boot console
- **macOS**: [Homebrew](https://brew.sh) must already be installed (the role refuses to install it because that requires an interactive sudo prompt). Homebrew tasks run as the login user, not root.

Prerequisite packages (zsh, git, curl, tmux, bat, fontconfig, dconf-cli, Node.js, compilers, ripgrep, fd, fzf, …) are installed automatically via **apt** on Linux and **Homebrew** on macOS — and only the packages the selected components actually need. Set `install_prerequisites: false` to skip this if another role already provides them.

Neovim requires **0.12+ with LuaJIT** for the bundled Tree-sitter plugin revision. On Linux, an existing compatible executable is reused; otherwise the role builds the configured release into `~/.local`. Rust/Cargo are installed with rustup if missing, and `tree-sitter-cli` is built with `cargo install --locked` when missing or older than 0.26.1. A Go toolchain is still needed for Go development and Go-based Mason tools.

## Role dependencies

[`gantsign.oh-my-zsh`](https://galaxy.ansible.com/gantsign/oh-my-zsh) is declared in `meta/main.yml` and runs automatically before this role **on Linux** (it installs zsh and oh-my-zsh and sets the default shell). On macOS it is skipped and this role bootstraps oh-my-zsh with the official installer script instead.

```bash
ansible-galaxy install -r requirements.yml
```

## Localhost quick start

With Ansible installed, use the included [playbook.example.yml](playbook.example.yml)
to configure the current user on localhost directly from this checkout:

```bash
git clone https://github.com/mr-pmillz/ansible-role-pimp-my-shell.git
cd ansible-role-pimp-my-shell
ansible-galaxy install -r requirements.yml
mv playbook.example.yml playbook.yml

# Install all components, including both Vim and Neovim.
ansible-playbook playbook.yml -K
```

If you already have this checkout, start with the dependency installation. Run the
playbook as your normal user; the role requests sudo only for system tasks. `-K`
prompts for your sudo password; omit it with passwordless sudo or on macOS when
running the user-level Homebrew setup. The playbook uses `{{ playbook_dir }}` to
load this checkout directly, so no role installation or path editing is needed.
Your local `playbook.yml` is ignored by Git.

To add only Neovim alongside an existing awesome-vimrc installation, use this
instead of the all-components command:

```bash
ansible-playbook playbook.yml -K -e only_neovim=true
```

The example enables `dark_mode: true`. Edit `playbook.yml` for persistent settings,
or use the [selection flags](#selective-installation) below to choose components
for each run. You can also run `playbook.example.yml` directly without renaming it.

## Role variables

Defaults from `defaults/main.yml`:

| Variable | Default | Description |
|----------|---------|-------------|
| `install_prerequisites` | `true` | Install required apt/Homebrew packages before configuring |
| `dark_mode` | `false` | Dark theme for bat, Vim, and terminal profiles (LazyVim keeps its default theme) |
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
| `only_neovim` | Neovim, LazyVim, Rust/Cargo, plugins, and Tree-sitter highlighters |
| `only_vim` | Existing awesome-vimrc setup, Vim plugins, and `~/.vimrc` |
| `only_bashrc` | `~/.bashrc` |
| `only_terminal_profiles` | OS-specific terminal profiles |

After the [localhost quick start](#localhost-quick-start), run any of these commands (omit `-K` when sudo does not require a password):

```bash
# Install everything, including both Vim and Neovim.
ansible-playbook playbook.yml -K

# Install/configure only the existing awesome-vimrc component.
ansible-playbook playbook.yml -K -e only_vim=true

# Add Neovim + LazyVim alongside an existing awesome-vimrc installation.
# This skips the role's Vim tasks and leaves ~/.vimrc and ~/.vim_runtime alone.
ansible-playbook playbook.yml -K -e only_neovim=true

# Install both editors, without the other optional components.
ansible-playbook playbook.yml -K -e only_vim=true -e only_neovim=true

# Neovim plus Nerd Fonts and tmux (multiple flags form a union).
ansible-playbook playbook.yml -K -e only_neovim=true -e only_nerdfonts=true -e only_tmux=true

# Examples for other components.
ansible-playbook playbook.yml -K -e only_zsh=true -e only_cli_tools=true
ansible-playbook playbook.yml -K -e only_terminal_profiles=true -e dark_mode=true

# Optionally limit upstream parsers for a smaller Neovim setup.
ansible-playbook playbook.yml -K -e only_neovim=true \
  -e '{"neovim_treesitter_languages": ["bash", "go", "lua", "python", "yaml"]}'
```

Repeat the same command to reconcile that selection. The Neovim installer checks
actual installed state, skips compatible tools and completed plugin/parser builds,
and repairs missing files. A successful unchanged rerun reports no Neovim changes.
The existing Vim component retains its original installation guards. After installing
both, launch `vim` for awesome-vimrc or `nvim` for LazyVim. Your default editor and
shell command names are not redirected. On Linux the role's existing
`gantsign.oh-my-zsh` dependency still runs before the selected components.

Flags are independent — `only_neovim` does not pull in `only_nerdfonts`, even though the Neovim config renders glyphs that want a Nerd Font. Advanced callers can bypass the flags by passing `pimp_my_shell_components` directly as a role parameter, e.g. `pimp_my_shell_components: [neovim, tmux]`. Vim and Neovim are separate components; a default run installs both.

## Neovim and highlighting

The role bundles the customized Lua configuration and language extras from the local
`my-nvim` setup, without its colorscheme override. Vim and Neovim coexist:
`vim` uses `~/.vimrc` and `~/.vim_runtime`, while `nvim` uses `~/.config/nvim`
and `~/.local/share/nvim`. The existing awesome-vimrc tasks and plugins remain
available via `only_vim`. Use `only_neovim` to install LazyVim independently.
The role does not redirect `vim`/`vi` or change your default editor. Both editors
are included when no `only_*` flags are set.

| Variable | Default | Description |
|----------|---------|-------------|
| `neovim_version` | `v0.12.6` | Linux source release used when Neovim is missing or too old |
| `neovim_minimum_version` | `0.12.0` | Minimum accepted Neovim; must support the bundled plugins |
| `neovim_prefix` | `~/.local` | Linux installation prefix |
| `neovim_config_dir` | `$XDG_CONFIG_HOME/nvim` or `~/.config/nvim` | Destination for the bundled config |
| `neovim_treesitter_languages` | `[all]` | Upstream parser languages; five custom dialects and their dependencies always install |
| `neovim_treesitter_jobs` | `4` | Concurrent parser builds |
| `neovim_treesitter_timeout` | `3600` | Timeout in seconds per parser installation phase |

Configuration files are managed with Ansible copy backups; a plugin lockfile is
seeded only on new installations so later `:Lazy` updates survive role reruns.
Existing unrelated configuration files are preserved. Remove any existing custom
colorscheme plugin yourself if migrating another configuration to the default theme.
`install_prerequisites: false` assumes a compatible Neovim and system build tools
already exist; the user-local Rust/Cargo and plugin setup still runs.

The role runs the same script you can run locally, from any directory:

```bash
~/.config/nvim/highlight.sh
# Optional smaller set; Go-template dialects still install:
TREESITTER_LANGUAGES=bash,go,lua,python,yaml ~/.config/nvim/highlight.sh
```

It installs missing Lazy plugins, discovers all languages supported by the installed
`nvim-treesitter` main revision, waits for compilation, installs matching queries,
and verifies parser loading and queries. Query-only helper languages are installed
alongside their dependents. Upstream tier-4 unsupported languages are excluded.
Reruns repair incomplete installations and update parser revisions without updating
the plugins themselves. Failures return a nonzero exit status; inspect `:TSLog` and
rerun to retry. There is no permanent success marker hiding failed builds.

The script also generates Bash, CUE, HTML, JSON, and YAML Go-template dialects using
the bundled upstream grammar. Files such as `config.yaml.gotmpl`, `page.gohtml`, and
`.env.gotmpl` get both template and embedded-language highlighting. It respects XDG
data/cache/state locations and uses the configuration beside the script.

Mason retains the language-server, formatter, and debugger settings from the local
configuration; those tools are managed by LazyVim/Mason and are separate from
Tree-sitter parser installation. The initial all-language build needs network access
and may take several minutes. `highlight.sh --help` lists its environment settings.

References: [LazyVim requirements](https://www.lazyvim.org/),
[nvim-treesitter main API](https://github.com/nvim-treesitter/nvim-treesitter/blob/main/README.md),
[Tree-sitter CLI installation](https://github.com/tree-sitter/tree-sitter/blob/master/crates/cli/README.md).

## Use the role from another project

For a checkout on localhost, use the [included example](playbook.example.yml) above.
For a separate Ansible project, install the role with Galaxy and use this playbook:

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
# After provisioning a test Neovim config and its custom parsers:
nvim --headless -u NONE -i NONE -l tests/neovim.lua
pip install molecule "molecule-plugins[docker]"
molecule --debug list # Validate scenario/driver configuration without creating containers
molecule --debug syntax # Check role discovery and converge playbook syntax
molecule converge   # Ubuntu, Debian, Kali, Parrot, and Mint containers
molecule verify     # Both editors, template highlighting, and repeat-run checks
molecule destroy
```

The Linux Mint image is published for amd64 only; on an arm64 host it needs qemu/binfmt emulation (`docker run --privileged tonistiigi/binfmt --install amd64`). All other images are multi-arch.

## License

Apache-2.0

## Author

[mr-pmillz](https://github.com/mr-pmillz) — Black Hills Information Security

Extracted from the `customize-terminal` role in [ansible-role-kali-parrot](https://github.com/mr-pmillz/ansible-role-kali-parrot) and generalized for Ubuntu, Debian, Linux Mint, Kali, Parrot, and macOS.
