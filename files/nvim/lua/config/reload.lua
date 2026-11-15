-- Polling detects agent edits (including atomic replacements) while tmux has focus elsewhere.
local M = {}
local timer

function M.setup()
  vim.opt.autoread = true
  if timer then
    timer:stop()
    timer:close()
  end
  local group = vim.api.nvim_create_augroup("pimp_my_shell_reload", { clear = true })
  vim.api.nvim_create_autocmd("FileChangedShell", {
    group = group,
    callback = function(event)
      -- Never interrupt typing with a modal prompt or discard local changes.
      vim.v.fcs_choice = ""
      if vim.v.fcs_reason == "deleted" or vim.bo[event.buf].modified then
        local reason = vim.v.fcs_reason == "deleted" and "Deleted on disk" or "Changed on disk; local edits kept"
        vim.schedule(function()
          vim.notify(reason .. ": " .. event.file, vim.log.levels.WARN, { title = "File changed externally" })
        end)
      elseif vim.bo[event.buf].autoread then
        vim.v.fcs_choice = "reload"
      end
    end,
  })
  local pending = false
  local function check()
    local mode = vim.api.nvim_get_mode()
    if not mode.blocking and not mode.mode:match("^[crt!]") and vim.fn.getcmdwintype() == "" then
      -- Explicit buffer IDs include files hidden behind other Bufferline tabs.
      for _, buf in ipairs(vim.api.nvim_list_bufs()) do
        if vim.api.nvim_buf_is_loaded(buf) and vim.bo[buf].buftype == "" and vim.api.nvim_buf_get_name(buf) ~= "" then
          vim.cmd("silent! checktime " .. buf)
        end
      end
    end
  end
  timer = assert(vim.uv.new_timer())
  timer:start(500, 500, function()
    if pending then
      return
    end
    pending = true
    vim.schedule(function()
      pending = false
      if timer then
        check()
      end
    end)
  end)
  vim.api.nvim_create_autocmd({ "FocusGained", "BufEnter", "TermLeave" }, {
    group = group,
    callback = check,
  })
  vim.api.nvim_create_autocmd("VimLeavePre", {
    group = group,
    callback = function()
      timer:stop()
      timer:close()
      timer = nil
    end,
  })
end

return M
