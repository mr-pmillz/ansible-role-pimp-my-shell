# LazyVim configuration

Based on Phil's active configuration and
[ImpostorKeanu/my-nvim](https://github.com/ImpostorKeanu/my-nvim), revision
`991ba54479b94d58c883ebc042b96b0bdd352c44` (Apache-2.0; see LICENSE).
The custom colorscheme override is omitted so LazyVim uses Tokyo Night.

The Go-template grammar factory and highlight queries are from
[ngalaiko/tree-sitter-go-template](https://github.com/ngalaiko/tree-sitter-go-template),
revision `aa71f63de226c5592dfbfc1f29949522d7c95fac` (MIT;
see tree-sitter-go-template/LICENSE). Only the source factory and queries are
bundled; generated C files and shared libraries are built on the target host.

Run `./highlight.sh` from any directory to install Rust/Cargo if needed,
tree-sitter-cli, missing Lazy plugins, all supported Tree-sitter parsers and
queries, and the five Go-template dialects. Run `./highlight.sh --help` for
prerequisites and optional settings. Run `./highlight.sh --upgrade` to update
Rust's stable toolchain, Lazy plugins, and an older Tree-sitter CLI, then synchronize
parser revisions and pick up new supported languages. `:Lazy` also remains available
for interactive plugin updates. Normal script runs preserve compatible tools and
existing plugin versions.

File search (`Space Space`) and text search (`Space /`) use fzf-lua. Provide
fzf >= 0.53, ripgrep, and fd/fdfind. The Ansible role installs these prerequisites
and repairs incompatible distro fzf versions using the upstream Git checkout and
`~/.fzf/install --bin`, without changing shell configuration. The picker prefers `~/.local/bin/fzf`,
then `~/.fzf/bin/fzf`, before falling back to PATH.

`config/treesitter.lua` is the shared custom-parser registration; it uses
`stdpath("config")` and registers again on `User TSUpdate`. Generated files are
under `tree-sitter/`; installed parsers live in `stdpath("data")/site`.

The installer deliberately returns failure for broken builds or invalid queries,
and it can repair a partial install on a later run. Language servers, formatters,
and debug adapters remain managed by the existing LazyVim/Mason configuration.
