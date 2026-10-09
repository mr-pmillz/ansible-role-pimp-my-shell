return {
  {
    "nvim-treesitter/nvim-treesitter",
    init = function()
      require("config.treesitter").setup()
    end,
    -- highlight.sh owns parser builds during unattended setup.
    build = vim.env.NVIM_HIGHLIGHT_SETUP ~= "1" and function()
      LazyVim.treesitter.build(function()
        require("nvim-treesitter").update(nil, { summary = true })
      end)
    end or false,
    opts = function(_, opts)
      if vim.env.NVIM_HIGHLIGHT_SETUP == "1" then
        opts.ensure_installed = {}
        return
      end
      vim.list_extend(opts.ensure_installed, {
        "cue", "lua", "yaml", "bash", "go", "gotmpl", "gomod", "python",
        "html", "css", "javascript",
        "html_gotmpl", "yaml_gotmpl", "json_gotmpl", "bash_gotmpl", "cue_gotmpl",
      })
    end,
  },
}
