
-- loqer_room/conf.lua

function love.conf(t)
    t.identity = "enterprise_business_game"  -- The name of the save directory
    t.version = "11.5"               -- The LÖVE version this game was made for 
    t.console = true                 -- Attach a console
    t.window.title = "Enterprise Business Game"  -- The window title
    t.window.width = 800             -- The window width
    t.window.height = 600            -- The window height
end
