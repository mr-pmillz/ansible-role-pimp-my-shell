-- Neo-tree-to-editor drags use terminal mouse events, including in Kitty.
-- No file is moved on disk: dropping only opens a buffer or creates a split.
local M = {}
local drag, menu
local preview

local function popup(name)
  -- Keep menu labels readable over editor text, and anchor them at the click.
  local blend = vim.o.pumblend
  vim.o.pumblend = 0
  local ok, err = pcall(vim.cmd, "popup! " .. name)
  vim.o.pumblend = blend
  if not ok then
    error(err)
  end
end

local function clear_preview()
  if preview and vim.api.nvim_win_is_valid(preview.win) then
    vim.api.nvim_win_close(preview.win, true)
  end
  preview = nil
end

local function is_tree(win)
  return vim.api.nvim_win_is_valid(win) and vim.bo[vim.api.nvim_win_get_buf(win)].filetype == "neo-tree"
end

local function is_editor(win)
  return vim.api.nvim_win_is_valid(win)
    and vim.api.nvim_win_get_config(win).relative == ""
    and vim.bo[vim.api.nvim_win_get_buf(win)].buftype == ""
end

local function editor_window()
  local prior = require("neo-tree").get_prior_window()
  if prior and is_editor(prior) then
    return prior
  end
  for _, win in ipairs(vim.api.nvim_tabpage_list_wins(0)) do
    if is_editor(win) then
      return win
    end
  end
end

local actions = {
  current = { cmd = "edit" },
  left = { cmd = "vsplit", mods = { split = "aboveleft" } },
  right = { cmd = "vsplit", mods = { split = "belowright" } },
  above = { cmd = "split", mods = { split = "aboveleft" } },
  below = { cmd = "split", mods = { split = "belowright" } },
  tab = { cmd = "tabedit" },
}

local function open_item(item, win, action)
  local ok, err = pcall(function()
    if win and is_editor(win) then
      vim.api.nvim_set_current_win(win)
    elseif action ~= "tab" then
      -- Preserve the sidebar when it is the only window left.
      vim.cmd("belowright vnew")
      action = "current"
    end
    local command = vim.deepcopy(assert(actions[action]))
    if item.buf then
      if action == "current" then
        command = { cmd = "buffer" }
      elseif action == "tab" then
        command = { cmd = "sbuffer", mods = { tab = 0 } }
      else
        command.mods.vertical = command.cmd == "vsplit"
        command.cmd = "sbuffer"
      end
      command.args = { tostring(item.buf) }
    else
      command.args = { item.file }
    end
    command.magic = { file = false }
    vim.api.nvim_cmd(command, {})
  end)
  if not ok then
    vim.notify(tostring(err), vim.log.levels.WARN, { title = "Open file" })
  end
end

function M.capture()
  clear_preview()
  drag = nil
  local pos = vim.fn.getmousepos()
  if not is_tree(pos.winid) or pos.line == 0 then
    return
  end
  local state = require("neo-tree.sources.manager").get_state_for_window(pos.winid)
  local node = state and state.tree and state.tree:get_node(pos.line)
  if node and node.type == "file" then
    drag = { file = node.path or node:get_id(), moved = false }
  end
end

local function drop_target()
  local pos = vim.fn.getmousepos()
  if not is_editor(pos.winid) then
    return
  end
  local width = vim.api.nvim_win_get_width(pos.winid)
  local height = vim.api.nvim_win_get_height(pos.winid)
  local winbar = vim.wo[pos.winid].winbar ~= "" and 1 or 0
  local row = pos.winrow - winbar
  -- Ignore statuslines, separators, popups, and drops back into the sidebar.
  if row < 1 or row > height or pos.wincol < 1 or pos.wincol > width then
    return
  end
  local action = "current"
  if pos.wincol <= 3 then
    action = "left"
  elseif pos.wincol > width - 3 then
    action = "right"
  elseif row <= 2 then
    action = "above"
  elseif row > height - 2 then
    action = "below"
  end
  return { win = pos.winid, action = action, width = width, height = height, winbar = winbar }
end

