"""Verify pane-local tabs, navigation, ownership, and unsaved work in a real UI."""

import os
from pathlib import Path
import signal
import tempfile
import time

import pynvim


def check_panes(root: Path) -> None:
    root = root.resolve()
    paths = {name: root / f"{name}.txt" for name in ("first", "second", "third", "fourth")}
    for path in paths.values():
        path.write_text("test file\n" * 40)
    os.environ["NVIM_HIGHLIGHT_SETUP"] = "1"
    n = pynvim.attach("child", argv=[os.environ.get("NVIM_BIN", "nvim"), "--embed", "--headless", "-i", "NONE"])

    def settle():
        time.sleep(0.08)
        n.api.get_mode()

    def keys(text):
        n.input(text)
        settle()

    def open_file(name, command="edit"):
        path = paths.get(name, name)
        n.exec_lua("vim.api.nvim_cmd({cmd=select(2,...),args={(...)},magic={file=false}}, {})", str(path), command)
        settle()
        return n.current.window.handle

    def reset():
        keys("<Esc>")
        n.command("silent! tabonly!")
        n.command("only!")
        n.exec_lua("""
          for _, buf in ipairs(vim.fn.getbufinfo({buflisted=1})) do
            if vim.bo[buf.bufnr].buftype == '' then
              vim.api.nvim_buf_delete(buf.bufnr, {force=true})
            end
          end
        """)
        settle()
        return open_file("first")

    def files(win):
        assert not n.api.get_mode()["blocking"], "Unexpected prompt while reading the pane's files"
        return n.exec_lua("return vim.tbl_map(function(b) return vim.api.nvim_buf_get_name(b) end, require('config.panes').buffers(...))", win)

    def header(win):
        fmt = n.api.get_option_value("winbar", {"win": win})
        return n.api.eval_statusline(fmt, {"winid": win, "use_winbar": True})["str"]

    def point(win, label, close=False):
        text = header(win)
        index = text.index(label)
        if close:
            index = text.index("×", index)
        else:
            index += 1
        row, col = n.api.win_get_position(win)
        return row, col + n.funcs.strdisplaywidth(text[:index])

    def mouse(action, pos, button="left"):
        n.api.input_mouse(button, action, "", 0, *pos)
        settle()

    def click(win, label, close=False):
        pos = point(win, label, close)
        mouse("press", pos)
        mouse("release", pos)

    def center(win):
        row, col = n.api.win_get_position(win)
        return row + 1 + n.api.win_get_height(win) // 2, col + n.api.win_get_width(win) // 2

    def two_groups():
        left = reset()
        open_file("second")
        right = open_file("third", "vsplit")
        open_file("fourth")
        return left, right

    try:
        n.ui_attach(160, 50, rgb=True)
        n.exec_lua("vim.wait(10000,function() return package.loaded['config.panes'] ~= nil end,20)")
        assert n.exec_lua("return package.loaded['config.panes'] ~= nil")
        mapping = n.funcs.maparg("]b", "n", False, True)
        assert mapping.get("desc") == "Next file in pane", (
            "Pane setup did not finish", mapping,
            n.exec_lua("return vim.tbl_map(function(n) return n.msg end, Snacks.notifier.get_history())"),
        )
        n.options["mousetime"] = 1

        left, right = two_groups()
        assert files(left) == [str(paths[x]) for x in ("first", "second")], files(left)
        assert files(right) == [str(paths[x]) for x in ("third", "fourth")], files(right)
        assert "first.txt" in header(left) and "third.txt" not in header(left)
        assert "third.txt" in header(right) and "first.txt" not in header(right)
        assert n.api.win_get_position(right)[1] > n.api.win_get_position(left)[1]
        assert n.options["showtabline"] == 1 and n.options["tabline"] == ""
        print("PASS: each split has its own file tabs directly above it", flush=True)

        for key, expected in (("H", "third"), ("L", "fourth"), ("]b", "third"), ("[b", "fourth"), ("<Space>bb", "third"), ("<C-^>", "fourth")):
            keys(key)
            assert n.current.window.handle == right
            assert n.current.buffer.name == str(paths[expected]), (key, n.current.buffer.name)
        keys("<C-h>")
        assert n.current.window.handle == left
        keys("H")
        assert n.current.buffer.name == str(paths["first"])
        keys("<Space>bb")
        assert n.current.buffer.name == str(paths["second"])
        click(right, "third.txt")
        assert n.current.window.handle == right and n.current.buffer.name == str(paths["third"])
        assert n.api.buf_get_name(n.api.win_get_buf(left)) == str(paths["second"])
        print("PASS: keyboard cycling, alternate file, pane focus, and tab clicks stay in their pane", flush=True)

        n.api.set_current_win(left)
        keys("<Space>bo")
        assert files(left) == [str(paths["second"])]
        assert files(right) == [str(paths[x]) for x in ("third", "fourth")]
        print("PASS: close-other-files affects only the current pane", flush=True)

        left, right = two_groups()
        n.api.win_set_cursor(right, [12, 2])
        sy, sx = n.api.win_get_position(right)
        mouse("press", (sy, sx + 1))
        mouse("drag", center(left))
        mouse("release", center(left))
        assert not n.api.win_is_valid(left)
        assert n.current.window.handle == right
        assert n.api.win_get_cursor(right) == [12, 2]
        assert set(files(right)) == {str(path) for path in paths.values()}
        for path in paths.values():
            assert path.name in header(right)
        print("PASS: joining panes merges all file tabs and preserves the dragged view", flush=True)

        left, right = two_groups()
        n.options["hidden"] = False
        n.api.set_current_win(left)
        n.current.buffer[0] = "unsaved moved tab"
        moved = n.current.buffer.number
        mouse("press", point(left, "second.txt"))
        mouse("drag", center(right))
        mouse("release", center(right))
        assert files(left) == [str(paths["first"])]
        assert files(right) == [str(paths[x]) for x in ("third", "fourth", "second")]
        assert n.current.buffer.number == moved
        assert n.current.buffer[0] == "unsaved moved tab"
        assert n.api.buf_get_name(n.api.win_get_buf(left)) == str(paths["first"])
        n.options["hidden"] = True
        print("PASS: dragging a file tab moves its membership and preserves unsaved edits", flush=True)

        click(right, "second.txt", close=True)
        keys("c")
        assert n.current.buffer[0] == "unsaved moved tab"
        assert str(paths["second"]) in files(right)
        click(right, "second.txt", close=True)
        keys("s")
        assert paths["second"].read_text().startswith("unsaved moved tab")
        assert str(paths["second"]) not in files(right)
        assert n.current.buffer.name == str(paths["third"])
        n.api.set_current_win(left)
        click(right, "fourth.txt", close=True)
        assert n.current.window.handle == left
        assert files(right) == [str(paths["third"])]
        print("PASS: close buttons confirm edits, save correctly, and target inactive panes", flush=True)

        left = reset()
        n.current.buffer[0] = "shared dirty buffer"
        shared = n.current.buffer.number
        right = open_file("first", "vsplit")
        click(right, "first.txt", close=True)
        assert not n.api.win_is_valid(right)
        assert n.api.buf_get_lines(shared, 0, 1, False) == ["shared dirty buffer"]
        assert n.api.get_option_value("modified", {"buf": shared})
        assert files(left) == [str(paths["first"])]
        n.api.set_current_win(left)
        n.command("edit!")
        print("PASS: closing one shared file view keeps the other pane and its unsaved edits", flush=True)

        left, right = two_groups()
        n.api.set_current_win(left)
        open_file("third")
        shared = n.current.buffer.number
        n.current.buffer[0] = "shared hidden edits"
        # The right pane owns this file behind its active fourth.txt tab.
        click(left, "third.txt", close=True)
        assert str(paths["third"]) not in files(left)
        assert str(paths["third"]) in files(right)
        assert n.api.buf_get_lines(shared, 0, 1, False) == ["shared hidden edits"]
        n.api.set_current_win(right)
        keys("H")
        assert n.current.buffer.number == shared
        n.command("edit!")
        click(right, "fourth.txt", close=True)
        click(right, "third.txt", close=True)
        assert not n.api.win_is_valid(right)
        assert files(left) == [str(paths[x]) for x in ("first", "second")]
        print("PASS: hidden shared tabs retain edits; closing a pane's final tab closes just that pane", flush=True)

        left, right = two_groups()
        keys(":q<CR>")
        assert not n.api.win_is_valid(right)
        assert set(files(left)) == {str(paths[x]) for x in ("first", "second", "third")}, files(left)
        assert str(paths["fourth"]) not in files(left)
        print("PASS: :q closes one pane, retaining its other hidden files in the surviving pane", flush=True)

        left = reset()
        for directory in ("alpha", "beta"):
            path = root / directory / "same.txt"
            path.parent.mkdir()
            path.write_text(directory)
            open_file(path)
        unusual = root / "雪 %literal.txt"
        unusual.write_text("unicode and percent")
        open_file(unusual)
        assert "alpha/same.txt" in header(left) and "beta/same.txt" in header(left)
        assert unusual.name in header(left)
        right = open_file("fourth", "vsplit")
        n.api.win_set_width(left, 28)
        settle()
        assert "literal.txt" in header(left) and "×" in header(left), header(left)
        click(left, "‹")
        assert "first.txt" in header(left) or "same.txt" in header(left), header(left)
        n.api.set_current_win(left)
        keys("H")
        assert "same.txt" in header(left)
        print("PASS: narrow panes scroll their tabs; duplicate names, Unicode, and percent signs render safely", flush=True)

        left = reset()
        open_file("second")
        new_page = open_file("third", "tabedit")
        assert files(new_page) == [str(paths["third"])]
        keys("gT")
        assert n.current.window.handle == left
        assert files(left) == [str(paths[x]) for x in ("first", "second")]
        print("PASS: native Neovim tab pages retain independent pane file groups", flush=True)
    finally:
        try:
            n.input("<Esc><Esc>")
            n.command("qa!")
        except (EOFError, OSError):
            pass
        n.close()


if __name__ == "__main__":
    def timeout(signum, frame):
        raise TimeoutError("Pane tab checks exceeded 60 seconds")

    signal.signal(signal.SIGALRM, timeout)
    signal.alarm(60)
    with tempfile.TemporaryDirectory(prefix="pms-pane-tabs-") as directory:
        check_panes(Path(directory))
