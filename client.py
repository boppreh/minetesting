"""
Minetest client. Implements the low level protocol and a few commands.

Created by reading the docs at
http://dev.minetest.net/Network_Protocol
and
https://github.com/minetest/minetest/blob/master/src/clientserver.h
"""
import socket
from struct import pack, unpack, calcsize
from binascii import hexlify
from threading import Thread, Semaphore
from queue import Queue
from collections import defaultdict

# Packet types.
CONTROL = 0x00
ORIGINAL = 0x01
SPLIT = 0x02
RELIABLE = 0x03

# Types of CONTROL packets.
CONTROLTYPE_ACK = 0x00
CONTROLTYPE_SET_PEER_ID = 0x01
CONTROLTYPE_PING = 0x02

# Initial sequence number for RELIABLE-type packets.
SEQNUM_INITIAL = 0xFFDC
SEQNUM_MOD = 0x10000

# Protocol id.
PROTOCOL_ID = 0x4F457403

# No idea.
SER_FMT_VER_HIGHEST_READ = 0x1A

# Supported protocol versions lifted from official client.
MIN_SUPPORTED_PROTOCOL = 0x0d
MAX_SUPPORTED_PROTOCOL = 0x16

# Client -> Server command ids.
TOSERVER_INIT = 0x10
TOSERVER_INIT2 = 0x11
TOSERVER_PLAYERPOS = 0x23
TOSERVER_CHAT_MESSAGE = 0x32
TOSERVER_RESPAWN = 0x38
TOSERVER_DAMAGE = 0x35

# Server -> Client command ids.
TOCLIENT_INIT = 0x10
TOCLIENT_ADDNODE = 0x21
TOCLIENT_REMOVENODE = 0x22
TOCLIENT_INVENTORY = 0x27
TOCLIENT_TIME_OF_DAY = 0x29
TOCLIENT_CHAT_MESSAGE = 0x30
TOCLIENT_HP = 0x33
TOCLIENT_MOVE_PLAYER = 0x34
TOCLIENT_ACCESS_DENIED = 0x35
TOCLIENT_DEATHSCREEN = 0x37
TOCLIENT_PLAY_SOUND = 0x3F
TOCLIENT_STOP_SOUND = 0x40
TOCLIENT_PRIVILEGES = 0x41
TOCLIENT_INVENTORY_FORMSPEC = 0x42
TOCLIENT_DETACHED_INVENTORY = 0x43
TOCLIENT_MOVEMENT = 0x45
TOCLIENT_ADD_PARTICLESPAWNER = 0x47
TOCLIENT_BREATH = 0x4e


