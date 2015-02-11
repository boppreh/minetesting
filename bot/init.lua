minetest.register_entity("bot:bot", {
    hp_max = 1,
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
})

bots = {}
directions = {}
directions["+"] = 1
directions["-"] = -1
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
        bots[bot_name] = minetest.add_entity({x = math.floor(pos.x),
                                              y = math.floor(pos.y)+1.5,
                                              z = math.floor(pos.z)},
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
        local axis
        local direction
        if direction_name == "frente" then
            axis = "z"
            direction = 1
        elseif direction_name == "tras" then
            axis = "z"
            direction = -1
        elseif direction_name == "direita" then
            axis = "x"
            direction = 1
        elseif direction_name == "esquerda" then
            axis = "x"
            direction = -1
        elseif direction_name == "cima" then
            axis = "y"
            direction = 1
        elseif direction_name == "baixo" then
            axis = "y"
            direction = -1
        else
            minetest.chat_send_player(name, "direcao invalida")
            return
        end
        position[axis] = position[axis] + direction
        bot:moveto(position, true)
        minetest.chat_send_player(name, "movido")
    else
        minetest.chat_send_player(name, "comando nao encontrado: " .. command)
    end
end)
