local ok, err = xpcall(function()
  local root = assert(vim.env.NVIM_HIGHLIGHT_CONFIG)
  vim.opt.rtp:prepend(root)
  local plugin = vim.fn.stdpath("data") .. "/lazy/nvim-treesitter"
  assert(vim.fn.isdirectory(plugin) == 1, "nvim-treesitter is missing; plugin installation failed")
  vim.opt.rtp:append(plugin)
  vim.opt.rtp:append(plugin .. "/runtime")
  local custom = require("config.treesitter")
  local changed = custom.prepare()
  custom.setup()
  local ts = require("nvim-treesitter")
  assert(ts.get_available and ts.install, "The nvim-treesitter main branch is required")
  ts.setup({ install_dir = vim.fn.stdpath("data") .. "/site" })
  local available = ts.get_available()
  local definitions = require("nvim-treesitter.parsers")
  local requested = vim.split(vim.env.TREESITTER_LANGUAGES or "all", "[, %s]+", { trimempty = true })
  assert(#requested > 0, "TREESITTER_LANGUAGES cannot be empty")
  local selected = {}
  local function select_language(language)
    local parser = definitions[language]
    assert(parser, "Unknown Tree-sitter language: " .. language)
    assert(parser.tier ~= 4, "Unsupported Tree-sitter language: " .. language)
    if selected[language] then
      return
    end
    selected[language] = true
    for _, dependency in ipairs(parser.requires or {}) do
      select_language(dependency)
    end
  end
  for _, language in ipairs(requested) do
    if language == "all" then
      for _, candidate in ipairs(available) do
        if definitions[candidate].tier ~= 4 then
          select_language(candidate)
        end
      end
    else
      select_language(language)
    end
  end
  for _, language in ipairs(custom.languages) do
    select_language(language .. "_gotmpl")
  end
  local languages = vim.tbl_keys(selected)
  table.sort(languages)
  local site = vim.fn.stdpath("data") .. "/site"
  local missing, outdated = {}, {}
  for _, language in ipairs(languages) do
    local parser = definitions[language]
    local info = parser.install_info
    local binary = site .. "/parser/" .. language .. ".so"
    local queries = site .. "/queries/" .. language
    local needs_queries = info and info.queries or vim.fn.isdirectory(plugin .. "/runtime/queries/" .. language) == 1
    local complete = (not info or vim.fn.filereadable(binary) == 1)
      and (not needs_queries or vim.fn.isdirectory(queries) == 1)
    if complete and info then
      complete = pcall(vim.treesitter.language.add, language, { path = binary })
    end
    if not complete then
      missing[#missing + 1] = language
    elseif info and info.revision then
      local rev = site .. "/parser-info/" .. language .. ".revision"
      if vim.fn.filereadable(rev) == 0 or vim.fn.readfile(rev)[1] ~= info.revision then
        outdated[#outdated + 1] = language
      end
    end
  end
  local options = { max_jobs = tonumber(vim.env.TREESITTER_JOBS) or 4, summary = true, force = true }
  local timeout = (tonumber(vim.env.TREESITTER_TIMEOUT) or 3600) * 1000
  io.stdout:write(("Checking %d languages; %d missing/broken, %d outdated\n"):format(#languages, #missing, #outdated))
  io.stdout:flush()
  -- force repairs partial installs (queries without a binary or vice versa),
  -- which the normal install API otherwise mistakes for an installed language.
  local success = true
  if #missing > 0 then
    success = ts.install(missing, options):wait(timeout) ~= false and success
    changed = true
  end
  if #outdated > 0 then
    success = ts.install(outdated, options):wait(timeout) ~= false and success
    changed = true
  end
  local failures = {}
  for _, language in ipairs(languages) do
    local parser = definitions[language]
    local valid, reason = pcall(function()
      if parser.install_info then
        vim.treesitter.language.add(language, { path = site .. "/parser/" .. language .. ".so" })
        for _, path in ipairs(vim.api.nvim_get_runtime_file("queries/" .. language .. "/*.scm", true)) do
          local query = vim.fn.fnamemodify(path, ":t:r")
          vim.treesitter.query.get(language, query)
        end
      end
    end)
    if not valid then
      failures[#failures + 1] = language .. ": " .. tostring(reason)
    end
  end
  assert(success and #failures == 0, "Tree-sitter setup failed; rerun to retry. See :TSLog.\n" .. table.concat(failures, "\n"))
  io.stdout:write(("Verified %d Tree-sitter languages, including all five Go-template dialects\n"):format(#languages))
  io.stdout:write("HIGHLIGHT_CHANGED=" .. (changed and "1" or "0") .. "\n")
  io.stdout:flush()
end, debug.traceback)
if not ok then
  io.stderr:write(tostring(err) .. "\n")
  vim.cmd("cquit 1")
end
