-- Vellum keeps Omarchy's square, flat geometry but gives light windows the
-- depth they need: a verdigris-to-clay focus seam and a warm, low shadow.

local active_border_color = { colors = { "rgba(2c6a59ee)", "rgba(9c4f17ee)" }, angle = 35 }
local inactive_border_color = "rgba(8a8375aa)"

hl.config({
  general = {
    border_size = 2,
    col = {
      active_border = active_border_color,
      inactive_border = inactive_border_color,
    },
  },

  decoration = {
    rounding = 0,
    shadow = {
      enabled = true,
      range = 18,
      render_power = 3,
      color = "rgba(26251f26)",
    },
  },

  group = {
    col = {
      border_active = active_border_color,
      border_inactive = inactive_border_color,
    },
    groupbar = {
      text_color = "rgb(26251f)",
      text_color_inactive = "rgba(26251f99)",
      col = {
        active = "rgba(2c6a591f)",
        inactive = "rgba(6a655912)",
      },
    },
  },
})
