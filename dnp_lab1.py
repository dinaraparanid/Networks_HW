import argparse
import socket
import sys

from dataclasses import dataclass
from enum import Enum
from os import path
from typing import TypeAlias

HOST = "0.0.0.0"
BUFFER_SIZE = 20480

Addr: TypeAlias = (str, int)


@dataclass(init=True, frozen=True, eq=True)
class ClientState:
    addr: Addr
    seqno: int
    filename: str
    bytes_left: int


class RequestType(Enum):
    START = 1
    DATA = 2
    ILLEGAL = 3


@dataclass(init=True, frozen=True, eq=True, match_args=True)
class RequestState:
    request_type: RequestType
    is_enough_clients: bool
    is_client_active: bool
    is_correct_seqno: int


sys.setrecursionlimit(2000)


def parse_port_clients() -> (int, int):
    parser = argparse.ArgumentParser(description='Server args parser')
    parser.add_argument('port', type=int)
    parser.add_argument('clients', type=int)
    args = parser.parse_args()
    return args.port, args.clients


def launch_server(port: int, max_clients: int):
    def on_available(
            sock: socket.socket,
            server_addr: Addr,
            active_clients: dict[Addr, ClientState],
            request: bytes,
            client_addr: Addr
    ):
        print(f'{client_addr}: {log_request(request)}')

        msg, seqno = acknowledge_msg(request)
        sock.sendto(msg, client_addr)

        filename, f_bytes = prepare_file(request, server_addr)
        client = ClientState(addr=client_addr, seqno=seqno, filename=filename, bytes_left=f_bytes)

        impl(sock, server_addr, {**active_clients, **{client_addr: client}})

    def on_busy(
            sock: socket.socket,
            server_addr: Addr,
            active_clients: dict[Addr, ClientState],
            request: bytes,
            client_addr: Addr
    ):
        print(f'{client_addr}: {log_request(request)}')

        msg, _ = reject_msg(request)
        sock.sendto(msg, client_addr)

        impl(sock, server_addr, active_clients)

    def on_file_content(
            sock: socket.socket,
            server_addr: Addr,
            active_clients: dict[Addr, ClientState],
            request: bytes,
            client_addr: Addr
    ):
        print(f'{client_addr}: {log_request(request)}')

        cur_client = active_clients[client_addr]
        bytes_left = append_to_file(request, client_state=cur_client)

        msg, seqno = acknowledge_msg(request)
        sock.sendto(msg, client_addr)

        if bytes_left == 0:
            print(f'{server_addr}:    Received {cur_client.filename}.')

            impl(
                sock=sock,
                server_addr=server_addr,
                active_clients={a: active_clients[a] for a in active_clients if a != client_addr}
            )
        else:
            upd_client = ClientState(addr=client_addr, seqno=seqno, filename=cur_client.filename, bytes_left=bytes_left)
            impl(sock, server_addr, {**active_clients, **{client_addr: upd_client}})

    def on_illegal_request(
            sock: socket.socket,
            server_addr: Addr,
            active_clients: dict[Addr, ClientState],
            request: bytes,
            client_addr: Addr
    ):
        print(f'{client_addr}: {log_request(request)}')
        print(f'{client_addr}: Illegal request')
        impl(sock, server_addr, active_clients)

    def on_resubmit(
            sock: socket.socket,
            server_addr: Addr,
            active_clients: dict[Addr, ClientState],
            request: bytes,
            client_addr: Addr,
    ):
        print(f'{client_addr}: {log_request(request)}')
        print(f'{client_addr}: Resubmit')

        msg, _ = acknowledge_msg(request)
        sock.sendto(msg, client_addr)
        impl(sock, server_addr, active_clients)

    def impl(
            sock: socket.socket,
            server_addr: Addr,
            active_clients: dict[Addr, ClientState] = {}
    ):
        request, client_addr = sock.recvfrom(BUFFER_SIZE)
        is_client_active = client_addr in active_clients
        nxt_sqn = next_seqno(active_clients[client_addr].seqno) if is_client_active else 0

        req_state = RequestState(
            request_type=parse_request_type(request),
            is_enough_clients=len(active_clients) < max_clients,
            is_client_active=is_client_active,
            is_correct_seqno=nxt_sqn == parse_seqno(request)
        )

        match req_state:
            case RequestState(
                RequestType.START, is_enough_clients=True, is_client_active=False, is_correct_seqno=True
            ): on_available(sock, server_addr, active_clients, request, client_addr)

            case RequestState(
                RequestType.START, is_enough_clients=False, is_client_active=False, is_correct_seqno=_
            ): on_busy(sock, server_addr, active_clients, request, client_addr)

            case RequestState(
                RequestType.START, is_enough_clients=_, is_client_active=True, is_correct_seqno=False
            ): on_resubmit(sock, server_addr, active_clients, request, client_addr)

            case RequestState(
                RequestType.DATA, is_enough_clients=_, is_client_active=True, is_correct_seqno=True
            ): on_file_content(sock, server_addr, active_clients, request, client_addr)

            case RequestState(
                RequestType.DATA, is_enough_clients=_, is_client_active=_, is_correct_seqno=False
            ): on_resubmit(sock, server_addr, active_clients, request, client_addr)

            case _:
                on_illegal_request(sock, server_addr, active_clients, request, client_addr)

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        server_addr = (HOST, port)
        sock.bind(server_addr)
        print(f'{server_addr}:    Listening...')

        try:
            impl(sock, server_addr)
        except KeyboardInterrupt:
            print(f'{server_addr}:    Shutting down...')


