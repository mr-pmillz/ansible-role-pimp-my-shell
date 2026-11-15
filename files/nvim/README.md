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

Mouse support is enabled. In Neo-tree (`Space e`), double-click to open a file,
or drag it into an editor pane: the center opens in place, the left/right three
columns create vertical splits, and the top/bottom two rows create horizontal
splits (left/right wins at corners). Right-click a file for a mouse-selectable
menu with explicit split directions and a new-tab action. Drops never move files
on disk; special buffers and the sidebar are not drop targets. A shaded preview
labels the current pane or horizontal/vertical split destination while dragging.
This integration lives in `config/mouse.lua`.

Drag a pane's **⠿ filename** header onto another pane's edge to move that pane,
or into its center to join the panes. The dragged pane stays visible and both
files stay in Bufferline, including unsaved changes. Drag a Bufferline filename
to open that buffer in a pane or new split. The preview labels each destination;
`Esc` cancels. Divider dragging still resizes panes and text dragging selects text.

Files changed by Codex, Claude Code, or other tools refresh automatically within
about half a second, including atomic saves and hidden Bufferline buffers.
Unsaved edits are kept, with a warning when the disk version changes. A deleted
file also keeps its buffer. `config/reload.lua` uses Neovim's timestamp checks.

Terminal pastes automatically normalize carriage returns and strip ANSI color
and hyperlink codes. Normal paste preserves blank lines and code indentation.
For copied agent output, **Space p a** (or `:PasteAgent`) reads the tmux copy
buffer and also removes common leading spaces and collapses excess blank lines
to one. Outside tmux it reads the system clipboard; `:PasteAgent +` explicitly
uses the clipboard and `:PasteAgent a` uses register `a`. Relative indentation
is preserved, and one undo reverses the paste. Terminal soft wrapping cannot
always be distinguished from intentional line breaks, so lines aren't reflowed.
Set `vim.g.pimp_my_shell_clean_paste = false` to disable automatic cleanup.
This integration lives in `config/paste.lua` and leaves embedded terminal input alone.

Bufferline provides clickable file tabs and red **×** close buttons. Closing
uses Snacks to preserve the split layout and prompt before discarding edits.
Modified files show a dot; middle-click their tab to close with a save prompt.
Closing the last file exits Neovim, after confirming any unsaved work.
Typed `:q` / `:quit` closes one pane and removes its file from the bar when no
other pane displays it. In the last pane, it switches to another open file if
one remains. `:wq` saves then does the same; `:qa` explicitly quits everything.
The command abbreviations and closing behavior live in `config/quit.lua`.
Neovim tab pages continue to represent separate window layouts.

In Kitty, drag without Shift so Neovim receives the mouse events. Shift is for
Kitty's terminal text selection. Kitty launch actions and desktop file drops
are separate workflows; no Kitty remapping is required for Neo-tree dragging.

`config/treesitter.lua` is the shared custom-parser registration; it uses
`stdpath("config")` and registers again on `User TSUpdate`. Generated files are
under `tree-sitter/`; installed parsers live in `stdpath("data")/site`.

The installer deliberately returns failure for broken builds or invalid queries,
and it can repair a partial install on a later run. Language servers, formatters,
and debug adapters remain managed by the existing LazyVim/Mason configuration.
