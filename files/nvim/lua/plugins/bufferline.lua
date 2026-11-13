return {
  "akinsho/bufferline.nvim",
  opts = {
    options = {
      mode = "buffers",
      always_show_bufferline = true,
      show_buffer_close_icons = true,
      show_close_icon = false,
      buffer_close_icon = "×",
      -- Keep the pane layout while files remain; confirm before losing edits.
      close_command = function(buf)
        require("config.quit").close_buffer(buf)
      end,
      middle_mouse_command = function(buf)
        require("config.quit").close_buffer(buf)
      end,
      right_mouse_command = "buffer %d",
    },
    highlights = {
      close_button = { fg = "#f7768e" },
      close_button_visible = { fg = "#f7768e" },
      close_button_selected = { fg = "#f7768e" },
    },
  },
}
