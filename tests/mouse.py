"""Exercise the installed config with a real Neovim UI and mouse input.

Run with the role's nvim/python/bin/python (pynvim), after provisioning plugins.
XDG directories and NVIM_BIN can point at a disposable installation.
"""

import os
from pathlib import Path
import signal
import tempfile
import time

import pynvim


def check_mouse(root: Path) -> None:
    first = root / "first.txt"
    second = root / "second space | %.txt"
    first.write_text("first buffer\n" * 80)
    second.write_text("second buffer\n" * 80)
    os.environ["NVIM_HIGHLIGHT_SETUP"] = "1"
    nvim = pynvim.attach(
        "child", argv=[os.environ.get("NVIM_BIN", "nvim"), "--embed", "--headless", "-i", "NONE"]
    )
    grid = [[" "] * 160 for _ in range(50)]

    def lua(code, *args):
        return nvim.exec_lua(code, *args)

    def settle():
        # Mouse input is asynchronous; separate events so positions aren't coalesced.
        time.sleep(0.06)
        # Only fast API calls work while a native popup is waiting for input.
        nvim.api.get_mode()

    def mouse(action, row, col, button="left"):
        nvim.api.input_mouse(button, action, "", 0, row, col)
        settle()

    def screen():
        # Read the UI's actual redraw stream, including native popup menus.
        while nvim._session._pending_messages:
            message = nvim.next_message()
            if message.type != "notification" or message.name != "redraw":
                continue
            for event, *updates in message.args:
                for update in updates:
                    if event == "grid_line":
                        _, row, col, cells, *_ = update
                        for cell in cells:
                            for _ in range(cell[2] if len(cell) > 2 else 1):
                                grid[row][col] = cell[0] or " "
                                col += 1
                    elif event == "grid_clear":
                        for row in grid:
                            row[:] = [" "] * 160
                    elif event == "grid_scroll":
                        _, top, bottom, left, right, rows, cols = update
                        assert cols == 0
                        old = [row[:] for row in grid]
                        for row in range(top, bottom):
                            if top <= row + rows < bottom:
                                grid[row][left:right] = old[row + rows][left:right]
        return ["".join(row) for row in grid]

    def tree_file():
        return lua("""
          local file = ...
          for _, win in ipairs(vim.api.nvim_tabpage_list_wins(0)) do
            if vim.bo[vim.api.nvim_win_get_buf(win)].filetype == 'neo-tree' then
              local state = require('neo-tree.sources.manager').get_state_for_window(win)
              if not state or not state.tree then return end
              local node, line = state.tree:get_node(file)
              if node and line and line <= vim.api.nvim_buf_line_count(vim.api.nvim_win_get_buf(win)) then
                local pos = vim.fn.screenpos(win, line, 1)
                if pos.row > 0 then return { win, pos.row - 1, pos.col + 5 } end
              end
            end
          end
        """, str(second))

    def reset():
        nvim.input("<Esc>")
        nvim.command("silent! tabonly!")
        nvim.command("silent! Neotree close")
        nvim.command("only!")
        lua("vim.api.nvim_cmd({cmd='edit',args={...},magic={file=false}}, {})", str(first))
        target = nvim.current.window.handle
        lua("require('neo-tree.command').execute({action='show',dir=...,reveal_file=select(2,...)})",
            str(root), str(second))
        deadline = time.monotonic() + 8
        while not tree_file():
            assert time.monotonic() < deadline, "Neo-tree did not render the file"
            settle()
        nvim.api.set_current_win(target)
        settle()
        return target

    def previews():
        return lua("""
          return vim.tbl_filter(function(win)
            return vim.bo[vim.api.nvim_win_get_buf(win)].filetype == 'pimp-drop-preview'
          end, vim.api.nvim_list_wins())
        """)

    def drag_to(row, col, zone=None):
        _, start_row, start_col = tree_file()
        mouse("press", start_row, start_col)
        mouse("drag", row, col)
        if zone:
            labels = {"current": "Open in this pane", "left": "Vertical split: left",
                      "right": "Vertical split: right", "above": "Horizontal split: above",
                      "below": "Horizontal split: below"}
            assert len(previews()) == 1
            assert labels[zone] in "\n".join(screen()), screen()
            config = nvim.api.win_get_config(previews()[0])
            assert not config["mouse"] and not config["focusable"]
        mouse("release", row, col)
        assert not previews(), "Drop preview did not disappear"

    def geometry(win):
        row, col = nvim.api.win_get_position(win)
        return row, col, nvim.api.win_get_height(win), nvim.api.win_get_width(win)

    def pane_count():
        # Notifications are floating windows, not editor panes.
        return lua("""
          return #vim.tbl_filter(function(win)
            return vim.api.nvim_win_get_config(win).relative == ''
          end, vim.api.nvim_tabpage_list_wins(0))
        """)

    def listed(buf):
        return nvim.api.buf_is_valid(buf) and nvim.api.get_option_value("buflisted", {"buf": buf})

    try:
        nvim.ui_attach(160, 50, rgb=True, ext_linegrid=True)
        lua("vim.wait(10000, function() return package.loaded['bufferline'] ~= nil end, 20)")
        assert lua("return package.loaded['bufferline'] ~= nil"), "Bufferline did not load"
        nvim.options["mousetime"] = 1
        assert nvim.options["mouse"] == "a"

        for zone in ("current", "left", "right", "above", "below"):
            target = reset()
            row, col, height, width = geometry(target)
            y = row + (0 if zone == "above" else height - 1 if zone == "below" else height // 2)
            x = col + (0 if zone == "left" else width - 1 if zone == "right" else width // 2)
            before = pane_count()
            drag_to(y, x, zone)
            assert nvim.current.buffer.name == str(second), (zone, nvim.current.buffer.name, screen())
            opened = nvim.current.window.handle
            if zone == "current":
                assert opened == target
                assert pane_count() == before
            else:
                assert pane_count() == before + 1
                assert nvim.api.buf_get_name(nvim.api.win_get_buf(target)) == str(first)
                new_row, new_col, _, _ = geometry(opened)
                old_row, old_col, _, _ = geometry(target)
                assert {"left": new_col < old_col, "right": new_col > old_col,
                        "above": new_row < old_row, "below": new_row > old_row}[zone]
            print(f"PASS: drag previews and opens file in {zone} pane", flush=True)

        target = reset()
        tree, row, col = tree_file()
        mouse("press", row, col)
        mouse("release", row, col)
        assert nvim.current.window.handle == tree
        assert nvim.api.buf_get_name(nvim.api.win_get_buf(target)) == str(first)
        mouse("press", row, col)
        mouse("drag", row + 1, col)
        mouse("release", row + 1, col)
        assert pane_count() == 2
        print("PASS: click selects; dropping back in sidebar does nothing", flush=True)

        target = reset()
        _, row, col = tree_file()
        nvim.options["mousetime"] = 500
        mouse("press", row, col)
        mouse("release", row, col)
        mouse("press", row, col)
        mouse("release", row, col)
        assert nvim.current.buffer.name == str(second)
        assert nvim.current.window.handle == target
        nvim.options["mousetime"] = 1
        print("PASS: double-click opens the sidebar file", flush=True)

        for mode, key in (("insert", "i"), ("visual", "v")):
            target = reset()
            nvim.input(key)
            settle()
            row, col, height, width = geometry(target)
            drag_to(row + height // 2, col + width // 2)
            assert nvim.current.buffer.name == str(second)
            assert nvim.current.window.handle == target
            assert nvim.api.get_mode()["mode"] == "n"
            print(f"PASS: explorer drag works from {mode} mode", flush=True)

        target = reset()
        row, col, height, width = geometry(target)
        mouse("press", row + 3, col + 10)
        mouse("drag", row + 4, col + 15)
        mouse("release", row + 4, col + 15)
        assert nvim.api.get_mode()["mode"] == "v"
        nvim.input("<Esc>")
        settle()
        mouse("press", row + height // 2, col - 1)
        mouse("drag", row + height // 2, col + 5)
        mouse("release", row + height // 2, col + 5)
        assert nvim.api.win_get_width(target) != width
        assert nvim.current.buffer.name == str(first)
        print("PASS: ordinary text selection and split resizing still work", flush=True)

        target = reset()
        nvim.command("belowright vsplit")
        other = nvim.current.window.handle
        row, col, height, width = geometry(target)
        drag_to(row + height // 2, col + width // 2)
        assert nvim.current.window.handle == target
        assert nvim.current.buffer.name == str(second)
        assert nvim.api.buf_get_name(nvim.api.win_get_buf(other)) == str(first)
        print("PASS: drop targets the pane under the mouse in an existing layout", flush=True)

        target = reset()
        lua("""
          vim.api.nvim_win_set_buf(..., vim.api.nvim_create_buf(false, true))
        """, target)
        row, col, height, width = geometry(target)
        drag_to(row + height // 2, col + width // 2)
        assert nvim.api.buf_get_name(nvim.api.win_get_buf(target)) == ""
        assert pane_count() == 2
        print("PASS: drops onto special buffers are ignored", flush=True)

        target = reset()
        _, row, col = tree_file()
        mouse("press", row, col, "right")
        mouse("release", row, col, "right")
        lines = screen()
        menu_row = next(i for i, line in enumerate(lines) if "New tab" in line)
        menu_col = lines[menu_row].index("New tab") + 2
        mouse("press", menu_row, menu_col)
        mouse("release", menu_row, menu_col)
        assert len(nvim.tabpages) == 2, screen()
        assert nvim.current.buffer.name == str(second)
        print("PASS: right-click menu opens a new tab with the mouse", flush=True)

        for action in ("Vertical split", "Horizontal split", "Current pane", "New tab"):
            target = reset()
            second_buf = lua("return vim.fn.bufadd(...)", str(second))
            lua("vim.fn.bufload(...)", second_buf)
            nvim.api.buf_set_lines(second_buf, 0, 1, False, ["unsaved buffer menu work"])
            if action == "Horizontal split":
                nvim.api.set_current_win(tree_file()[0])
            elif action == "Current pane":
                nvim.input("i")
            elif action == "New tab":
                nvim.input("v")
            nvim.command("redraw!")
            settle()
            tabline = screen()[0]
            tab_col = tabline.index("second space") + 2
            mouse("press", 0, tab_col, "right")
            mouse("release", 0, tab_col, "right")
            lines = screen()
            matches = [i for i, line in enumerate(lines) if action in line]
            assert matches, f"Missing buffer menu action {action}:\n" + "\n".join(lines)
            menu_row = matches[0]
            assert menu_row <= 4, "Buffer menu should appear below the clicked tab"
            menu_col = lines[menu_row].index(action) + 2
            mouse("press", menu_row, menu_col)
            mouse("release", menu_row, menu_col)
            assert nvim.current.buffer.number == second_buf
            assert nvim.current.buffer[0] == "unsaved buffer menu work"
            if action in ("Vertical split", "Horizontal split"):
                assert pane_count() == 3
                assert nvim.api.buf_get_name(nvim.api.win_get_buf(target)) == str(first)
                new_row, new_col, _, _ = geometry(nvim.current.window.handle)
                old_row, old_col, _, _ = geometry(target)
                assert new_col > old_col if action == "Vertical split" else new_row > old_row
            elif action == "Current pane":
                assert pane_count() == 2 and nvim.current.window.handle == target
            else:
                assert len(nvim.tabpages) == 2
            nvim.command("edit!")
            print(f"PASS: bufferline menu {action} uses the clicked buffer and preserves edits", flush=True)

        target = reset()
        tabline = screen()[0]
        tab_col = tabline.index("second space") + 2
        mouse("press", 0, tab_col, "right")
        mouse("release", 0, tab_col, "right")
        nvim.input("<Esc>")
        settle()
        assert nvim.current.window.handle == target
        assert nvim.current.buffer.name == str(first)
        assert pane_count() == 2
        print("PASS: cancelling the bufferline menu keeps the current file and layout", flush=True)

        target = reset()
        row, col, height, width = geometry(target)
        drag_to(row + height // 2, col + width - 1)
        second_buf = nvim.current.buffer.number
        nvim.input(":q<CR>")
        settle()
        assert pane_count() == 2, "Quit should close just the second editor pane"
        assert not listed(second_buf)
        assert "second space" not in screen()[0]
        print("PASS: :q closes the pane and removes its file from Bufferline", flush=True)

        target = reset()
        row, col, height, width = geometry(target)
        drag_to(row + height // 2, col + width // 2)
        second_buf = nvim.current.buffer.number
        nvim.input(":q<CR>")
        settle()
        assert pane_count() == 2, "The last editor pane must remain while another file is open"
        assert nvim.current.buffer.name == str(first)
        assert not listed(second_buf)
        print("PASS: :q in the last pane switches to another open file", flush=True)

        target = reset()
        nvim.command("vsplit")
        first_buf = nvim.current.buffer.number
        nvim.input(":q<CR>")
        settle()
        assert listed(first_buf)
        assert nvim.api.buf_get_name(nvim.api.win_get_buf(target)) == str(first)
        print("PASS: :q keeps files that are still displayed in another pane", flush=True)

        target = reset()
        row, col, height, width = geometry(target)
        drag_to(row + height // 2, col + width // 2)
        nvim.current.buffer[0] = "unsaved before quit"
        nvim.input(":q<CR>")
        settle()
        nvim.input("c")
        settle()
        assert nvim.current.buffer.name == str(second)
        assert nvim.current.buffer[0] == "unsaved before quit"
        nvim.command("edit!")
        print("PASS: cancelling :q preserves unsaved work", flush=True)

        target = reset()
        row, col, height, width = geometry(target)
        drag_to(row + height // 2, col + width // 2)
        second_buf = nvim.current.buffer.number
        tabline = screen()[0]
        first_col = tabline.index("first.txt") + 2
        mouse("press", 0, first_col)
        mouse("release", 0, first_col)
        assert nvim.current.buffer.name == str(first)
        tabline = screen()[0]
        close_col = tabline.index("×", tabline.index("second space"))
        mouse("press", 0, close_col)
        mouse("release", 0, close_col)
        assert not listed(second_buf)
        assert pane_count() == 2
        print("PASS: file tabs switch and close buffers without collapsing panes", flush=True)

        nvim.current.buffer[0] = "unsaved work"
        first_buf = nvim.current.buffer.number
        mouse("press", 0, first_col, "middle")
        mouse("release", 0, first_col, "middle")
        nvim.input("c")
        settle()
        assert nvim.current.buffer[0] == "unsaved work"
        assert listed(first_buf)
        assert first.read_text().startswith("first buffer")
        print("PASS: cancelling close preserves unsaved edits", flush=True)

        nvim.command("edit!")
        settle()
        assert len(lua("return vim.fn.getbufinfo({buflisted=1})")) == 1
        tabline = screen()[0]
        close_col = tabline.index("×", tabline.index("first.txt"))
        exited = False
        try:
            mouse("press", 0, close_col)
            mouse("release", 0, close_col)
        except EOFError:
            exited = True
        assert exited, "Closing the final clean file must exit the editor"
        print("PASS: the last clean file's close button exits Neovim", flush=True)
    finally:
        try:
            nvim.input("<Esc><Esc>")
            nvim.command("qa!")
        except (EOFError, OSError):
            pass
        nvim.close()


if __name__ == "__main__":
    def timeout(signum, frame):
        raise TimeoutError("Neovim mouse checks exceeded 60 seconds")

    signal.signal(signal.SIGALRM, timeout)
    signal.alarm(60)
    with tempfile.TemporaryDirectory(prefix="pimp-my-shell-mouse-files-") as directory:
        check_mouse(Path(directory))
