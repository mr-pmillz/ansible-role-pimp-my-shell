require("config.filetypes")
require("config.gotmpl")

-- These legacy remote-plugin hosts are not used by the bundled Lua plugins.
-- Remove a line when adding a plugin that requires that provider.
vim.g.loaded_node_provider = 0
vim.g.loaded_perl_provider = 0
vim.g.loaded_ruby_provider = 0

-- Keep the Python host separate from distro packages and project virtualenvs.
local python_host = vim.fn.stdpath("data") .. "/python/bin/python"
if vim.fn.executable(python_host) == 1 and not vim.g.python3_host_prog then
  vim.g.python3_host_prog = python_host
end

-- vim.opt.mouse = "" -- disable mouse

-- ENABLE PER-PROJECT RC/SCRIPTS
vim.opt.exrc = true -- allow per-project rc files (.nvim.lua)
vim.opt.secure = true -- require that per-project rc files are trusted (see :h trust)

-- CLIPBOARD BEHAVIOR
-- vim.opt.clipboard = "unnamedplus" -- enable clipboard nonsense
vim.opt.clipboard = "" -- disable clipboard nonsense
vim.opt.completeopt = "menu,menuone,noselect,preview"
