local M = {}
local installed = false

local function clean(text, agent)
  -- OSC hyperlinks/titles and ANSI CSI formatting can survive terminal copies.
  text = text:gsub("\27%][^\7\27]*\7", ""):gsub("\27%][^\7\27]*\27\\", "")
  text = text:gsub("\27%[[0-?]*[ -/]*[@-~]", "")
  text = text:gsub("\r+\n", "\n"):gsub("\r+", "\n")
  if not agent then
    return text
  end
  -- Explicit agent paste removes terminal margins, retaining relative indentation.
  local lines = vim.split(text, "\n", { plain = true })
  local margin
  for _, line in ipairs(lines) do
    if line:find("%S") then
      local spaces = #line:match("^ *")
      margin = math.min(margin or spaces, spaces)
    end
  end
  local result = {}
  for _, line in ipairs(lines) do
    if line:find("%S") then
      result[#result + 1] = line:sub((margin or 0) + 1)
    elseif #result > 0 and result[#result] ~= "" then
      result[#result + 1] = ""
    end
  end
  if result[#result] == "" then
    table.remove(result)
  end
  return table.concat(result, "\n")
end

function M.agent(register)
  local text
  if register == "tmux" or ((not register or register == "") and vim.env.TMUX) then
    -- Read just the user's copied text, never scrape a terminal pane.
    local result = vim.system({ "tmux", "save-buffer", "-" }, { text = false }):wait()
    if result.code ~= 0 then
      vim.notify(result.stderr or "No tmux copy buffer", vim.log.levels.WARN)
      return
    end
    text = result.stdout
  else
    text = vim.fn.getreg(register and register ~= "" and register or "+")
  end
  if text and text ~= "" then
    -- crlf=false lets cleanup normalize repeated CRs before Neovim splits lines.
    vim.api.nvim_paste(clean(text, true), false, -1)
  end
end

function M.setup()
  if installed then
    return
  end
  installed = true
  local original = vim.paste
  local chunks, bypass
  vim.paste = function(lines, phase)
    if phase == -1 or phase == 1 then
      chunks = {}
      -- Embedded terminals and command lines must retain their native input semantics.
      bypass = vim.bo.buftype == "terminal" or vim.fn.getcmdtype() ~= "" or vim.g.pimp_my_shell_clean_paste == false
    end
    if bypass then
      return original(lines, phase)
    end
    chunks = chunks or {}
    chunks[#chunks + 1] = table.concat(lines, "\n")
    if phase ~= -1 and phase ~= 3 then
      return true
    end
    -- Buffer the paste so CRLF and escape codes split across chunks stay intact.
    local text = clean(table.concat(chunks), false)
    chunks = nil
    return original(vim.split(text, "\n", { plain = true }), -1)
  end
  vim.api.nvim_create_user_command("PasteAgent", function(opts)
    M.agent(opts.args)
  end, { nargs = "?", desc = "Paste cleaned agent output from tmux (or a Vim register)" })
  vim.keymap.set({ "n", "x" }, "<leader>pa", function()
    M.agent()
  end, { desc = "Paste agent output (tmux/clipboard)" })
end

return M
