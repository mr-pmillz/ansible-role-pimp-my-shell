local ok, err = xpcall(function()
  local lazy = require("lazy")
  local config = require("lazy.core.config")
  local changed = false
  for _, plugin in pairs(config.plugins) do
    changed = changed or not plugin._.installed or plugin._.build or #(plugin._.tasks or {}) > 0
  end
  lazy.install({ wait = true, show = false, lockfile = true })
  for name, plugin in pairs(config.plugins) do
    assert(plugin._.installed, "Plugin was not installed: " .. name)
    for _, task in ipairs(plugin._.tasks or {}) do
      assert(not task:has_errors(), name .. ": " .. task:output())
    end
  end
  io.stdout:write("HIGHLIGHT_CHANGED=" .. (changed and "1" or "0") .. "\n")
  io.stdout:flush()
end, debug.traceback)
if not ok then
  io.stderr:write(tostring(err) .. "\n")
  vim.cmd("cquit 1")
end
vim.cmd("qa!")