function M.update_drag()
  if not drag then
    return
  end
  drag.moved = true
  local target = drop_target()
  if not target then
    clear_preview()
    return
  end
  local key = table.concat({ target.win, target.action, target.width, target.height }, ":")
  if preview and preview.key == key and vim.api.nvim_win_is_valid(preview.win) then
    return
  end
  clear_preview()
  local row, col, width, height = target.winbar, 0, target.width, target.height
  local labels = {
    current = "Open in this pane",
    left = "Vertical split: left",
    right = "Vertical split: right",
    above = "Horizontal split: above",
    below = "Horizontal split: below",
  }
  if target.action == "left" or target.action == "right" then
    width = math.max(1, math.floor(width / 2))
    if target.action == "right" then
      col = target.width - width
    end
  elseif target.action == "above" or target.action == "below" then
    height = math.max(1, math.floor(height / 2))
    if target.action == "below" then
      row = row + target.height - height
    end
  end
  local label = labels[target.action]:sub(1, width)
  local lines = {}
  for i = 1, height do
    lines[i] = ""
  end
  lines[math.ceil(height / 2)] = string.rep(" ", math.floor((width - #label) / 2)) .. label
  local buf = vim.api.nvim_create_buf(false, true)
  vim.bo[buf].bufhidden = "wipe"
  vim.bo[buf].filetype = "pimp-drop-preview"
  vim.api.nvim_buf_set_lines(buf, 0, -1, false, lines)
  local win = vim.api.nvim_open_win(buf, false, {
    relative = "win",
    win = target.win,
    row = row,
    col = col,
    width = width,
    height = height,
    style = "minimal",
    focusable = false,
    mouse = false,
    noautocmd = true,
    zindex = 60,
  })
  vim.wo[win].winblend = 35
  vim.wo[win].winhighlight = "Normal:PimpMyShellDrop,NormalNC:PimpMyShellDrop,EndOfBuffer:PimpMyShellDrop"
  preview = { win = win, key = key }
end

function M.drop()
  local item = drag
  drag = nil
  local target = item and item.moved and drop_target()
  clear_preview()
  if target then
    open_item(item, target.win, target.action)
  end
end

function M.open_menu()
  M.capture()
  menu, drag = drag, nil
  if not menu then
    return
  end
  menu.target = editor_window()
  popup("PimpMyShellOpen")
end

function M.open_buffer_menu(buf)
  if not vim.api.nvim_buf_is_valid(buf) then
    return
  end
  clear_preview()
  drag = nil
  local win = vim.api.nvim_get_current_win()
  menu = { buf = buf, target = is_editor(win) and win or editor_window() }
  -- Bufferline invokes this from a tabline click callback. Defer the popup
  -- until that callback finishes, keeping the clicked buffer as its target.
  vim.schedule(function()
    popup("PimpMyShellBuffer")
  end)
end

function M.menu_action(action)
  local item = menu
  menu = nil
  if item then
    open_item(item, item.target, action)
  end
end

function M.setup()
  vim.api.nvim_set_hl(0, "PimpMyShellDrop", { link = "Visual", default = true })
  -- Pass ordinary editing, selection, tab clicks, and resizing to Neovim.
  -- Expression mappings defer window changes until after the native click.
  vim.keymap.set({ "n", "i", "x" }, "<LeftMouse>", function()
    drag = nil
    -- Clear a preview left behind when a release happened outside the terminal.
    vim.schedule(clear_preview)
    if is_tree(vim.fn.getmousepos().winid) then
      local escape = vim.fn.mode() == "n" and "" or "<Esc>"
      return escape .. "<LeftMouse><Cmd>lua require('config.mouse').capture()<CR>"
    end
    return "<LeftMouse>"
  end, { expr = true, desc = "Select file or start explorer drag" })
  vim.keymap.set("n", "<LeftDrag>", function()
    if drag then
      return "<Cmd>lua require('config.mouse').update_drag()<CR>"
    end
    return "<LeftDrag>"
  end, { expr = true, desc = "Drag explorer file to a pane" })
  vim.keymap.set("n", "<LeftRelease>", function()
    if drag then
      return "<Cmd>lua require('config.mouse').drop()<CR>"
    end
    return "<LeftRelease>"
  end, { expr = true, desc = "Open file at drop position" })
  vim.keymap.set({ "n", "i", "x" }, "<RightMouse>", function()
    drag = nil
    local pos = vim.fn.getmousepos()
    local escape = vim.fn.mode() == "n" and "" or "<Esc>"
    if is_tree(pos.winid) then
      return escape .. "<LeftMouse><Cmd>lua require('config.mouse').open_menu()<CR>"
    end
    return "<RightMouse>"
  end, { expr = true, desc = "File open menu" })
  for _, entry in ipairs({
    { "Current\\ pane", "current" },
    { "Split\\ left", "left" },
    { "Split\\ right", "right" },
    { "Split\\ above", "above" },
    { "Split\\ below", "below" },
    { "New\\ tab", "tab" },
  }) do
    vim.cmd(
      ("nnoremenu PimpMyShellOpen.%s <Cmd>lua require('config.mouse').menu_action('%s')<CR>"):format(entry[1], entry[2])
    )
  end
  for _, entry in ipairs({
    { "Current\\ pane", "current" },
    { "Vertical\\ split", "right" },
    { "Horizontal\\ split", "below" },
    { "New\\ tab", "tab" },
  }) do
    vim.cmd(
      ("anoremenu PimpMyShellBuffer.%s <Cmd>lua require('config.mouse').menu_action('%s')<CR>"):format(
        entry[1],
        entry[2]
      )
    )
  end
  vim.api.nvim_create_autocmd({ "TabLeave", "FocusLost", "InsertEnter" }, {
    group = vim.api.nvim_create_augroup("pimp_my_shell_mouse", { clear = true }),
    callback = function()
      drag, menu = nil, nil
      clear_preview()
    end,
  })
end

return M
