-- Run with the installed configuration, after the Neovim prerequisites.
vim.defer_fn(function()
  local ok, err = pcall(function()
    local python = assert(vim.g.python3_host_prog, "isolated Python provider was not selected")
    assert(python == vim.fn.stdpath("data") .. "/python/bin/python", "wrong Python host")
    vim.fn.system({ python, "-c", "import pynvim" })
    assert(vim.v.shell_error == 0, "isolated Python cannot import pynvim")
    assert(vim.fn.py3eval("1 + 1") == 2, "Python RPC provider failed")

    assert(not Snacks.config.picker.enabled, "SQLite configuration unexpectedly enabled a competing picker")

    -- Exercise the database consumer, including its configured library lookup.
    local database = require("snacks.picker.util.db").new(":memory:", "string")
    database:set("pimp-my-shell", "working")
    assert(database:get("pimp-my-shell") == "working", "SQLite read/write failed")
    database.insert:close()
    database.select:close()
    database:close()
    print("Passed isolated Python RPC provider and SQLite read/write checks")
  end)
  if not ok then
    vim.api.nvim_err_writeln(tostring(err))
    vim.cmd("cquit 1")
  else
    vim.cmd("qa!")
  end
end, 200)
