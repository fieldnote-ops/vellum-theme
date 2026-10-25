-- Vellum's Neovim palette.
--
-- Omarchy's template only hands Aether the colours: Neovim still reports
-- `background=dark`, the popup menu has no fill of its own, and PmenuSel is a
-- mid grey that leaves dark ink at 1.9:1. Vellum reads its own colors.toml —
-- the file every other app theme is rendered from — and pins the popup ladder
-- the palette needs: paper page, bar-deep menu, mist selection, ink text.

local function read_palette(path)
  local colors = {}
  local ok = pcall(function()
    for line in io.lines(path) do
      local key, value = line:match('^([%w_]+)%s*=%s*"(#%x%x%x%x%x%x)"')
      if key then
        colors[key] = value
      end
    end
  end)
  if ok and next(colors) then
    return colors
  end
  return nil
end

-- Lazy may import these specs from a string, so `debug.getinfo` is only the
-- last resort: the staged theme is the canonical copy of colors.toml.
local function palette()
  local source = debug.getinfo(1, "S").source:sub(2)
  local staged = vim.fn.stdpath("state") .. "/../omarchy/current/theme/colors.toml"
  for _, path in ipairs({ staged, vim.fn.expand("~/.local/state/omarchy/current/theme/colors.toml"), vim.fn.fnamemodify(source, ":h") .. "/colors.toml" }) do
    local colors = read_palette(path)
    if colors then
      return colors
    end
  end
  return {}
end

local c = palette()
local pinning = false

local function pin_surfaces()
  if pinning or not (c.foreground and c.background and c.dark_background) then
    return
  end
  pinning = true
  if vim.o.background ~= "light" then
    vim.o.background = "light"
  end
  vim.o.pumblend = 0

  local page, bar, card = c.background, c.dark_background, c.lighter_background
  local mist, mist_fg = c.selection_background, c.selection_foreground
  local function hl(group, spec)
    pcall(vim.api.nvim_set_hl, 0, group, spec)
  end

  hl("Normal", { fg = c.foreground, bg = page })
  hl("NormalFloat", { fg = c.foreground, bg = card })
  hl("FloatBorder", { fg = c.muted, bg = card })
  hl("FloatTitle", { fg = c.foreground, bg = card, bold = true })
  hl("FloatFooter", { fg = c.muted, bg = card })

  hl("Pmenu", { fg = c.foreground, bg = bar })
  hl("PmenuSel", { fg = mist_fg, bg = mist, bold = true })
  hl("PmenuBorder", { fg = c.muted, bg = bar })
  hl("PmenuKind", { fg = c.muted, bg = bar })
  hl("PmenuKindSel", { fg = mist_fg, bg = mist })
  hl("PmenuExtra", { fg = c.muted, bg = bar })
  hl("PmenuExtraSel", { fg = mist_fg, bg = mist })
  hl("PmenuMatch", { fg = c.accent, bg = bar, bold = true })
  hl("PmenuMatchSel", { fg = mist_fg, bg = mist, bold = true })
  hl("PmenuSbar", { bg = c.darker_background })
  hl("PmenuThumb", { bg = c.muted })

  pinning = false
end

if vim.o.background ~= "light" then
  vim.o.background = "light"
end

-- Aether applies its own groups while `:colorscheme` runs, so pin on the next
-- tick rather than inside the same event.
local function pin_later()
  vim.schedule(pin_surfaces)
end

vim.api.nvim_create_autocmd("ColorScheme", { callback = pin_later })
vim.api.nvim_create_autocmd("User", { pattern = "LazyDone", callback = pin_later })
vim.api.nvim_create_autocmd("VimEnter", { callback = pin_later })
pin_surfaces()

return {
  {
    "bjarneo/aether.nvim",
    branch = "v3",
    name = "aether",
    priority = 1000,
    opts = {
      colors = c,
    },
  },
  {
    "LazyVim/LazyVim",
    opts = {
      colorscheme = "aether",
    },
  },
}
