-- Options are automatically loaded before lazy.nvim startup
-- Default options that are always set: https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/options.lua
-- Add any additional options here

-- enhance filetype detection. nvim will:
-- - check extensions and set the 'filetype' option
-- - if the extension is unknown, it runs $VIMRUNTIME/scripts.vim to
--   check the contents and attempt detection
-- REMINDER: nvim-treesitter is responsible for generating syntax parsers,
--   so adding them involves updating the nvim-treesitter configurations.
vim.filetype.add({
  extension = {
    cue = "cue",
    shtml = "superhtml",
  },
  filename = {
    [".gitlab-ci.yml"] = "yaml.gitlab",
    [".gitlab-ci.yaml"] = "yaml.gitlab",
    ["docker-compose.yml"] = "yaml.docker-compose",
    ["docker-compose.yaml"] = "yaml.docker-compose",
    ["compose.yml"] = "yaml.docker-compose",
    ["compose.yaml"] = "yaml.docker-compose",
  },
  pattern = {
    [".*/values.*%.ya?ml"] = function(path)
      return vim.fs.root(path, "Chart.yaml") and "yaml.helm-values" or nil
    end,
  },
})
