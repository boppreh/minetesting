from client import MinetestClient
from queue import Queue

class MinetestRobotController(MinetestClient):
    def __init__(self, host='localhost:30000', user='user', password=''):
        MinetestClient.__init__(self, host, user, password)

        self.answer_buffer = Queue()
        self.on_message = self._distinguish_message

    def command(self, robot, message):
        self.say('bot {} {}'.format(robot, message))
        return self.answer_buffer.get()

    def _distinguish_message(self, message):
        if message.startswith('Server -!- '):
            block_name = message[len('Server -!- '):]
            self.answer_buffer.put(block_name)
        else:
            print(message)

    def disconnect(self):
        MinetestClient.disconnect(self)


if __name__ == '__main__':
    import sys
    import time
    import math

    from flask import Flask
    app = Flask(__name__)

    controller = MinetestRobotController()

    @app.route("/<name>/<command>")
    def command(name, command):
        return controller.command(name, command)

    try:
        app.run(port=50209)
    finally:
        controller.disconnect()
