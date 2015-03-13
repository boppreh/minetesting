# minetesting

This project consists of a **Python client** for talking with a Minetest server,
and a **Minetest Mod** that creates a chat-controlled robot. Those two parts
are independent, but play well with each other.

The Python client (`client.py`) speaks the Minetest protocol and logs in as a
regular user.  It's not feature complete, but the basics are stable and it's
easy to implement the missing commands. You can use it as a library and import
`MinetestClient`, or run as `python3 client.py *hostname* *username* *password*`,
where each message typed in the console is sent as a chat message to the
server.

The Minetest mod (`bot/`) allows users to create and controls robots by speaking
commands in the chat. These robots can move through the map, placing and
removing blocks. To install it just copy the entire `bot/` folder to
`.minetest/mods` and activate in the world configuration.

Because the robots answer to regular chat commands, the Python client is able
to login and say commands to the robot, giving a remote interface to control
it.

`controller.py` is used as the glue between Scratch and the Minetest bot, creating an HTTP server and forwarding commands.
