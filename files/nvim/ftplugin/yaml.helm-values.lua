-- Register the compound filetype and preserve YAML comment behavior for Helm
-- values files. Neovim also loads the base yaml ftplugin for dotted filetypes.
vim.bo.commentstring = "# %s"