def prepare_file(request: bytes, server_addr: Addr) -> (str, int):
    req = parse_start_request(request)
    filename = get_or_default(req, 2).decode()
    f_bytes = int(get_or_default(req, 3).decode())

    if path.exists(filename):
        print(f'{server_addr}:    Overwriting file {filename}...')

    open(filename, mode='w').close()
    return filename, f_bytes


def append_to_file(request: bytes, client_state: ClientState) -> int:
    req = parse_data_request(request)
    content = get_or_default(req, 2)
    ap_bytes = len(content)

    with open(client_state.filename, mode='ab') as file:
        file.write(content)

    return max(client_state.bytes_left - ap_bytes, 0)


def reject_msg(request: bytes) -> (bytes, int):
    seqno = parse_seqno(request)
    return f'n|{next_seqno(seqno)}'.encode(), seqno


def acknowledge_msg(request: bytes) -> (bytes, int):
    seqno = parse_seqno(request)
    return f'a|{next_seqno(seqno)}'.encode(), seqno


def next_seqno(seqno: int) -> int:
    return (seqno + 1) % 2


def parse_start_request(data: bytes) -> list[bytes]:
    return data.split(b'|')


def parse_data_request(request: bytes) -> list[bytes]:
    content = request.split(b'|', maxsplit=2)
    data = request.removeprefix(b'|'.join(content))
    return content + list(data)


def log_request(request: bytes) -> str:
    def log_start_request() -> str:
        req = parse_start_request(request)
        content = "|".join(map(lambda x: x.decode(), req[:-1]))
        return f'{content}|{req[-1].decode()}'

    def log_data_request() -> str:
        req = parse_data_request(request)
        content = "|".join(map(lambda x: x.decode(), req[:-1]))
        return f'{content}|{len(req[-1])}'

    if is_legal_data_request(request):
        return log_data_request()
    return log_start_request()


def parse_request_type(request: bytes) -> RequestType:
    req = parse_start_request(request)

    match get_or_default(req, 0):
        case b's':
            return RequestType.START
        case b'd':
            return RequestType.DATA
        case _:
            return RequestType.ILLEGAL


def parse_seqno(request: bytes) -> int:
    req = parse_start_request(request)
    return int(get_or_default(req, 1))


def is_legal_start_request(request: bytes) -> bool:
    req = parse_start_request(request)
    return req[0] == b's'


def is_illegal_start_request(request: bytes) -> bool:
    return not is_legal_start_request(request)


def is_legal_data_request(request: bytes) -> bool:
    req = parse_data_request(request)
    return req[0] == b'd'


def is_illegal_data_request(request: bytes) -> bool:
    return not is_legal_data_request(request)


def get_or_default(arr: list, index: int, default=None):
    return next(iter(arr[index:]), default)


def main():
    port, max_clients = parse_port_clients()
    launch_server(port, max_clients)


if __name__ == "__main__":
    main()
