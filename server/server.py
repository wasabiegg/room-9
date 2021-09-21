from typing import Optional
import socket
import select
from message import Message
from user import User
import argparse
import sys


# HOST = "127.0.0.1"
# PORT = 9090
HEADER_SIZE = 4  # u32 # can contains 4GB
BUFFER_SIZE = 1024

APPLICATION = "ROOM 9"


def main():
    parser = argparse.ArgumentParser(prog=f"{APPLICATION} server")
    parser.add_argument(
        "Addr", metavar="addr", type=str, help="listen address, ****:9999"
    )
    # parser.add_argument(
    #     "-u", "--username", type=str, help="specify a username to login in server"
    # )

    args = parser.parse_args()
    server_str = args.Addr

    host, port = server_str.split(":")
    try:
        port = int(port)
    except ValueError:
        print(f"can't parse addr '{server_str}', check it again")
        sys.exit(1)

    server = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)

    # set to non blocking
    # sock.setblocking(True) is equivalent to sock.settimeout(None)
    # sock.setblocking(False) is equivalent to sock.settimeout(0.0)
    server.setblocking(False)

    # allow to reconnect
    server.setsockopt(
        socket.SOL_SOCKET, socket.SO_REUSEADDR, 1
    )  # 0 is False, 1 is True
    server.bind((host, port))

    print("[STARTING] server is starting...")
    print(f"[LISTENING] {host}:{port}")
    # set max queue number
    server.listen(512)

    # add socket to inputs socket list
    inputs = [server]

    clients = {}
    message_queues = []

    def purge_conn(conn: socket.socket):
        inputs.remove(s)
        del clients[s]
        conn.close()

    while inputs:
        readable, writeable, exceptional = select.select(inputs, [], inputs)

        for s in readable:
            # s is main server, just accpect new connection, then add to inputs
            if s is server:
                conn, addr = s.accept()
                conn.setblocking(0)

                username = get_username(conn)
                if username is None:
                    continue

                print(f"connected from {addr}")
                inputs.append(conn)
                clients[conn] = User(username, addr)
            # s is client, handle message from client
            else:
                user = clients[s]
                msg = handle(s, user)
                if msg is not None:
                    message_queues.append(msg)
                else:
                    purge_conn(s)

        for s in exceptional:
            # if error occured in a socket, purge it
            purge_conn(s)

        # debug print
        for msg in message_queues:
            print(msg)

        # send new messages to client
        for client, _ in clients.items():
            for msg in message_queues:
                send_msg(client, msg)

        # clear message_queues after jobs done
        message_queues.clear()


# get username from client, if failed, refuse connection
def get_username(conn: socket.socket) -> Optional[str]:
    try:
        username_header_length = int.from_bytes(
            conn.recv(HEADER_SIZE), byteorder="big"
        )  # u32

        if username_header_length == 0:
            return None

        username = conn.recv(username_header_length).decode("utf-8")
        return username
    except Exception as e:
        print(e)
        return None


# send message: Message to client
def send_msg(conn: socket.socket, msg: Message):
    msg_bytes = msg.to_bytes()
    msg_length = len(msg_bytes).to_bytes(HEADER_SIZE, byteorder="big")

    # print(f"[DEBUG] msg_bytes: {msg_bytes}")
    # print(f"[DEBUG] msg_length: {msg_length}")
    conn.send(msg_length + msg_bytes)


def handle(conn: socket.socket, user: User) -> Optional[Message]:
    try:

        msg = b""
        msg_length = int.from_bytes(conn.recv(HEADER_SIZE), byteorder="big")  # u32
        if msg_length == 0:
            return None

        while len(msg) != msg_length:
            msg_chunk = conn.recv(BUFFER_SIZE)
            if len(msg_chunk) == 0:
                connected = False
                break

            msg += msg_chunk

        # return message str
        msg = Message.new(msg.decode("utf-8"), user)
        # msg_str = f"[MESSAGE] - {msg.decode('utf-8')} - [{msg_length} bytes] - {addr}"
        return msg
    except ConnectionResetError:
        return None
    except Exception as e:
        print(e)
        return None


if __name__ == "__main__":
    main()
