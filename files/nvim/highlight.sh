#!/usr/bin/env bash
# Install LazyVim plugins and every supported Tree-sitter language, then verify them.
set -euo pipefail

if [[ ${1:-} == --help ]]; then
  cat <<'HELP'
Usage: /path/to/nvim/highlight.sh
Run from any directory. Installs Rust/Cargo if missing and builds tree-sitter-cli
with Cargo when necessary. Neovim >= 0.12, git, curl, tar, a C/C++ compiler, and
Node.js must already be available (the Ansible role installs these prerequisites).

Optional environment:
  TREESITTER_LANGUAGES   Comma-separated upstream languages (default: all)
  TREESITTER_JOBS        Maximum concurrent parser builds (default: 4)
  TREESITTER_TIMEOUT     Seconds allowed per installation phase (default: 3600)
  TREE_SITTER_VERSION   Cargo version to install if CLI is missing/old (default: 0.27.1)
  NVIM_BIN              Neovim executable (default: nvim)

The five Go-template dialects and their base languages are always included.
Re-running repairs missing parsers and updates parsers to the installed plugin's
revisions. Unsupported upstream languages (tier 4) are excluded by nvim-treesitter.
HELP
  exit 0
fi
[[ $# == 0 ]] || { echo "Unknown argument; use --help" >&2; exit 2; }

config_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
export PATH="${CARGO_HOME:-$HOME/.cargo}/bin:$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
export TREESITTER_JOBS=${TREESITTER_JOBS:-4}
export TREESITTER_TIMEOUT=${TREESITTER_TIMEOUT:-3600}
export TREESITTER_LANGUAGES=${TREESITTER_LANGUAGES:-all}
for value in "$TREESITTER_JOBS" "$TREESITTER_TIMEOUT"; do
  [[ $value =~ ^[1-9][0-9]*$ ]] || { echo "Jobs and timeout must be positive integers" >&2; exit 2; }
done
nvim_bin=${NVIM_BIN:-nvim}
for tool in "$nvim_bin" git curl tar cc c++ node; do
  command -v "$tool" >/dev/null || { echo "Required executable missing: $tool" >&2; exit 1; }
done
"$nvim_bin" --clean --headless -i NONE -c 'lua os.exit(vim.fn.has("nvim-0.12") == 1 and jit and 0 or 1)' || {
  echo 'Neovim >= 0.12 with LuaJIT is required.' >&2
  exit 1
}

if ! cargo --version >/dev/null 2>&1 || ! rustc --version >/dev/null 2>&1; then
  installer=$(mktemp)
  trap 'rm -f "$installer"' EXIT
  curl --proto '=https' --tlsv1.2 -fsSL https://sh.rustup.rs -o "$installer"
  sh "$installer" -y --profile minimal
  cargo --version
  rustc --version
  echo HIGHLIGHT_CHANGED=1
fi

cli_version=$(tree-sitter --version 2>/dev/null || true)
if ! [[ $cli_version =~ ^tree-sitter\ ([0-9]+)\.([0-9]+)\.([0-9]+) ]] ||
  ! (( BASH_REMATCH[1] > 0 || BASH_REMATCH[2] > 26 || (BASH_REMATCH[2] == 26 && BASH_REMATCH[3] >= 1) )); then
  cargo install --locked tree-sitter-cli --version "${TREE_SITTER_VERSION:-0.27.1}"
  echo HIGHLIGHT_CHANGED=1
fi

# Resolve this configuration independently of the working directory or user's
# default NVIM_APPNAME. Data/cache/state still respect the caller's XDG settings.
export XDG_CONFIG_HOME
XDG_CONFIG_HOME=$(dirname -- "$config_dir")
export NVIM_APPNAME
NVIM_APPNAME=$(basename -- "$config_dir")
export NVIM_HIGHLIGHT_SETUP=1
export NVIM_HIGHLIGHT_CONFIG="$config_dir"

"$nvim_bin" --headless -i NONE -c 'lua dofile(vim.env.NVIM_HIGHLIGHT_CONFIG .. "/scripts/plugins.lua")'
# Use a fresh process without plugin startup jobs competing with parser installs.
"$nvim_bin" --headless -u NONE -i NONE -l "$config_dir/scripts/highlight.lua"
