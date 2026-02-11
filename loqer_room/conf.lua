
-- loqer_room/conf.lua

function love.conf(t)
    t.identity = "loqer_room"        -- The name of the save directory
    t.version = "11.5"               -- The LÖVE version this game was made for 
    t.console = true                 -- Attach a console
    t.window.title = "Loqer Room"    -- The window title
    t.window.width = 800             -- The window width
    t.window.height = 600            -- The window height
end
