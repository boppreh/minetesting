minetest.register_entity("bot:bot", {
    hp_max = 1000,
    physical = true,
    weight = 5,
    collisionbox = {-0.5,-0.5,-0.5, 0.5,0.5,0.5},
    visual = "mesh",
    visual_size = {x=1, y=1},
    mesh = "robot.x",
    textures = {"robot.png"},
    colors = {}, -- number of required colors depends on visual
    spritediv = {x=1, y=1},
    initial_sprite_basepos = {x=0, y=0},
    is_visible = true,
    makes_footstep_sound = false,
    automatic_rotate = false,
    groups = {immortal=1},
})

function move(pos, angle, distance)
    return {x = math.floor(.5 + pos.x + distance * math.cos(angle)),
            y = math.floor(pos.y),
            z = math.floor(.5 + pos.z + distance * math.sin(angle))}
end

bots = {}
minetest.register_on_chat_message(function(name, message)
    local bot_name, command = string.match(message, "^bot (%w+) (.+)$")
    print('Processing', command, 'for bot', bot_name)
    if bot_name == nil then
        return
    end

    if command == "criar" then
        if bots[bot_name] then
            minetest.chat_send_player(name, "Destruindo bot existente...")
            bots[bot_name]:remove()
        end

        local player = minetest.get_player_by_name(name)
        local pos = player:getpos()
        local yaw = player:get_look_yaw()
        local distance = 5
        local bot_pos = move(player:getpos(), player:get_look_yaw(), 5)
        bot_pos.y = bot_pos.y + 1.5
        bots[bot_name] = minetest.add_entity(bot_pos,
                                             "bot:bot")
        minetest.chat_send_player(name, 'Bot "' .. bot_name .. '" criado.')
        return
    end

    local bot = bots[bot_name]
    if bot == nil then
        minetest.chat_send_player(name, "Nao existe nenhum bot " .. bot_name)
        return
    end
    local position = bot:getpos()
    position.y = position.y - 1

    if command == 'testar' then
        local node = minetest.get_node(position)
        local node_name = name:sub(string.len("default:"))
        minetest.chat_send_player(name, node_name)
    elseif command == "destruir" then
        bot:remove()
        bots[bot_name] = nil
        minetest.chat_send_player(name, "destruido")
    elseif command == "remover" then
        minetest.remove_node(position)
    elseif command:sub(1, 7) == "colocar" then
        local block_name = string.match(command, "^colocar (.+)$")
        if block_name == nil or block_name == "" then
            return
        end
        local node_name = "default:" .. block_name:gsub(" ", "_"):lower()
        minetest.set_node(position, {name=node_name})
        minetest.chat_send_player(name, "colocado")
    elseif command:sub(1, 5) == "mover" then
        local direction_name = string.match(command, "^mover (.+)$")
        position = bot:getpos()
        local yaw = bot:getyaw()
        if direction_name == "frente" then
            position = move(position, yaw + math.pi/2, 1)
        elseif direction_name == "tras" then
            yaw = yaw - math.pi
            position = move(position, yaw + math.pi/2, 1)
        elseif direction_name == "direita" then
            yaw = yaw - math.pi / 2
            position = move(position, yaw + math.pi/2, 1)
        elseif direction_name == "esquerda" then
            yaw = yaw + math.pi / 2
            position = move(position, yaw + math.pi/2, 1)
        elseif direction_name == "cima" then
            position.y = position.y + 1
        elseif direction_name == "baixo" then
            position.y = position.y - 1
        else
            minetest.chat_send_player(name, "direcao invalida")
            return
        end
        bot:setyaw(yaw)
        position.y = position.y + 0.5
        bot:moveto(position, true)
        minetest.chat_send_player(name, "movido")
    else
        minetest.chat_send_player(name, "comando nao encontrado: " .. command)
    end
end)