class MinetestClientProtocol(object):
    """
    Class for exchanging messages with a Minetest server. Automatically
    processes received messages in a separate thread and performs the initial
    handshake when created. Blocks until the handshake is finished.

    TODO: resend unacknowledged messages.
    """
    def __init__(self, host, username, password=''):
        if ':' in host:
            host, port = host.split(':')
            server = (host, int(port))
        else:
            server = (host, 30000)

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server = server
        self.seqnum = SEQNUM_INITIAL
        self.peer_id = 0
        self.username = username
        self.password = password

        # Priority channel, not actually implemented in the official server but
        # required for the protocol.
        self.channel = 0
        # Buffer with the messages received, filled by the listener thread.
        self.receive_buffer = Queue()
        # Last sequence number acknowledged by the server.
        self.acked = 0
        # Buffer for SPLIT-type messages, indexed by sequence number.
        self.split_buffers = defaultdict(dict)

        # Send TOSERVER_INIT and start a reliable connection. The order is
        # strange, but imitates the official client.
        self._handshake_start()
        self._start_reliable_connection()

        # Lock until the handshake is completed.
        self.handshake_lock = Semaphore(0)
        # Run listen-and-process asynchronously.
        thread = Thread(target=self._receive_and_process)
        thread.daemon = True
        thread.start()
        self.handshake_lock.acquire()

    def _send(self, packet):
        """ Sends a raw packet, containing only the protocol header. """
        header = pack('>IHB', PROTOCOL_ID, self.peer_id, self.channel)
        self.sock.sendto(header + packet, self.server)

    def _handshake_start(self):
        """ Sends the first part of the handshake. """
        packet = pack('>HB20s28sHH',
                TOSERVER_INIT, SER_FMT_VER_HIGHEST_READ,
                self.username.encode('utf-8'), self.password.encode('utf-8'),
                MIN_SUPPORTED_PROTOCOL, MAX_SUPPORTED_PROTOCOL)
        self.send_command(packet)

    def _handshake_end(self):
        """ Sends the second and last part of the handshake. """
        self.send_command(pack('>H', TOSERVER_INIT2))

    def _start_reliable_connection(self):
        """ Starts a reliable connection by sending an empty reliable packet. """
        self.send_command(b'')

    def disconnect(self):
        """ Sends a RELIABLE without sequence number. """
        self._send(pack('>H', RELIABLE))

    def _send_reliable(self, message):
        """
        Sends a reliable message. This message can be a packet of another
        type, such as CONTROL or ORIGINAL.
        """
        packet = pack('>BH', RELIABLE, self.seqnum % SEQNUM_MOD) + message
        self.seqnum += 1
        self._send(packet)

    def send_command(self, message):
        """ Sends a useful message, such as a place or say command. """
        start = pack('B', ORIGINAL)
        self._send_reliable(start + message)

    def _ack(self, seqnum):
        """ Sends an ack for the given sequence number. """
        self._send(pack('>BBH', CONTROL, CONTROLTYPE_ACK, seqnum))

    def receive_command(self):
        """
        Returns a command message from the server, blocking until one arrives.
        """
        return self.receive_buffer.get()

    def _process_packet(self, packet):
        """
        Processes a packet received. It can be of type
        - CONTROL, used by the protocol to control the connection
        (ack, set_peer_id and ping);
        - RELIABLE in which it requires an ack and contains a further message to
        be processed;
        - ORIGINAL, which designates it's a command and it's put in the receive
        buffer;
        - or SPLIT, used to send large data (unimplemented because we don't
          need visuals or to see the entire world).
        """
        packet_type, data = packet[0], packet[1:]

        if packet_type == CONTROL:
            if len(data) == 1:
                assert data[0] == CONTROLTYPE_PING
                # Do nothing. PING is sent through a reliable packet, so the
                # response was already sent we unwrapped it.
                return

            control_type, value = unpack('>BH', data)
            if control_type == CONTROLTYPE_ACK:
                self.acked = value
            elif control_type == CONTROLTYPE_SET_PEER_ID:
                self.peer_id = value
                self._handshake_end()
                self.handshake_lock.release()
        elif packet_type == RELIABLE:
            seqnum, = unpack('>H', data[:2])
            self._ack(seqnum)
            self._process_packet(data[2:])
        elif packet_type == ORIGINAL:
            self.receive_buffer.put(data)
        elif packet_type == SPLIT:
            # We can decode SPLIT packets, but the results are not making any
            # sense. Since we don't use the values passed here, we can safely
            # ignore them.
            return
            header_size = calcsize('>HHH')
            split_header, split_data = data[:header_size], data[header_size:]
            seqnumber, chunk_count, chunk_num = unpack('>HHH', split_header)
            self.split_buffers[seqnumber][chunk_num] = split_data
            if chunk_count - 1 in self.split_buffers[seqnumber]:
                complete = []
                try:
                    for i in range(chunk_count):
                        complete.append(self.split_buffers[seqnumber][chunk_num])
                except KeyError:
                    # We are missing data, ignore and wait for resend.
                    pass
                self.receive_buffer.put(b''.join(complete))
                del self.split_buffers[seqnumber]
        else:
            raise ValueError('Unknown packet type {}'.format(packet_type))



    def _receive_and_process(self):
        """
        Constantly listens for incoming packets and processes them as required.
        """
        while True:
            packet, origin = self.sock.recvfrom(1024)
            header_size = calcsize('>IHB')
            header, data = packet[:header_size], packet[header_size:]
            protocol, peer_id, channel = unpack('>IHB', header)
            assert protocol == PROTOCOL_ID, 'Unexpected protocol.'
            assert peer_id == 0x01, 'Unexpected peer id, should be 1 got {}'.format(peer_id)
            self._process_packet(data)


