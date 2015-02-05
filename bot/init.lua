minetest.register_entity("bot:bot", {
    hp_max = 1,
    physical = true,
    weight = 5,
    collisionbox = {-0.5,-0.5,-0.5, 0.5,0.5,0.5},
    visual = "sprite",
    visual_size = {x=1, y=1},
    mesh = "model",
    textures = {}, -- number of required textures depends on visual
    colors = {}, -- number of required colors depends on visual
    spritediv = {x=1, y=1},
    initial_sprite_basepos = {x=0, y=0},
    is_visible = true,
    makes_footstep_sound = false,
    automatic_rotate = false,
})

bots = nil
minetest.register_on_chat_message(function(name, message)
    local player = minetest.get_player_by_name(name)
    if message == "create" then
        local pos = player:getpos()
        if bot ~= nil then
            bot:remove()
        end
        bot = minetest.add_entity({x = math.floor(pos.x),
                                   y = math.floor(pos.y)+1,
                                   z = math.floor(pos.z)}, "bot:bot")
    elseif message == "destroy" then
        if bot ~= nil then
            bot:remove()
            bot = nil
        end
    elseif message == "place" then
        minetest.place_node(bot:getpos(), {name="default:lava_source"})
    elseif message == 'x' or 'message' == y or 'message' == 'x' then
        local y = bot:getpos().y
        local x = bot:getpos().x
        local z = bot:getpos().z
        if message == "x" then
            bot:moveto({x=x+1,y=y,z=z}, true)
        end
        if message == "y" then
            bot:moveto({x=x,y=y+1,z=z}, true)
        end
        if message == "z" then
            bot:moveto({x=x,y=y,z=z+1}, true)
        end
    end
end)
