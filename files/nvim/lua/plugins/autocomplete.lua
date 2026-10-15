return {
  {
    "hrsh7th/nvim-cmp",
    -- Apply mappings after all opts functions, including completion.lua's replacement table.
    ---@param opts cmp.ConfigSchema
    config = function(_, opts)
      local cmp = require("cmp")
      local luasnip = require("luasnip")

      -- Normalize existing key names before overriding Tab and Shift-Tab.
      opts.mapping = cmp.mapping.preset.insert(opts.mapping or {})
      opts.mapping["<Tab>"] = cmp.mapping(function(fallback)
        if cmp.visible() then
          cmp.select_next_item({ behavior = cmp.SelectBehavior.Select })
        elseif luasnip.locally_jumpable(1) then
          luasnip.jump(1)
        else
          fallback()
        end
      end, { "i", "s" })
      opts.mapping["<S-Tab>"] = cmp.mapping(function(fallback)
        if cmp.visible() then
          cmp.select_prev_item({ behavior = cmp.SelectBehavior.Select })
        elseif luasnip.locally_jumpable(-1) then
          luasnip.jump(-1)
        else
          fallback()
        end
      end, { "i", "s" })

      -- completion.lua also replaces the LuaSnip extra's snippet expansion option.
      opts.snippet = {
        expand = function(args)
          luasnip.lsp_expand(args.body)
        end,
      }

      -- Preserve LazyVim's completion setup and event handlers.
      require("lazyvim.util.cmp").setup(opts)
    end,
  },
}
