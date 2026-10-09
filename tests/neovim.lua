-- Run after highlight.sh in an isolated XDG config/data directory (see README).
vim.opt.rtp:prepend(vim.fn.stdpath("config"))
vim.opt.rtp:append(vim.fn.stdpath("data") .. "/site")
require("config.filetypes")
local gotmpl = require("config.gotmpl")
local cases = {
  ["settings.yaml.gotmpl"] = "yaml_gotmpl",
  ["settings.yml.gtemp"] = "yaml_gotmpl",
  ["settings.json.gotmpl"] = "json_gotmpl",
  ["page.html.gotmpl"] = "html_gotmpl",
  ["page.gohtml"] = "html_gotmpl",
  ["run.sh.gotmpl"] = "bash_gotmpl",
  ["config.cue.gotmpl"] = "cue_gotmpl",
  [".env.gotmpl"] = "bash_gotmpl",
  [".env.production.gotmpl"] = "bash_gotmpl",
  ["environ.gtemp"] = "bash_gotmpl",
  ["unknown.gotmpl"] = "gotmpl",
}
for name, expected in pairs(cases) do
  local actual = gotmpl.detect(name, 0)
  assert(actual == expected, name .. ": expected " .. expected .. ", got " .. actual)
  assert(vim.filetype.match({ filename = name, buf = 0 }) == expected, name .. ": filetype detection failed")
end

local filetypes = {
  [".gitlab-ci.yml"] = "yaml.gitlab",
  ["compose.yaml"] = "yaml.docker-compose",
  ["docker-compose.yml"] = "yaml.docker-compose",
  ["page.shtml"] = "superhtml",
}
for name, expected in pairs(filetypes) do
  assert(vim.filetype.match({ filename = name, buf = 0 }) == expected, name .. ": filetype detection failed")
end
local chart = vim.fn.tempname()
vim.fn.mkdir(chart, "p")
vim.fn.writefile({ "apiVersion: v2", "name: test", "version: 1.0.0" }, chart .. "/Chart.yaml")
assert(vim.filetype.match({ filename = chart .. "/values.yaml", buf = 0 }) == "yaml.helm-values")
assert(vim.filetype.match({ filename = chart .. "/values-production.yml", buf = 0 }) == "yaml.helm-values")
vim.fn.delete(chart, "rf")
assert(vim.filetype.match({ filename = chart .. "/values.yaml", buf = 0 }) == "yaml", "ordinary YAML misdetected as Helm")
local known = vim.filetype._get_known_filetypes()
for _, filetype in ipairs({ "gotmpl", "superhtml", "yaml.gitlab", "yaml.docker-compose", "yaml.helm-values" }) do
  assert(known[filetype], "filetype missing from LSP registry: " .. filetype)
end

local samples = {
  bash = 'echo "{{ .Name }}"\n',
  cue = 'name: "{{ .Name }}"\n',
  html = '<p>{{ .Name }}</p>\n',
  json = '{"name": "{{ .Name }}"}\n',
  yaml = 'name: "{{ .Name }}"\n',
}
for language, text in pairs(samples) do
  local dialect = language .. "_gotmpl"
  local parser = vim.treesitter.get_string_parser(text, dialect)
  parser:parse(true)
  assert(parser:children()[language], dialect .. ": embedded language was not parsed")
  local query = assert(vim.treesitter.query.get(dialect, "highlights"))
  local count = 0
  for _ in query:iter_captures(parser:trees()[1]:root(), text) do
    count = count + 1
  end
  assert(count > 0, dialect .. ": template tokens were not highlighted")
end
print("Passed filetype detection and five Go-template highlighting/injection checks")
