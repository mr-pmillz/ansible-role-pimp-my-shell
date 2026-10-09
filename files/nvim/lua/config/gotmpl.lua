local languages = {
  yml = "yaml", yaml = "yaml", json = "json", html = "html",
  bash = "bash", sh = "bash", env = "bash", cue = "cue",
}

local function detect(path, bufnr)
  local name = vim.fn.fnamemodify(path, ":t")
  if name:match("%.gohtml$") then
    return "html_gotmpl"
  end
  local stem = name:match("^(.*)%.[^.]+$") or name
  local extension = stem:match("([^%.]+)$")
  local language = languages[extension]
  if stem == "environ" or stem == "environment" or stem:match("^%.?env%.") then
    language = "bash"
  end
  if language then
    vim.b[bufnr].gtemp_injection_language = language
    return language .. "_gotmpl"
  end
  return "gotmpl"
end

vim.filetype.add({
  extension = { gotmpl = detect, gohtml = detect, gtemp = detect },
  -- Neovim's .env.* pattern runs before extension rules.
  pattern = {
    [".*%.gotmpl"] = { detect, { priority = 100 } },
    [".*%.gtemp"] = { detect, { priority = 100 } },
    [".*%.gohtml"] = { detect, { priority = 100 } },
  },
})
return { detect = detect }