class MinetestClient(object):
    """
    Class for sending commands to a remote Minetest server. This creates a
    character on the running world, controlled by the methods exposed in this
    class.
    """
    def __init__(self, server='localhost:30000', username='user', password='', on_message=print):
        """
        Creates a new Minetest Client to send remote commands.

        'server' must be in the format 'host:port' or just 'host'.
        'username' is the name of the character on the world.
        'password' is an optional value used when the server is private.
        'on_message' is a function called whenever a chat message arrives.
        """
        self.protocol = MinetestClientProtocol(server, username, password)

        self.access_denied = None
        self.init_lock = Semaphore(0)
        thread = Thread(target=self._receive_and_process)
        thread.daemon = True
        thread.start()
        # Wait until we know our position, otherwise the 'move' method will not
        # work.
        self.init_lock.acquire()

        if self.access_denied is not None:
            raise ValueError('Access denied. Reason: ' + self.access_denied)

        self.on_message = on_message

        # HP is not a critical piece of information, so we assume it's full
        # until the server says otherwise.
        self.hp = 20

    def say(self, message):
        """ Sends a global chat message. """
        message = str(message)
        encoded = message.encode('UTF-16BE')
        packet = pack('>HH', TOSERVER_CHAT_MESSAGE, len(message)) + encoded
        self.protocol.send_command(packet)

    def respawn(self):
        """ Resurrects and teleports the dead character. """
        packet = pack('>H', TOSERVER_RESPAWN)
        self.protocol.send_command(packet)

    def damage(self, amount=20):
        """
        Makes the character damage itself. Amount is measured in half-hearts
        and defaults to a complete suicide.
        """
        packet = pack('>HB', TOSERVER_DAMAGE, int(amount))
        self.protocol.send_command(packet)

    def move(self, delta_position=(0,0,0), delta_angle=(0,0), key=0x01):
        """ Moves to a position relative to the player. """
        x = self.position[0] + delta_position[0]
        y = self.position[1] + delta_position[1]
        z = self.position[2] + delta_position[2]
        yaw = self.angle[0] + delta_angle[0]
        pitch = self.angle[1] + delta_angle[1]
        self.teleport(position=(x, y, z), angle=(yaw, pitch), key=key)

    def teleport(self, position=(0,0,0), speed=(0,0,0), angle=(0,0), key=0x01):
        """ Moves to an absolute position. """
        transformation = lambda k: int(k*1000)
        x, y, z = map(transformation, position)
        dx, dy, dz = map(transformation, speed)
        yaw, pitch = map(transformation, angle)
        packet = pack('>H3i3i2iI', TOSERVER_PLAYERPOS, x, y, z, dx, dy, dz, yaw, pitch, key)
        self.protocol.send_command(packet)
        self.position = position
        self.angle = angle

    def disconnect(self):
        """ Disconnects the client, removing the character from the world. """
        self.protocol.disconnect()

    def _receive_and_process(self):
        while True:
            packet = self.protocol.receive_command()
            (command_type,), data = unpack('>H', packet[:2]), packet[2:]

            if command_type == TOCLIENT_INIT:
                # No useful info here.
                pass
            elif command_type == TOCLIENT_MOVE_PLAYER:
                x1000, y1000, z1000, pitch1000, yaw1000 = unpack('>3i2i', data)
                self.position = (x1000/1000, y1000/1000, z1000/1000)
                self.angle = (yaw1000/1000, pitch1000/1000)
                self.init_lock.release()
            elif command_type == TOCLIENT_CHAT_MESSAGE:
                length, bin_message = unpack('>H', data[:2]), data[2:]
                # Length is not matching for some reason.
                #assert len(bin_message) / 2 == length 
                message = bin_message.decode('UTF-16BE')
                self.on_message(message)
            elif command_type == TOCLIENT_DEATHSCREEN:
                self.respawn()
            elif command_type == TOCLIENT_HP:
                self.hp, = unpack('B', data)
            elif command_type == TOCLIENT_INVENTORY_FORMSPEC:
                pass
            elif command_type == TOCLIENT_INVENTORY:
                pass
            elif command_type == TOCLIENT_PRIVILEGES:
                pass
            elif command_type == TOCLIENT_MOVEMENT:
                pass
            elif command_type == TOCLIENT_BREATH:
                pass
            elif command_type == TOCLIENT_DETACHED_INVENTORY:
                pass
            elif command_type == TOCLIENT_TIME_OF_DAY:
                pass
            elif command_type == TOCLIENT_REMOVENODE:
                pass
            elif command_type == TOCLIENT_ADDNODE:
                pass
            elif command_type == TOCLIENT_PLAY_SOUND:
                pass
            elif command_type == TOCLIENT_STOP_SOUND:
                pass
            elif command_type == TOCLIENT_ACCESS_DENIED:
                length, bin_message = unpack('>H', data[:2]), data[2:]
                self.access_denied = bin_message.decode('UTF-16BE')
                self.init_lock.release()
            else:
                print('Unknown command type {}.'.format(hex(command_type)))



if __name__ == '__main__':
    import sys
    import time
    import math

    args = sys.argv[1:]
    assert len(args) <= 3, 'Too many arguments, expected no more than 3'
    client = MinetestClient(*args)
    try:
        while True:
            line = sys.stdin.readline().rstrip()
            client.say(line)
    finally:
        client.protocol.disconnect()
