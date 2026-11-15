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

Each pane has its own clickable file tabs directly above it, replacing the global
Bufferline row. A new right split has its file tab above that right split.
Drag a pane's **⠿** grip onto another pane's edge to move the pane and all its tabs,
or into its center to join the panes. The dragged pane stays visible and the two
file lists merge, including unsaved changes. Drag a filename to move that file tab
into another pane or a new split. Dropping onto a pane's tab row also moves the
file there. Right-click a file tab for the current pane, vertical/horizontal split,
or new-tab menu; splitting adds another view of the file. The preview labels each destination;
`Esc` cancels. Divider dragging still resizes panes and text dragging selects text.

Files changed by Codex, Claude Code, or other tools refresh automatically within
about half a second, including atomic saves and files behind inactive tabs.
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

File tabs have red **×** close buttons, including modified files marked **●**.
Click **×**, or middle-click a filename, to close it. Closing the last tab in a
pane closes that pane; closing the final file exits Neovim. Save/Discard/Cancel
protects unsaved work. Closing one shared view retains edits in the other pane.
Narrow panes show **‹** / **›** buttons to scroll their tabs.
Typed `:q` / `:quit` closes one pane and removes its file from the bar when no
other pane owns it; the closed pane's other files move to a surviving pane.
In the last pane, it switches to another open file if one remains. `:wq` saves
then does the same; `:qa` explicitly quits everything. The file groups and close
buttons live in `config/panes.lua`; typed quit handling lives in `config/quit.lua`.

Normal-mode shortcuts (`Space` is the leader):

| Keys | Action |
|------|--------|
| `Shift+h` / `Shift+l`, or `[b` / `]b` | Previous / next file in this pane |
| `Space b b` or `Ctrl+6` | Previous active file in this pane |
| `Space b j` | Pick a file from this pane |
| `Space ,` or `Space f b` | Pick any open file and add it to this pane |
| `Space b d` | Close this file tab |
| `Space b o` | Close other file tabs in this pane |
| `Space b l` / `Space b r` | Close file tabs to the left / right |
| `[B` / `]B` | Move the current file tab left / right |
| `Ctrl+h/j/k/l` | Focus the pane to the left / below / above / right |

Neovim tab pages represent separate pane layouts, with their own native top row
when multiple layouts are open. Switch between them with `gt` / `gT`.

In Kitty, drag without Shift so Neovim receives the mouse events. Shift is for
Kitty's terminal text selection. Kitty launch actions and desktop file drops
are separate workflows; no Kitty remapping is required for Neo-tree dragging.

`config/treesitter.lua` is the shared custom-parser registration; it uses
`stdpath("config")` and registers again on `User TSUpdate`. Generated files are
under `tree-sitter/`; installed parsers live in `stdpath("data")/site`.

The installer deliberately returns failure for broken builds or invalid queries,
and it can repair a partial install on a later run. Language servers, formatters,
and debug adapters remain managed by the existing LazyVim/Mason configuration.
