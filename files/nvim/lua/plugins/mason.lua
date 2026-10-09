local plugin = {
  "mason-org/mason.nvim",
  opts = {
    PATH = "append",
  },
}

-- Parser setup must not start unrelated background package installations that
-- would be killed when headless Neovim exits. Interactive Mason keeps LazyVim's
-- normal registry refresh, language-server, formatter, and debugger behavior.
if vim.env.NVIM_HIGHLIGHT_SETUP == "1" then
  plugin.build = false
  plugin.config = function(_, opts)
    require("mason").setup(opts)
  end
end

return { plugin }
