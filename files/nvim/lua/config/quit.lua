local M = {}

local function other_buffers(buf)
  return vim.tbl_filter(function(candidate)
    return candidate ~= buf and vim.bo[candidate].buflisted
  end, vim.api.nvim_list_bufs())
end

function M.close(force)
  local buf = vim.api.nvim_get_current_buf()
  if vim.bo[buf].buftype ~= "" then
    vim.cmd({ cmd = "quit", bang = force })
    return
  end
  local editors = vim.tbl_filter(function(win)
    return vim.api.nvim_win_get_config(win).relative == "" and vim.bo[vim.api.nvim_win_get_buf(win)].buftype == ""
  end, vim.api.nvim_list_wins())
  local others = other_buffers(buf)
  if #editors == 1 and #others > 0 then
    -- In the last pane, close one file and select another from that pane.
    require("config.panes").close(buf, nil, force)
    return
  end
  local win = vim.api.nvim_get_current_win()
  -- Let native :quit perform its unsaved-change checks and close this pane.
  vim.cmd({ cmd = "quit", bang = force })
  if
    not vim.api.nvim_win_is_valid(win)
    and vim.api.nvim_buf_is_valid(buf)
    and #vim.fn.win_findbuf(buf) == 0
    and not require("config.panes").owned(buf, win)
    and (force or not vim.bo[buf].modified)
  then
    vim.api.nvim_buf_delete(buf, { force = force })
  end
end

function M.setup()
  vim.api.nvim_create_user_command("PimpMyShellQuit", function(opts)
    M.close(opts.bang)
  end, { bang = true, desc = "Close this pane or file, keeping other open files" })
  vim.api.nvim_create_user_command("PimpMyShellWriteQuit", function(opts)
    vim.cmd({ cmd = "write", bang = opts.bang })
    M.close(opts.bang)
  end, { bang = true, desc = "Save and close this pane or file" })
  for key, command in pairs({ q = "PimpMyShellQuit", quit = "PimpMyShellQuit", wq = "PimpMyShellWriteQuit" }) do
    vim.keymap.set("ca", key, function()
      -- Expand only the whole command, never a search, filename, or :normal q.
      return vim.fn.getcmdtype() == ":" and vim.fn.getcmdline() == key and command or key
    end, { expr = true })
  end
end

return M
