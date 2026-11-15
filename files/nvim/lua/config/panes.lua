-- File tabs belong to windows; Neovim's tab pages still hold whole layouts.
local M = {}
local groups = {}
local scheduled = false
local bar = "%!v:lua.require'config.panes'.render()"

local function file(buf)
  return vim.api.nvim_buf_is_valid(buf) and vim.bo[buf].buflisted and vim.bo[buf].buftype == ""
end

local function placeholder(buf)
  return vim.api.nvim_buf_get_name(buf) == ""
    and not vim.bo[buf].modified
    and (
      not vim.api.nvim_buf_is_loaded(buf)
      or (vim.api.nvim_buf_line_count(buf) == 1 and vim.api.nvim_buf_get_lines(buf, 0, 1, false)[1] == "")
    )
end

function M.is_editor(win)
  return vim.api.nvim_win_is_valid(win)
    and vim.api.nvim_win_get_config(win).relative == ""
    and file(vim.api.nvim_win_get_buf(win))
end

local function add(group, buf)
  if file(buf) and not vim.tbl_contains(group.buffers, buf) then
    group.buffers[#group.buffers + 1] = buf
  end
end

local function record(win)
  local buf = vim.api.nvim_win_get_buf(win)
  local group = groups[win] or { buffers = {} }
  groups[win] = group
  group.buffers = vim.tbl_filter(function(b)
    return file(b) and (b == buf or not placeholder(b))
  end, group.buffers)
  add(group, buf)
  if group.current ~= buf then
    group.previous, group.current = group.current, buf
    group.start = nil
  end
  return group
end

function M.buffers(win)
  win = win or vim.api.nvim_get_current_win()
  return M.is_editor(win) and vim.deepcopy(record(win).buffers) or {}
end

function M.owned(buf, except)
  -- A new split may display the buffer before its deferred group is recorded.
  for _, win in ipairs(vim.fn.win_findbuf(buf)) do
    if win ~= except and M.is_editor(win) then
      return true
    end
  end
  for win, group in pairs(groups) do
    if win ~= except and vim.api.nvim_win_is_valid(win) and vim.tbl_contains(group.buffers, buf) then
      return true
    end
  end
  return false
end

function M.refresh()
  for _, win in ipairs(vim.api.nvim_list_wins()) do
    if M.is_editor(win) then
      record(win)
      vim.wo[win].winbar = bar
    elseif vim.wo[win].winbar == bar then
      vim.wo[win].winbar = ""
    end
  end
  vim.cmd("redrawstatus")
end

local function queue()
  if scheduled then
    return
  end
  scheduled = true
  vim.schedule(function()
    scheduled = false
    M.refresh()
  end)
end

function M.merge(destination, source)
  local from = groups[source]
  if from and M.is_editor(destination) then
    local into = record(destination)
    for _, buf in ipairs(from.buffers) do
      add(into, buf)
    end
    groups[source] = nil
    queue()
  end
end

function M.select(win, buf)
  if M.is_editor(win) and file(buf) then
    vim.api.nvim_set_current_win(win)
    -- :hide retains edits when switching tabs, even with 'nohidden'.
    vim.api.nvim_cmd({ cmd = "buffer", args = { tostring(buf) }, mods = { hide = true } }, {})
    record(win)
    queue()
  end
end

function M.cycle(direction)
  local win = vim.api.nvim_get_current_win()
  local buffers = M.buffers(win)
  for i, buf in ipairs(buffers) do
    if buf == vim.api.nvim_get_current_buf() then
      M.select(win, buffers[(i - 1 + direction * vim.v.count1) % #buffers + 1])
      return
    end
  end
end

function M.previous()
  local win = vim.api.nvim_get_current_win()
  local group = M.is_editor(win) and record(win)
  if group and vim.tbl_contains(group.buffers, group.previous) then
    M.select(win, group.previous)
  end
end

function M.pick()
  local win = vim.api.nvim_get_current_win()
  vim.ui.select(M.buffers(win), {
    prompt = "Files in this pane",
    format_item = function(buf)
      local name = vim.api.nvim_buf_get_name(buf)
      return name == "" and "[No Name]" or vim.fn.fnamemodify(name, ":~:.")
    end,
  }, function(buf)
    if buf then
      M.select(win, buf)
    end
  end)
end

function M.reorder(direction)
  local win = vim.api.nvim_get_current_win()
  local group = M.is_editor(win) and record(win)
  if not group then
    return
  end
  for i, buf in ipairs(group.buffers) do
    if buf == group.current then
      local next_index = math.max(1, math.min(#group.buffers, i + direction))
      table.remove(group.buffers, i)
      table.insert(group.buffers, next_index, buf)
      queue()
      return
    end
  end
end

local function remove(win, buf)
  local group = groups[win]
  if group then
    group.buffers = vim.tbl_filter(function(b)
      return b ~= buf and file(b)
    end, group.buffers)
  end
end

function M.transfer(source, destination, buf)
  if source == destination or not M.is_editor(source) or not M.is_editor(destination) then
    return
  end
  local remaining = vim.tbl_filter(function(b)
    return b ~= buf
  end, M.buffers(source))
  if vim.api.nvim_win_get_buf(source) == buf then
    if #remaining == 0 then
      -- The destination already displays the file, including any unsaved edits.
      vim.api.nvim_win_call(source, function()
        vim.cmd("hide close")
      end)
      groups[source] = nil
    else
      vim.api.nvim_win_set_buf(source, remaining[1])
    end
  end
  remove(source, buf)
  record(destination)
  vim.api.nvim_set_current_win(destination)
  queue()
end

local function confirm_close(buf, force)
  if not vim.bo[buf].modified or force then
    return true
  end
  local name = vim.fn.bufname(buf)
  local choice =
    vim.fn.confirm("Save changes to " .. (name ~= "" and name or "[No Name]") .. "?", "&Save\n&Discard\n&Cancel", 3)
  if choice == 1 then
    local ok, err = pcall(vim.api.nvim_buf_call, buf, function()
      vim.cmd({ cmd = "write", mods = { silent = true } })
    end)
    if not ok then
      vim.notify(tostring(err), vim.log.levels.ERROR)
    end
    return ok
  end
  return choice == 2
end

function M.close(buf, win, force)
  win = win or vim.api.nvim_get_current_win()
  local members = M.buffers(win)
  if not vim.tbl_contains(members, buf) then
    return
  end
  local remaining = vim.tbl_filter(function(b)
    return b ~= buf
  end, members)
  local others = vim.tbl_filter(function(b)
    return b ~= buf and file(b) and (not placeholder(b) or #vim.fn.win_findbuf(b) > 0)
  end, vim.api.nvim_list_bufs())
  if #others == 0 and not M.owned(buf, win) then
    vim.cmd("confirm qall")
    return
  end
  -- Closing one view of a shared buffer never deletes that buffer's edits.
  local shared = M.owned(buf, win)
  if not shared and not confirm_close(buf, force) then
    return
  end
  if #remaining == 0 then
    local editors = vim.tbl_filter(M.is_editor, vim.api.nvim_list_wins())
    if #editors > 1 then
      vim.api.nvim_win_call(win, function()
        vim.cmd("hide close")
      end)
      groups[win] = nil
    else
      -- Recover files kept hidden by native commands or a restored session.
      for _, other in ipairs(others) do
        add(groups[win], other)
      end
      M.select(win, others[1])
    end
  elseif vim.api.nvim_win_get_buf(win) == buf then
    M.select(win, remaining[1])
  end
  remove(win, buf)
  if not shared and #vim.fn.win_findbuf(buf) == 0 then
    vim.api.nvim_buf_delete(buf, { force = true })
  end
  queue()
end

function M.click(buf, _, button)
  local win = vim.fn.getmousepos().winid
  if button == "l" then
    require("config.mouse").buffer_click(buf, win)
  elseif button == "r" then
    require("config.mouse").open_buffer_menu(buf, win)
  elseif button == "m" then
    vim.schedule(function()
      M.close(buf, win)
    end)
  end
end

function M.close_others(side)
  local win = vim.api.nvim_get_current_win()
  local members = M.buffers(win)
  local current = vim.api.nvim_get_current_buf()
  local index = 1
  for i, buf in ipairs(members) do
    if buf == current then
      index = i
    end
  end
  for i, buf in ipairs(members) do
    if buf ~= current and (not side or (side == "left" and i < index) or (side == "right" and i > index)) then
      M.close(buf, win)
      if vim.tbl_contains(M.buffers(win), buf) then
        return -- A cancelled save prompt stops the operation.
      end
    end
  end
end

function M.close_click(buf, _, button)
  if button == "l" or button == "m" then
    local win = vim.fn.getmousepos().winid
    vim.schedule(function()
      M.close(buf, win)
    end)
  end
end

function M.scroll(direction)
  local win = vim.fn.getmousepos().winid
  if M.is_editor(win) then
    local group = record(win)
    group.start =
      math.max(1, math.min(#group.buffers, (group.start or group.render_start or 1) + (direction == 1 and -1 or 1)))
    vim.schedule(function()
      vim.cmd("redrawstatus")
    end)
  end
end

local function fit(text, width)
  if vim.fn.strdisplaywidth(text) <= width then
    return text
  end
  while vim.fn.strdisplaywidth(text) > math.max(0, width - 1) do
    text = vim.fn.strcharpart(text, 1)
  end
  return "…" .. text
end

local function escape(text)
  return text:gsub("[\r\n\t]", " "):gsub("%%", "%%%%")
end

function M.render()
  local win = tonumber(vim.g.statusline_winid) or vim.api.nvim_get_current_win()
  local group = groups[win]
  if not group or not M.is_editor(win) then
    return ""
  end
  local buffers = vim.tbl_filter(file, group.buffers)
  local current = vim.api.nvim_win_get_buf(win)
  local width = math.max(1, vim.api.nvim_win_get_width(win) - 7)
  local labels, sizes, active = {}, {}, 1
  local basenames = {}
  for _, buf in ipairs(buffers) do
    local name = vim.fn.fnamemodify(vim.api.nvim_buf_get_name(buf), ":t")
    basenames[name] = (basenames[name] or 0) + 1
  end
  for i, buf in ipairs(buffers) do
    local path = vim.api.nvim_buf_get_name(buf)
    local name = path == "" and "[No Name]" or vim.fn.fnamemodify(path, ":t")
    if basenames[name] and basenames[name] > 1 and path ~= "" then
      name = vim.fn.fnamemodify(path, ":h:t") .. "/" .. name
    end
    local modified = vim.bo[buf].modified and " ●" or ""
    labels[i] = fit(name, math.max(1, math.min(30, width - 5 - vim.fn.strdisplaywidth(modified)))) .. modified
    sizes[i] = vim.fn.strdisplaywidth(labels[i]) + 5
    if buf == current then
      active = i
    end
  end
  local start = math.max(1, math.min(#buffers, group.start or 1))
  if not group.start then
    local used = 0
    for i = 1, active do
      used = used + sizes[i]
      while used > width and start < i do
        used = used - sizes[start]
        start = start + 1
      end
    end
  end
  group.render_start = start
  local result = { "%#WinBarNC#%@v:lua.require'config.mouse'.pane_click@ ⠿ %T" }
  if start > 1 then
    result[#result + 1] = "%1@v:lua.require'config.panes'.scroll@‹ %T"
  end
  local used, last = 0, start - 1
  for i = start, #buffers do
    if i > start and used + sizes[i] > width then
      break
    end
    local buf = buffers[i]
    local hl = buf == current and "TabLineSel" or "TabLine"
    result[#result + 1] = ("%%#%s#%%%d@v:lua.require'config.panes'.click@ %s %%T"):format(hl, buf, escape(labels[i]))
    result[#result + 1] = ("%%#DiagnosticError#%%%d@v:lua.require'config.panes'.close_click@×%%T%%#%s# %%#WinBarNC# "):format(
      buf,
      hl
    )
    used, last = used + sizes[i], i
  end
  if last < #buffers then
    result[#result + 1] = "%2@v:lua.require'config.panes'.scroll@› %T"
  end
  result[#result + 1] = "%#WinBarNC#%="
  return table.concat(result)
end

function M.setup()
  -- Use the native top row only for actual Neovim tab pages (whole layouts).
  vim.opt.showtabline = 1
  vim.opt.tabline = ""
  local group = vim.api.nvim_create_augroup("pimp_my_shell_panes", { clear = true })
  vim.api.nvim_create_autocmd({
    "BufEnter",
    "BufWinEnter",
    "WinEnter",
    "WinNew",
    "BufDelete",
    "BufFilePost",
    -- Some development builds lack BufModifiedSet; these also refresh the dirty marker.
    "BufWritePost",
    "TextChanged",
    "TextChangedI",
    "FileType",
    "VimResized",
    "WinResized",
    "SessionLoadPost",
  }, {
    group = group,
    callback = function()
      local win = vim.api.nvim_get_current_win()
      if groups[win] and M.is_editor(win) then
        record(win)
      end
      -- New splits are recorded after :split file finishes, excluding the transient old buffer.
      queue()
    end,
  })
  vim.api.nvim_create_autocmd("WinClosed", {
    group = group,
    callback = function(event)
      local closed = tonumber(event.match)
      vim.schedule(function()
        if groups[closed] then
          local destination = vim.api.nvim_get_current_win()
          if not M.is_editor(destination) then
            destination = vim.tbl_filter(M.is_editor, vim.api.nvim_list_wins())[1]
          end
          if destination then
            M.merge(destination, closed)
          else
            groups[closed] = nil
          end
        end
      end)
    end,
  })
  M.refresh()
  for _, binding in ipairs({ { "<S-h>", -1 }, { "[b", -1 }, { "<S-l>", 1 }, { "]b", 1 } }) do
    vim.keymap.set("n", binding[1], function()
      M.cycle(binding[2])
    end, { desc = binding[2] == -1 and "Previous file in pane" or "Next file in pane" })
  end
  vim.keymap.set("n", "<leader>bb", M.previous, { desc = "Previous active file in pane" })
  vim.keymap.set("n", "<leader>`", M.previous, { desc = "Previous active file in pane" })
  vim.keymap.set("n", "<C-^>", M.previous, { desc = "Previous active file in pane" })
  vim.keymap.set("n", "<C-6>", M.previous, { desc = "Previous active file in pane" })
  vim.keymap.set("n", "<leader>bj", M.pick, { desc = "Pick file in pane" })
  vim.keymap.set("n", "<leader>bd", function()
    M.close(vim.api.nvim_get_current_buf())
  end, { desc = "Close file in pane" })
  vim.keymap.set("n", "<leader>bo", function()
    M.close_others()
  end, { desc = "Close other files in pane" })
  vim.keymap.set("n", "<leader>bl", function()
    M.close_others("left")
  end, { desc = "Close file tabs to the left" })
  vim.keymap.set("n", "<leader>br", function()
    M.close_others("right")
  end, { desc = "Close file tabs to the right" })
  vim.keymap.set("n", "[B", function()
    M.reorder(-1)
  end, { desc = "Move file tab left" })
  vim.keymap.set("n", "]B", function()
    M.reorder(1)
  end, { desc = "Move file tab right" })
end

return M
