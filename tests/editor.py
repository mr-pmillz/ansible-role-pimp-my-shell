"""Exercise external edits and terminal pastes in the installed Neovim config."""

import os
from pathlib import Path
import signal
import shlex
import subprocess
import tempfile
import time

import pynvim


def check_editor(root: Path) -> None:
    root = root.resolve()
    file = root / "agent.txt"
    other = root / "hidden.txt"
    file.write_text("before\nline two\n")
    other.write_text("hidden before\n")
    env = os.environ.copy()
    env["NVIM_HIGHLIGHT_SETUP"] = "1"
    os.environ["NVIM_HIGHLIGHT_SETUP"] = "1"
    nvim = pynvim.attach("child", argv=[env.get("NVIM_BIN", "nvim"), "--embed", "--headless", "-i", "NONE"])

    def wait_for(predicate, message):
        deadline = time.monotonic() + 5
        while not predicate():
            assert time.monotonic() < deadline, message
            time.sleep(0.05)
            nvim.api.get_mode()

    def edit(path):
        nvim.exec_lua("vim.api.nvim_cmd({cmd='edit',args={...},magic={file=false}}, {})", str(path))

    def fresh():
        nvim.input("<Esc>")
        nvim.command("enew!")
        nvim.current.buffer.options["buftype"] = "nofile"
        nvim.current.buffer.options["swapfile"] = False
        nvim.current.buffer.options["autoindent"] = True
        nvim.current.buffer.options["smartindent"] = True

    try:
        nvim.ui_attach(100, 32, rgb=True)
        wait_for(lambda: nvim.exec_lua("return package.loaded['config.paste'] ~= nil"), "Config did not load")
        edit(other)
        hidden = nvim.current.buffer.number
        edit(file)
        buf = nvim.current.buffer.number
        nvim.api.win_set_cursor(0, [2, 3])
        file.write_text("agent changed this\nline two\n")
        wait_for(lambda: nvim.current.buffer[0] == "agent changed this", "External write did not reload")
        assert nvim.api.win_get_cursor(0) == [2, 3]
        assert not nvim.current.buffer.options["modified"]
        print("PASS: external edits reload without focus changes and preserve cursor", flush=True)

        temporary = root / "replacement.txt"
        temporary.write_text("atomic replacement\nline two\n")
        temporary.replace(file)
        wait_for(lambda: nvim.current.buffer[0] == "atomic replacement", "Atomic save did not reload")
        other.write_text("hidden agent edit\n")
        wait_for(lambda: nvim.api.buf_get_lines(hidden, 0, 1, False) == ["hidden agent edit"], "Hidden buffer stale")
        assert nvim.current.buffer.number == buf
        print("PASS: atomic replacements and hidden buffers reload", flush=True)

        nvim.current.buffer[0] = "my unsaved work"
        file.write_text("conflicting agent edit\nline two\n")
        time.sleep(1.1)
        nvim.api.get_mode()
        assert nvim.current.buffer[0] == "my unsaved work"
        assert nvim.current.buffer.options["modified"]
        assert file.read_text().startswith("conflicting agent edit")
        assert not nvim.api.get_mode()["blocking"]
        nvim.command("edit!")
        file.unlink()
        time.sleep(0.7)
        assert nvim.current.buffer[0] == "conflicting agent edit"
        assert not nvim.api.get_mode()["blocking"]
        file.write_text("recreated by agent\nline two\n")
        wait_for(lambda: nvim.current.buffer[0] == "recreated by agent", "Recreated file did not reload")
        print("PASS: local edits and deleted files are preserved without blocking prompts", flush=True)

        nvim.input("i")
        time.sleep(0.1)
        file.write_text("changed while inserting\nline two\n")
        wait_for(lambda: nvim.current.buffer[0] == "changed while inserting", "Insert-mode reload failed")
        assert nvim.api.get_mode()["mode"] == "i"
        print("PASS: unmodified files refresh during insert mode", flush=True)

        fresh()
        nvim.api.paste("\x1b[32mdef demo():\x1b[0m\r\n    return 1\r\n\r\nnext", False, -1)
        expected = ["def demo():", "    return 1", "", "next"]
        assert nvim.current.buffer[:] == expected, nvim.current.buffer[:]
        nvim.command("undo")
        assert nvim.current.buffer[:] == [""]
        nvim.command("redo")
        assert nvim.current.buffer[:] == expected
        nvim.command("undo")
        nvim.command("normal! .")
        assert nvim.current.buffer[:] == expected
        print("PASS: terminal paste cleans CRLF and ANSI codes, preserving code indentation and undo", flush=True)

        fresh()
        for phase, text in ((1, "\x1b[3"), (2, "2mhello\x1b[0m\r"), (3, "\n    world")):
            assert nvim.api.paste(text, False, phase)
        assert nvim.current.buffer[:] == ["hello", "    world"], nvim.current.buffer[:]
        nvim.command("undo")
        assert nvim.current.buffer[:] == [""]
        print("PASS: streamed paste handles split escape sequences and CRLF as one undo", flush=True)

        fresh()
        nvim.api.paste("\x1b]8;;https://example.com\x1b\\link\x1b]8;;\x1b\\\n\n\n    indented", False, -1)
        assert nvim.current.buffer[:] == ["link", "", "", "    indented"]
        nvim.command("normal! gg0v$")
        nvim.api.paste("replacement", False, -1)
        assert nvim.current.buffer[0] == "replacement"
        print("PASS: paste removes terminal hyperlinks and supports visual replacement", flush=True)

        fresh()
        raw = "     first\r\n     \r\n\r\n\r\n\r\n     if ready:\r\n         run()\r\n"
        nvim.funcs.setreg("a", raw)
        nvim.command("PasteAgent a")
        assert nvim.current.buffer[:] == ["first", "", "if ready:", "    run()"], nvim.current.buffer[:]
        nvim.command("undo")
        assert nvim.current.buffer[:] == [""]
        print("PASS: agent paste removes excess blank lines and common padding, preserving relative indentation", flush=True)

        fresh()
        # Isolate tmux completely from the user's running server and copy buffer.
        socket = str(root / "tmux.sock")
        tmux = ["tmux", "-S", socket, "-f", "/dev/null"]
        try:
            subprocess.run(tmux + ["new-session", "-d", "-s", "paste-test"], check=True, env={**env, "TMUX": ""})
            subprocess.run(tmux + ["load-buffer", "-"], input=raw.encode(), check=True)
            nvim.exec_lua("vim.env.TMUX = ...", socket + ",0,0")
            nvim.input("<Space>pa")
            wait_for(lambda: nvim.current.buffer[:] == ["first", "", "if ready:", "    run()"], "tmux paste binding failed")
            print("PASS: Space p a reads and cleans the actual tmux copy buffer", flush=True)
            # Exercise tmux's real bracketed-paste transport into a separate TUI.
            address = root / "nvim.sock"
            subprocess.run(tmux + ["new-window", "-d", "-n", "editor", shlex.join([
                env.get("NVIM_BIN", "nvim"), "-i", "NONE", "--listen", str(address),
            ])], check=True)
            wait_for(address.exists, "tmux Neovim did not start")
            terminal = pynvim.attach("socket", path=str(address))
            try:
                deadline = time.monotonic() + 10
                while not terminal.exec_lua("return package.loaded['config.paste'] ~= nil"):
                    assert time.monotonic() < deadline, "tmux Neovim config did not load"
                    time.sleep(0.05)
                terminal.command("enew")
                terminal.command("setlocal autoindent smartindent")
                terminal.input("i")
                subprocess.run(tmux + ["load-buffer", "-"], input=b"\x1b[32mdef demo():\x1b[0m\n    return 1\n\nnext", check=True)
                subprocess.run(tmux + ["paste-buffer", "-p", "-t", "paste-test:editor"], check=True)
                wait_for(lambda: terminal.current.buffer[:] == expected, "tmux bracketed paste changed indentation or line breaks")
                print("PASS: actual tmux bracketed paste into Neovim cleans formatting without autoindent artifacts", flush=True)
            finally:
                terminal.close()
        finally:
            subprocess.run(tmux + ["kill-server"], check=False, capture_output=True)
    finally:
        try:
            nvim.input("<Esc><Esc>")
            nvim.command("qa!")
        except (EOFError, OSError):
            pass
        nvim.close()


if __name__ == "__main__":
    def timeout(signum, frame):
        raise TimeoutError("Editor integration checks exceeded 60 seconds")

    signal.signal(signal.SIGALRM, timeout)
    signal.alarm(60)
    with tempfile.TemporaryDirectory(prefix="pimp-editor-") as directory:
        check_editor(Path(directory))
