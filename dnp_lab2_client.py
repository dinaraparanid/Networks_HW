import os
import socket
import time
import sys
from multiprocessing import Pool

SERVER_IP = '127.0.0.1'
SERVER_PORT = 12345

CLIENT_BUFFER = 1024
UNSORTED_FILES_COUNT = 100

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
            while True:
                try:
                    return g(*args, **kwargs)
                except TailRecurseException as e:
                    args = e.args
                    kwargs = e.kwargs

    func.__doc__ = g.__doc__
    return func


def create_directories():
    if not os.path.exists('unsorted_files'):
        os.mkdir('unsorted_files')

    if not os.path.exists('sorted_files'):
        os.mkdir('sorted_files')


def download_unsorted_files():
    @tailrec
    def retrieve_file_content(sock: socket.socket, content: bytes = b'') -> bytes:
        packet = sock.recv(CLIENT_BUFFER)
        return content if not packet else retrieve_file_content(sock, content + packet)

    def download_file(file_index: int):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((SERVER_IP, SERVER_PORT))
            file_content = retrieve_file_content(s)

            with open(f'unsorted_files/{file_index}.txt', 'wb') as f:
                f.write(file_content)

    @tailrec
    def impl(steps_left: int = UNSORTED_FILES_COUNT):
        download_file(file_index=UNSORTED_FILES_COUNT - steps_left)
        return None if steps_left <= 0 else impl(steps_left - 1)

    impl()


def create_sorted_files():
    @tailrec
    def impl(prc_pool: Pool, steps_left: int = UNSORTED_FILES_COUNT):
        unsorted_id = UNSORTED_FILES_COUNT - steps_left
        prc_pool.map(handle_unsorted_file, [unsorted_id])
        return None if steps_left <= 0 else impl(prc_pool, steps_left - 1)

    with Pool(processes=os.cpu_count()) as prc_pool:
        impl(prc_pool)


def handle_unsorted_file(unsorted_id: int):
    def sort_numbers() -> list[int]:
        with open(f'unsorted_files/{unsorted_id}.txt') as unsorted_file:
            unsorted_list = [int(number) for number in unsorted_file.read().split(',')]
            return sorted(unsorted_list)

    def store_numbers(sorted_list: list[int]):
        with open(f'sorted_files/{unsorted_id}.txt', 'w') as sorted_file:
            sorted_file.write(','.join(map(str, sorted_list)))

    store_numbers(sort_numbers())


def handle_unsorted_files():
    tdownload0 = time.monotonic()
    download_unsorted_files()
    tdownload = time.monotonic() - tdownload0
    print(f"Files download time: {tdownload}")


def handle_sorted_files():
    tsort0 = time.monotonic()
    create_sorted_files()
    tsort = time.monotonic() - tsort0
    print(f"Sorting time: {tsort}")


def main():
    try:
        create_directories()
        handle_unsorted_files()
        handle_sorted_files()
    except ConnectionRefusedError:
        print("Server is down...")
    except KeyboardInterrupt:
        print("Shutting down...")


if __name__ == '__main__':
    main()
