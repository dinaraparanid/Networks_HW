import socket
import random
import sys
from threading import Thread

SERVER_IP = '127.0.0.1'
SERVER_PORT = 12345

MIN_GENERATE = -999_999_999
MAX_GENERATE = 999_999_999
GENERATE_NUM = 250_000


sys.setrecursionlimit(sys.getrecursionlimit())


class TailRecurseException(BaseException):
    def __init__(self, args, kwargs):
        self.args = args
        self.kwargs = kwargs


def tailrec(g):
    def func(*args, **kwargs):
        f = sys._getframe()

        if f.f_back and f.f_back.f_back \
                and f.f_back.f_back.f_code == f.f_code:
            raise TailRecurseException(args, kwargs)
        else:
            while 1:
                try:
                    return g(*args, **kwargs)
                except TailRecurseException as e:
                    args = e.args
                    kwargs = e.kwargs

    func.__doc__ = g.__doc__
    return func


def launch_server():
    print(f'Listening on {SERVER_IP}:{SERVER_PORT}')

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_sock:
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind((SERVER_IP, SERVER_PORT))
        server_sock.listen()
        process_requests(server_sock)


def process_requests(server_sock: socket.socket):
    def process_request(conn: socket.socket, addr: (str, int)):
        conn.send(generate_response())
        conn.close()
        print(f'Sent a file to {addr}')

    @tailrec
    def impl():
        conn, addr = server_sock.accept()
        Thread(target=process_request, args=(conn, addr)).start()
        return impl()

    impl()


def generate_response():
    nums = [random.randint(MIN_GENERATE, MAX_GENERATE) for _ in range(GENERATE_NUM)]
    return ','.join(map(str, nums)).encode()


def main():
    try:
        launch_server()
    except KeyboardInterrupt:
        print('Shutting down...')


if __name__ == '__main__':
    main()
