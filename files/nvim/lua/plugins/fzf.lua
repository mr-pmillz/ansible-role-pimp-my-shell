return {
  "ibhagwan/fzf-lua",
  opts = function(_, opts)
    -- Use the role's compatible binary even when an older distro fzf occurs
    -- earlier on PATH, including launches from a desktop or an existing shell.
    for _, binary in ipairs({ "~/.local/bin/fzf", "~/.fzf/bin/fzf" }) do
      binary = vim.fn.expand(binary)
      if vim.fn.executable(binary) == 1 then
        opts.fzf_bin = binary
        break
      end
    end
  end,
}
