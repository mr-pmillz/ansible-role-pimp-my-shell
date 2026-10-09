return {
  "folke/snacks.nvim",
  opts = function(_, opts)
    -- Debian-family runtime packages expose the versioned library. The bare
    -- "sqlite3" name normally requires development-package symlinks.
    if vim.fn.has("linux") == 1 and pcall(require("ffi").load, "libsqlite3.so.0") then
      -- Configuring an absent Snacks module enables it implicitly. Keep the
      -- bundled fzf-lua picker unless the user already opted into Snacks.picker.
      opts.picker = opts.picker or { enabled = false }
      opts.picker.db = opts.picker.db or {}
      opts.picker.db.sqlite3_path = opts.picker.db.sqlite3_path or "libsqlite3.so.0"
    end
  end,
}
