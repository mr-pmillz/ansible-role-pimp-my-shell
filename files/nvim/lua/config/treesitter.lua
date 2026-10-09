-- Custom Go-template grammars share the upstream grammar; only the injected
-- language changes. Paths follow stdpath so XDG_CONFIG_HOME/NVIM_APPNAME work.
local M = {}
M.languages = { "bash", "cue", "html", "json", "yaml" }

local function read(path)
  local file = assert(io.open(path, "rb"))
  local content = file:read("*a")
  file:close()
  return content
end

local function write(path, content)
  if vim.fn.filereadable(path) == 1 and read(path) == content then
    return false
  end
  vim.fn.mkdir(vim.fs.dirname(path), "p")
  local file = assert(io.open(path, "wb"))
  assert(file:write(content))
  file:close()
  return true
end

function M.prepare()
  local root = vim.fn.stdpath("config")
  local highlights = read(root .. "/tree-sitter-go-template/queries/highlights.scm")
  local changed = false
  for _, language in ipairs(M.languages) do
    local dialect = language .. "_gotmpl"
    local grammar = 'const make_grammar = require("../../../tree-sitter-go-template/make_grammar");\n'
      .. 'module.exports = make_grammar("' .. dialect .. '");\n'
    local injections = '((text) @injection.content\n (#set! injection.language "'
      .. language
      .. '")\n (#set! injection.combined))\n'
    changed = write(root .. "/tree-sitter/dialects/" .. dialect .. "/grammar.js", grammar) or changed
    changed = write(root .. "/tree-sitter/queries/" .. dialect .. "/highlights.scm", highlights) or changed
    changed = write(root .. "/tree-sitter/queries/" .. dialect .. "/injections.scm", injections) or changed
  end
  return changed
end

function M.register()
  local root = vim.fn.stdpath("config")
  local repo = root .. "/tree-sitter"
  local parsers = require("nvim-treesitter.parsers")
  for _, language in ipairs(M.languages) do
    local dialect = language .. "_gotmpl"
    local dir = repo .. "/dialects/" .. dialect
    if vim.fn.filereadable(dir .. "/grammar.js") == 1 then
      -- A revision hash lets TSUpdate detect edits to local grammars or queries.
      local revision = vim.fn.sha256(read(root .. "/tree-sitter-go-template/make_grammar.js")
        .. read(dir .. "/grammar.js")
        .. read(repo .. "/queries/" .. dialect .. "/highlights.scm")
        .. read(repo .. "/queries/" .. dialect .. "/injections.scm"))
      parsers[dialect] = {
        install_info = {
          path = repo,
          location = "dialects/" .. dialect,
          generate = true,
          generate_from_json = false,
          queries = "queries/" .. dialect,
          revision = revision,
        },
        requires = { language },
        tier = 2,
      }
      vim.treesitter.language.register(dialect, dialect)
    end
  end
end

function M.setup()
  vim.api.nvim_create_autocmd("User", {
    group = vim.api.nvim_create_augroup("pimp_my_shell_treesitter", { clear = true }),
    pattern = "TSUpdate",
    callback = M.register,
  })
end

return M
