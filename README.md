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
- **Kitty** — the official binary installer, Linux desktop integration, and the Dracula theme from [kitty-themes](https://github.com/dexpota/kitty-themes)
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

Prerequisite packages (zsh, git, curl, tmux, bat, fontconfig, dconf-cli, Node.js, compilers, ripgrep, fd, …) are installed automatically via **apt** on Linux and **Homebrew** on macOS — and only the packages the selected components actually need. The role also provides compatible Go and fzf releases for the editors. Set `install_prerequisites: false` to skip this if another role already provides them.

Neovim requires **0.12+ with LuaJIT** for the bundled Tree-sitter plugin revision. On Linux, an existing compatible executable is reused; otherwise the role builds the configured release into `~/.local`. Rust/Cargo are installed with rustup if missing, and `tree-sitter-cli` is built with `cargo install --locked` when missing or older than 0.26.1.

Selecting either editor also installs **Go 1.27.2** when Go is missing, for vim-go,
Go development, and Go-based Mason tools. The role downloads the official archive
for Linux or macOS on amd64/arm64 and verifies its published SHA-256 checksum.
Releases live under `~/.local/share/go/<version>` with `go` and `gofmt` symlinks in
`~/.local/bin`. Ensure that directory comes first on your shell's `PATH`; the
role's Bash and Zsh configurations already include it. Existing Go installations
are reused unless `upgrade_components=true` requests an upgrade to `go_version`.

## Role dependencies

[`gantsign.oh-my-zsh`](https://galaxy.ansible.com/gantsign/oh-my-zsh) is declared in `meta/main.yml` and runs **on Linux when the zsh component is selected** (it installs zsh and oh-my-zsh and sets the default shell). A Neovim-only run skips it, preserving the existing `.zshrc`, theme, and login shell. On macOS this role bootstraps oh-my-zsh with the official installer script when zsh is selected.

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

### Restoring an overwritten Zsh configuration

Older versions ran the Oh My Zsh dependency even during `only_neovim=true` and
could overwrite an existing `~/.zshrc`. Neovim-only runs now skip that dependency
and all Zsh tasks. Runs that select Zsh intentionally manage `.zshrc`; both the
dependency and this role's Zsh template keep Ansible backups when changing it.

List the backups on the affected machine:

```bash
ls -lt ~/.zshrc*
```

Ansible backup names resemble `~/.zshrc.<PID>.<DATE>@<TIME>~`. Inspect candidates
and select the backup from **before the first unwanted change**. Repeated runs
can create later backups that already contain the unwanted configuration.

```bash
# Keep the current file too; mktemp gives it a unique name.
zshrc_saved=$(mktemp "$HOME/.zshrc.before-restore.XXXXXX")
cp -p "$HOME/.zshrc" "$zshrc_saved"

# Replace this example path with the actual backup you chose.
cp -p '/full/path/to/the/chosen/.zshrc.backup~' "$HOME/.zshrc"
exec zsh
```

Restoring the file recovers its previous theme, plugins, and custom settings.
If there is no usable backup and you want the role's Powerlevel10k configuration,
save the current file as above, then explicitly select Zsh:

```bash
ansible-playbook playbook.yml -K -e only_zsh=true \
  -e oh_my_zsh_theme=powerlevel10k/powerlevel10k
exec zsh
```

The Powerlevel10k command rebuilds the managed configuration; it cannot recover
customizations from a lost original file. The role's Zsh snippet now preserves
the terminal's existing `TERM` value, including `tmux-256color` inside tmux.

## Role variables

Defaults from `defaults/main.yml`:

| Variable | Default | Description |
|----------|---------|-------------|
| `install_prerequisites` | `true` | Install required apt/Homebrew packages and compatible editor tools |
| `upgrade_components` | `false` | Upgrade existing dependencies for the selected components |
| `go_version` | `1.27.2` | Go release for missing toolchains and explicit editor upgrades |
| `go_install_dir` | `~/.local/share/go` | Parent directory for versioned Go installations |
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
| `only_neovim` | Neovim, LazyVim, Go, Rust/Cargo, fzf, plugins, and Tree-sitter highlighters |
| `only_vim` | Existing awesome-vimrc setup, Vim plugins, and `~/.vimrc` |
| `only_bashrc` | `~/.bashrc` |
| `only_kitty` | Kitty terminal, Linux desktop integration, and Dracula theme |
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

# Upgrade Neovim, LazyVim, Go, Rust, fzf, and Tree-sitter.
ansible-playbook playbook.yml -K -e only_neovim=true -e upgrade_components=true

# Upgrade every component managed by this role.
ansible-playbook playbook.yml -K -e upgrade_components=true

# Neovim plus Nerd Fonts and tmux (multiple flags form a union).
ansible-playbook playbook.yml -K -e only_neovim=true -e only_nerdfonts=true -e only_tmux=true

# Examples for other components.
ansible-playbook playbook.yml -K -e only_kitty=true
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
shell command names are not redirected. Neovim-only runs install Neovim and its
prerequisites without running the Zsh, Vim, or other unselected components.

Fresh installations use the configured Go/Neovim/fzf/Tree-sitter releases, the bundled
Lazy lockfile, and current upstream branches for the other Git-based tools.
Use `upgrade_components=true` to update selected apt/Homebrew packages, fonts,
Git checkouts, TPM plugins, and Lazy plugins. The Neovim component also updates
Rust's stable toolchain, upgrades older fzf and Tree-sitter executables to the configured
version, builds the configured Neovim release when needed, and synchronizes parsers.
Either editor selection upgrades an older Go toolchain to `go_version` when
prerequisites are enabled. Newer existing Go/Neovim/fzf/Tree-sitter versions are
retained. Normal reruns reuse compatible tools; plugin changes made through
`:Lazy` are preserved.

System packages use the versions available in your configured distribution or
Homebrew repositories; these can lag upstream releases. Mason manages language
servers, formatters, and debuggers independently. To refresh the controller's
Galaxy dependencies before an upgrade, run:

```bash
ansible-galaxy role install -r requirements.yml --force
ansible-galaxy collection install -r requirements.yml --upgrade
```

Flags are independent — `only_neovim` does not pull in `only_nerdfonts`, even though the Neovim config renders glyphs that want a Nerd Font. Advanced callers can bypass the flags by passing `pimp_my_shell_components` directly as a role parameter, e.g. `pimp_my_shell_components: [neovim, tmux]`. Vim and Neovim are separate components; a default run installs both.

## Kitty terminal

Kitty installs with the [official binary installer](https://sw.kovidgoyal.net/kitty/binary/)
into `~/.local/kitty.app` on Linux or `~/Applications/kitty.app` on macOS, with
`launch=n` so provisioning does not open a terminal. Both `kitty` and `kitten`
are linked into `~/.local/bin`; ensure that directory is on your `PATH`.

On Linux the role installs `kitty.desktop` and `kitty-open.desktop` into
`~/.local/share/applications`, rewrites their executable and icon paths, and
sets `~/.config/xdg-terminals.list` to `kitty.desktop`.

The themes repository is shallow-cloned into `~/.config/kitty/kitty-themes`.
`~/.config/kitty/theme.conf` links to `kitty-themes/themes/Dracula.conf`, and
`kitty.conf` includes `./theme.conf` while retaining other settings. Dracula is
used regardless of `dark_mode`. Normal reruns retain the installed binaries and
themes; add `-e upgrade_components=true` to reinstall the latest Kitty release
and update the themes repository.

## Vim Go tools

The Vim component installs vim-go's 15 helper programs with individual `go install`
tasks. Cold builds of tools such as `gopls` and `golangci-lint` can take several
minutes. Ansible reports the tool name and polls every 10 seconds while it builds;
failed commands report their compiler or download errors and stop the installation.
Each build has a deadline, and builds run on one host at a time to avoid exhausting
the shared CI runner when Molecule tests multiple distributions.

| Variable | Default | Description |
|----------|---------|-------------|
| `vim_go_install_timeout` | `900` | Maximum seconds allowed per tool build |
| `vim_go_build_jobs` | `2` | Parallel build jobs and Go runtime CPU limit per build |
| `vim_go_tools` | vim-go's 15 tools | Dictionary of executable names to Go package/version references; see `defaults/main.yml` |

Tools go into `go env GOBIN`, or the first `go env GOPATH` entry's `bin` directory
when GOBIN is empty (normally `~/go/bin`). Normal reruns check actual executables
and repair missing tools; they no longer trust `vim_go_is_installed.txt`. Existing
tools are upgraded only with `upgrade_components=true`.

For a slower machine, allow more time per tool while installing only Vim:

```bash
ansible-playbook playbook.yml -K -e only_vim=true -e vim_go_install_timeout=1800
```

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
| `neovim_version` | `v0.12.6` | Linux source release for installs and explicit upgrades |
| `neovim_minimum_version` | `0.12.0` | Minimum accepted Neovim; must support the bundled plugins |
| `neovim_tree_sitter_version` | `0.27.1` | Tree-sitter CLI release for installs and explicit upgrades |
| `neovim_fzf_version` | `0.74.4` | Upstream fzf release when missing, incompatible, or explicitly upgraded |
| `neovim_fzf_minimum_version` | `0.53.0` | Minimum compatible fzf for the bundled fuzzy picker |
| `neovim_lazygit_version` | `0.66.0` | Checksum-verified lazygit release for missing installs or explicit upgrades |
| `neovim_prefix` | `~/.local` | Linux installation prefix |
| `neovim_config_dir` | `$XDG_CONFIG_HOME/nvim` or `~/.config/nvim` | Destination for the bundled config |
| `neovim_treesitter_languages` | `[all]` | Upstream parser languages; five custom dialects and their dependencies always install |
| `neovim_treesitter_jobs` | `4` | Concurrent parser builds |
| `neovim_treesitter_timeout` | `3600` | Timeout in seconds per parser installation phase |

Configuration files are managed with Ansible copy backups; a plugin lockfile is
seeded only on new installations so later `:Lazy` updates survive role reruns.
Existing unrelated configuration files are preserved. Remove any existing custom
colorscheme plugin yourself if migrating another configuration to the default theme.
`install_prerequisites: false` assumes compatible Neovim, Go, fzf, and system build tools
already exist; the user-local Rust/Cargo and plugin setup still runs.

### Useful hotkeys for power users

These shortcuts apply to the bundled LazyVim configuration, which uses Neo-tree
for the sidebar and fzf-lua for search. Press `Esc` to enter normal mode first.
`Space` is the leader key: `Space → e` means press the keys in sequence;
`Ctrl+h` means hold Ctrl while pressing h. Uppercase letters require Shift.

#### Sidebar and tabs

| Action | Keys |
|--------|------|
| Toggle the file sidebar | `Space → e` |
| Open the selected sidebar file in a **new tab**, keeping the current tab | Lowercase `t` while focused in Neo-tree |
| Open the selected sidebar file in the current editor pane | `Enter` while focused in Neo-tree |
| Create an empty tab | `Space → Tab → Tab` |
| Go to the next tab | `gt` or `Space → Tab → ]` |
| Go to the previous tab | `gT` or `Space → Tab → [` |
| Close the current tab | `Space → Tab → d` |

To keep your current file in its own tab, open the sidebar with
`Space → e`, highlight another file, and press **`t`**. Use `gt` and `gT` to
switch between the tabs. You can also run `:tabedit path/to/file` followed by
`Enter` to open a file directly in a new tab.

#### Panes and splits

| Action | Keys |
|--------|------|
| Move focus to the pane on the left | `Ctrl+h` |
| Move focus to the pane on the right | `Ctrl+l` |
| Move focus to the pane below | `Ctrl+j` |
| Move focus to the pane above | `Ctrl+k` |
| Split the editor to the right | `Space → \|` |
| Split the editor below | `Space → -` |
| Close the focused pane | `Space → w → d` |
| Toggle zoom for the focused pane | `Space → w → m` |

With the sidebar on the left and the editor on the right, `Ctrl+l` moves into
the editor and `Ctrl+h` returns to the sidebar. These shortcuts move between
Neovim panes; tmux panes have their own bindings.

#### Search and open files

| Action | Keys |
|--------|------|
| Find a file by name | `Space → Space` |
| Search text across files | `Space → /` |
| Pick an already-open file (buffer) | `Space → ,` |
| Show the previous / next open buffer | `Shift+H` / `Shift+L` |
| Switch back to the previously edited buffer | `Space → b → b` |
| Close the current buffer | `Space → b → d` |
| Save the current file | `Ctrl+s` |
| Search available key mappings | `Space → s → k` |

Files remain open as buffers when you switch files in the same pane. A tab holds
its own arrangement of panes. This configuration disables bufferline's visual
file bar; use `Space → ,` to see open buffers. Inside the fzf picker, `Ctrl+t`
opens Trouble's results list. To open a sidebar file in a new tab, use Neo-tree's
`t` mapping above.

#### Code navigation and editing

Language-server actions require a server attached to the current file and support
for the requested action; formatting requires a configured formatter.

| Action | Keys |
|--------|------|
| Jump to the symbol's definition | `gd` |
| Find references to the symbol | `gr` |
| Show documentation for the symbol | `K` |
| Rename the symbol | `Space → c → r` |
| Choose a code action or suggested fix | `Space → c → a` |
| Format the file | `Space → c → f` |
| Jump to the next / previous diagnostic | `]d` / `[d` |
| Open LazyGit for the current repository | `Space → g → g` |

Press `Space` and pause to see the available shortcut groups, or press
`Space → Tab` and pause for the tab menu. See the
[LazyVim keymap reference](https://www.lazyvim.org/keymaps) and
[Neo-tree mappings](https://github.com/nvim-neo-tree/neo-tree.nvim#quickstart)
for more; the tables above account for this role's sidebar, picker, and bufferline
settings.

### File and text search on Mint/Ubuntu

`Space Space` opens the fuzzy file picker; `Space /` searches file contents.
Both use `fzf-lua`. Some distribution packages are too old for the configured
picker: fzf 0.44.1, for example, fails with `unknown action: transform`.
The role uses [fzf's upstream Git installer](https://github.com/junegunn/fzf#using-git),
not apt or Homebrew, to install fzf. The equivalent interactive commands are:

```bash
git clone --depth 1 https://github.com/junegunn/fzf.git ~/.fzf
~/.fzf/install
```

For Neovim-only runs, Ansible checks out the configured release when fzf is missing
or below the supported minimum and runs `~/.fzf/install --bin`. This installs the
executable without touching `.zshrc`, `.bashrc`, or other shell configuration.
It links `~/.local/bin/fzf` to `~/.fzf/bin/fzf`; Neovim prefers this over an old
distro copy earlier on PATH. CLI-tools runs use `--all` to enable shell integration.
The upstream installer normally downloads a native binary and falls back to
compiling with Go when a binary is unavailable. Compatible existing versions are
retained on normal Neovim-only reruns; use `upgrade_components=true` for upgrades.

To repair an installation made with an older role checkout, update the checkout
and rerun your normal command, then restart Neovim:

```bash
ansible-playbook playbook.yml -K -e only_neovim=true
```

This compatibility repair does not require the upgrade flag. If search still
fails, run `:checkhealth fzf-lua` and `:messages` in Neovim. The role also installs
`rg` and `fd`/`fdfind`; a general health check reporting that fzf exists does not
establish version compatibility.

### Understanding health-check warnings

The Neovim prerequisites include lazygit, fd/fdfind, Linux inotify tools, SQLite,
and an isolated `pynvim` environment in the Neovim data directory (`nvim/python`).
The Python provider uses that environment instead of distro or project packages.
Unused Node, Perl, and Ruby remote-plugin providers and Lazy's unused LuaRocks
support are disabled in the bundled configuration. Re-enable the corresponding
settings in `lua/config/options.lua` or `lua/config/lazy.lua` if adding plugins
that need them. Language servers and external language tools are separate from
these remote-plugin providers.

Some upstream health checks also inspect optional or disabled features:

- Mason reports absent PHP/Composer, Java/Javac, Julia, or LuaRocks even when no
  selected language tool needs them. Install those runtimes when using their
  Mason packages; they are not required for the bundled Go/YAML/JSON setup.
- Snacks reports its disabled picker/explorer/statuscolumn modules. This config
  uses fzf-lua and Neo-tree. Enabling competing modules solely to clear these
  messages would change the configured editor behavior.
- Image, LaTeX, and Mermaid previews need optional conversion tools and a
  terminal supporting the Kitty graphics protocol, such as Kitty or Ghostty.
  Installing a terminal executable cannot add that protocol to an existing
  GNOME/MATE terminal session. Norg is not among the bundled supported parsers.
- Which-key's `gc`, `gr`, `a`, and `i` prefix overlap reports are informational;
  they describe normal operator/text-object mappings, not duplicate bindings.
- Dashboard checks may report that it did not open when Neovim was launched
  with a file. Headless checks also cannot verify interactive UI setup.

Run `:checkhealth` in an interactive Neovim session for terminal/UI diagnostics.
The role preserves these upstream reports so real failures remain visible.

### Tree-sitter setup

The role runs the same script you can run locally, from any directory:

```bash
~/.config/nvim/highlight.sh
# Explicitly upgrade Rust, Lazy plugins, and Tree-sitter, then update parsers:
~/.config/nvim/highlight.sh --upgrade
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

CI runs Debian, Parrot, Mint, Ubuntu, and Kali in five independent Molecule jobs,
each with its own Ubuntu runner and one container. A sixth job runs the Darwin
scenario directly on a `macos-15` runner using Homebrew. All six jobs start after
lint passes; a Linux distro failure does not cancel the other distro jobs.

Each job runs the full role and verifies the editors, template highlighting,
fuzzy pickers, Python provider, SQLite, and repeated highlighting setup. The
Darwin scenario also verifies Kitty, fonts, shell configuration files, and
Terminal.app profiles. Parser and Cargo builds use two workers in these scenarios
to leave resources available for the CI runner.

To run linting and the Linux container tests locally:

Use a Python 3.14 virtual environment, as CI does, to keep pip dependencies separate from system packages such as `pyOpenSSL` and `cryptography`.
Python 3.14 is the newest controller version supported by the current [Ansible release](https://docs.ansible.com/projects/ansible/latest/reference_appendices/release_and_maintenance.html#ansible-core-support-matrix).
Install virtual environment support for your Python version if missing (for example, `python3.14-venv` on Debian/Ubuntu). Docker must be running for the container tests.

```bash
python3.14 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install molecule "molecule-plugins[docker]" ansible ansible-core ansible-lint docker psutil yamllint
python -m pip check
ansible-galaxy install -r requirements.yml
ansible-galaxy collection install -r molecule/default/requirements.yml
yamllint .
ansible-lint
bash tests/highlight.sh
python tests/upgrades.py
python tests/selection.py
python tests/kitty.py
python tests/fzf.py
python tests/go.py
python tests/vim_go.py
# Optional: build all vim-go tools in temporary directories (downloads required).
python tests/vim_go.py --real
# After provisioning a test Neovim config and its custom parsers:
nvim --headless -u NONE -i NONE -l tests/neovim.lua
NVIM_HIGHLIGHT_SETUP=1 nvim --headless -i NONE -c 'luafile tests/pickers.lua'
NVIM_HIGHLIGHT_SETUP=1 nvim --headless -i NONE -c 'luafile tests/health.lua'
molecule --debug list # Validate scenario/driver configuration without creating containers
molecule --debug syntax # Check role discovery and converge playbook syntax
ansible-playbook -i localhost, molecule/default/pull.yml # Refresh base images with download retries
molecule converge   # Ubuntu, Debian, Kali, Parrot, and Mint containers
molecule verify     # Both editors, template highlighting, and repeat-run checks
molecule destroy
deactivate
```

To test just one Linux distro, keep the same platform selection for the image
download and Molecule test:

```bash
export MOLECULE_PLATFORM_NAME=debian-pimp-my-shell
ansible-playbook -i localhost, molecule/default/pull.yml
molecule test --platform-name "$MOLECULE_PLATFORM_NAME"
unset MOLECULE_PLATFORM_NAME
```

`molecule test` runs dependency installation, container creation, converge,
verify, and container destruction. The platform filter applies to every stage,
so the other four containers are not created. With no selection, the default
scenario continues to test all five Linux distributions.

On a macOS test host or disposable VM with Homebrew installed, use
`molecule test -s darwin`. This scenario configures the current user's machine
directly; it does not create or destroy a VM. It uses the same converge and
editor verification playbooks as Linux. The role preserves the runner's
preinstalled Go toolchain, so the exact downloaded Go version is asserted only
for the fresh Linux containers.

The Linux Mint image is published for amd64 only; on an arm64 host it needs qemu/binfmt emulation (`docker run --privileged tonistiigi/binfmt --install amd64`). All other images are multi-arch.

Molecule pulls the official Debian and Ubuntu base images from
[Docker's public ECR repository](https://aws.amazon.com/blogs/containers/docker-official-images-now-available-on-amazon-elastic-container-registry-public/)
to avoid Docker Hub's unauthenticated pull quota on shared CI runners. Both the
scenario image references and Dockerfile `FROM` lines use that registry. These
public pulls need no AWS account or registry credentials.

Each Linux CI job downloads only its selected base image, using `pull.yml` above. Each
failed download gets up to five retries, waiting 60 seconds between attempts.
The playbook reads the image names and architectures from `molecule.yml` and
checks for newer images even when a local copy exists. Molecule then builds with
`pull: false`, so a successful download is reused without another forced registry
request. Run the same pull command before local container tests to refresh their
base images. Without `MOLECULE_PLATFORM_NAME`, the pull playbook downloads all five
images. CI limits the download step to 30 minutes and stops if it fails.

Kali, Parrot, and Mint still use their upstream Docker Hub repositories. A
`toomanyrequests: You have reached your unauthenticated pull rate limit` error
during image downloads is a registry failure before the role runs. Docker Hub
authentication timeouts such as `Client.Timeout exceeded while awaiting headers`
are also download failures; the retries can recover from a temporary outage,
but cannot bypass an exhausted quota or a prolonged registry outage.
If it affects one of those images locally, authenticate with `docker login`
and retry. CI authentication, if added later, should use a read-only Docker Hub
token and keep credentials out of pull-request jobs.

### CI security and action updates

CI uses GitHub-hosted runners, read-only repository permissions, and full commit
SHA pins for all external actions. Checkout credentials are not persisted for
test commands, and the workflow does not request secrets or OIDC credentials.
Job timeouts and cancellation of superseded runs bound resource usage.
Dependabot checks action versions weekly and opens update PRs; updates still
need review and passing CI. Action pins are Git commit SHAs, not SHA-256 digests.

See the [workflow security audit](docs/ci-security-audit.md) for verified action
versions, findings, and the repository settings that need separate verification.

## License

Apache-2.0

## Author

[mr-pmillz](https://github.com/mr-pmillz) — Black Hills Information Security

Extracted from the `customize-terminal` role in [ansible-role-kali-parrot](https://github.com/mr-pmillz/ansible-role-kali-parrot) and generalized for Ubuntu, Debian, Linux Mint, Kali, Parrot, and macOS.
