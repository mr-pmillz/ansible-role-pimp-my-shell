-- Run with the installed Neovim config: nvim --headless -i NONE -l is not
-- suitable because -l skips init.lua. Use -c 'luafile tests/pickers.lua'.
vim.defer_fn(function()
  local fixture = vim.fn.tempname()
  vim.fn.mkdir(fixture, "p")
  vim.fn.writefile({ "pms_unique_content" }, fixture .. "/pms_unique_file.txt")
  local ok, err = xpcall(function()
    local fzf = require("fzf-lua")
    local failures = {}
    local report_error = fzf.utils.error
    fzf.utils.error = function(...)
      failures[#failures + 1] = vim.inspect({ ... })
      report_error(...)
    end
    for _, case in ipairs({
      { picker = "files", expected = "pms_unique_file.txt" },
      { picker = "live_grep", search = "pms_unique_content", expected = "pms_unique_content" },
    }) do
      local selected
      fzf[case.picker]({
        cwd = fixture,
        search = case.search,
        -- Optional override for reproducing old distro binaries in isolation.
        fzf_bin = vim.env.FZF_TEST_BIN,
        -- Accept once the real file/grep backend returns the single fixture.
        keymap = { fzf = { one = "accept" } },
        actions = { enter = function(items) selected = items end },
      })
      assert(vim.wait(15000, function() return selected ~= nil or #failures > 0 end, 20),
        case.picker .. ": timed out waiting for search results")
      assert(#failures == 0, table.concat(failures, "\n"))
      assert(selected and #selected == 1 and selected[1]:find(case.expected, 1, true),
        case.picker .. ": unexpected result " .. vim.inspect(selected))
      print("PASS: " .. case.picker .. " returns the expected result")
    end
    for _, mapping in ipairs({ "  ", " /" }) do
      assert(not vim.tbl_isempty(vim.fn.maparg(mapping, "n", false, true)),
        "Missing search mapping: " .. vim.inspect(mapping))
    end
  end, debug.traceback)
  vim.fn.delete(fixture, "rf")
  if not ok then
    vim.api.nvim_err_writeln(err)
    vim.cmd("cquit 1")
  else
    vim.cmd("qa!")
  end
end, 100)
