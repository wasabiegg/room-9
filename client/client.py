import socket
import time
import threading
import curses
import sys
import os

# from curses.textpad import Textbox, rectangle
from typing import Optional
import select
from message import Message
import argparse
import names


# network settings
HEADER_SIZE = 4  # u32
BUFFER_SIZE = 1024

# window settings
HEADER_HEIGHT = 3
INPUT_HEIGHT = 3

APPLICATION = "ROOM 9"

# init curses
stdscr = curses.initscr()
stdscr.clear()


def get_random_name() -> str:
    return names.get_full_name()


def get_windows():
    # Wh = curses.LINES  # window height
    # Ww = curses.COLS  # window width

    header_win = curses.newwin(HEADER_HEIGHT, curses.COLS, 0, 0)
    header_win.border(0)

    msg_list_height = curses.LINES - HEADER_HEIGHT - INPUT_HEIGHT
    message_list_win = curses.newwin(msg_list_height, curses.COLS, HEADER_HEIGHT, 0)
    message_list_win.scrollok(True)
    message_list_win.border(0)

    input_win = curses.newwin(
        INPUT_HEIGHT, curses.COLS, msg_list_height + HEADER_HEIGHT, 0
    )
    input_win.border(0)

    return (header_win, message_list_win, input_win)


def clean_curses():
    curses.nocbreak()
    stdscr.keypad(False)
    curses.echo()
    curses.endwin()


def get_input(win, r: int, c: int):
    win.clear()
    # win_title = " INPUT "
    # win.addstr(0, curses.COLS // 2 - (len(win_title) // 2), win_title, curses.A_REVERSE)
    # win.noutrefresh()

    curses.echo()
    prompt_string = ">>> "
    # prompt_string = "[INPUT] "
    win.addstr(r + 1, c, prompt_string)
    win.border(0)
    win.noutrefresh()
    user_input = win.getstr(r + 1, c + len(prompt_string), curses.COLS).decode("utf-8")
    return user_input


def main():
    parser = argparse.ArgumentParser(prog=f"{APPLICATION} client")
    parser.add_argument("Host", metavar="host", type=str, help="server host, ****:9999")
    parser.add_argument(
        "-u", "--username", type=str, help="specify a username to login in server"
    )

    args = parser.parse_args()
    server_str = args.Host

    host, port = server_str.split(":")
    try:
        port = int(port)
    except ValueError:
        print(f"can't parse host '{server_str}', check it again")
        sys.exit(1)

    if args.username:
        username = args.username
    else:
        username = get_random_name()

    # stdscr.addstr(0, 0, "Enter IM message: (hit Ctrl-G to send)")

    header_win, message_list_win, input_win = get_windows()

    header_win_title = f" {APPLICATION} "
    header_win.addstr(
        1,
        curses.COLS // 2 - (len(header_win_title) // 2),
        header_win_title,
        curses.A_REVERSE,
    )

    message_list_win.addstr("\n")
    message_list_win.addstr(f"  {host}:{port} <=> [CONNECTED]\n", curses.A_DIM)
    message_list_win.border(0)

    # input_win_title = " INPUT "
    # input_win.addstr(
    #     0, curses.COLS // 2 - (len(input_win_title) // 2), input_win_title, curses.A_REVERSE
    # )

    header_win.noutrefresh()
    message_list_win.noutrefresh()
    input_win.noutrefresh()
    curses.doupdate()

    client = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
    client.connect((host, port))

    # say hi to server
    send_msg(client, username)

    inputs = [client]
    monitor_msg_task = threading.Thread(
        target=monitor_socket, args=(client, message_list_win, inputs)
    )
    monitor_msg_task.start()

    while inputs:
        # s = input_win.getstr(0, 0, 15).decode("utf-8")
        s = get_input(input_win, 0, 2)
        if s == "":
            continue

        msg = s
        send_msg(client, msg)
        # message_list_win.addstr(f"  {datetime.datetime.now()} - {msg}\n")
        # message_list_win.border(0)
        # message_list_win.refresh()
        # message_list_win.addstr(f" {msg}\n", curses.A_DIM)

    monitor_msg_task.join()


# monitor new messages from server, then put messages to msg list
def monitor_socket(conn: socket.socket, msg_window, inputs):
    while inputs:
        readable, writeable, exceptional = select.select(inputs, [], inputs)

        for s in readable:
            time.sleep(0.1)
            msg = recv_msg(s)
            if msg is None:
                inputs.remove(conn)
                return
            else:
                msg = Message.new(msg)
                msg_window.addstr(f"  {msg}\n")
                # msg_window.addstr(f"asdasdasd\n")
                msg_window.border(0)
                msg_window.noutrefresh()
                curses.doupdate()


# send msg to chat group
def send_msg(conn: socket.socket, msg: str):
    if msg == "":
        msg = "\\n"
    msg_bytes = msg.encode("utf-8")
    msg_length = len(msg_bytes).to_bytes(HEADER_SIZE, byteorder="big")

    # print(f"[DEBUG] msg_bytes: {msg_bytes}")
    # print(f"[DEBUG] msg_length: {msg_length}")
    conn.send(msg_length + msg_bytes)


# read new msg from server
def recv_msg(conn: socket.socket) -> Optional[str]:
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
        # msg_str = f"[MESSAGE] - {msg.decode('utf-8')} - [{msg_length} bytes] - {addr}"
        msg_str = msg.decode("utf-8")
        return msg_str
    except ConnectionResetError:
        return None
    except Exception as e:
        print(e)
        return None


if __name__ == "__main__":
    try:
        main()
    # except (KeyboardInterrupt, SystemExit):
    except KeyboardInterrupt:
        print("Ctrl-C detected, exiting...")
        clean_curses()
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
