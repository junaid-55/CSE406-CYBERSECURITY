import socket
import threading
import pickle
import sys
import struct
import importlib.util
import base64
import os

spec1 = importlib.util.spec_from_file_location("dh_module", "2105006_dh.py")
spec2 = importlib.util.spec_from_file_location("aes_module", "2105006_aes.py")
dh_module = importlib.util.module_from_spec(spec1)
aes_module = importlib.util.module_from_spec(spec2)
spec1.loader.exec_module(dh_module)
spec2.loader.exec_module(aes_module)

DHParameters = dh_module.DHParameters
DH = dh_module.DH
AES = aes_module.AES


class Peer:
    def __init__(self, host, port, name):
        self.host = host
        self.port = port
        self.name = name
        self.peers = {}  # {(ip, port): socket}
        self.peer_details = {}

    def set_peer_detail(self, name, ip, port):
        self.peer_details[name] = (ip, port)

    def get_peer_details(self, name):
        return self.peer_details[name]

    def get_name(self):
        return self.name

    def set_dh_params(self, bit_length):
        self.params = DHParameters(bit_length)
        self.params.generate()
        self.dh = DH(self.name, self.params)
        self.dh.generate_keys()

    def get_negotiating_params_from_sender(self):
        return [
            self.params.get_prime(),
            self.params.get_generator(),
            self.dh.get_public_key(),
        ]

    def start(self):
        listener_thread = threading.Thread(target=self._listen, daemon=True)
        listener_thread.start()

    def _listen(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((self.host, self.port))
        server_socket.listen()
        print(f"Listening on {self.host}:{self.port}")

        while True:
            conn, addr = server_socket.accept()
            print(f"Incoming connection from {addr}")
            threading.Thread(
                target=self._handle_conn, args=(conn, addr), daemon=True
            ).start()

    def _handle_conn(self, conn, addr):
        with conn:
            while True:
                try:
                    msg = self.recv_msg(conn)
                except ConnectionError:
                    print(f"{addr} disconnected")
                    break
                self.process_message(conn, msg)

    def process_message(self, sock, msg):
        print(f"Recieved message: {msg}")
        type = msg["type"]
        data = msg["data"]
        sender = msg["sender"]
        is_encrypted = msg["is_encrypted"]

        if type == "dh_init":
            p, g, public_key, mode = data
            self.mode = mode
            self.params = DHParameters(p.bit_length())
            self.params.set_generator(g)
            self.params.set_prime(p)
            self.dh = DH(self.name, self.params)
            self.dh.set_other_public_key(public_key)
            self.dh.generate_keys()
            reply = {
                "type": "dh_init_reply",
                "sender": self.name,
                "data": [self.dh.get_public_key(), self.mode],
                "is_encrypted": False,
            }
            self.send_msg(
                self.peer_details[sender][0], self.peer_details[sender][1], reply
            )
            self.dh.generate_shared_secret(public_key)
            self.aes = AES(
                self.dh.derive_aes_key(),
                self.mode,
                len(self.dh.derive_aes_key()) * 8,
            )
        elif type == "dh_init_reply":
            public_key, mode = data
            self.mode = mode
            self.dh.generate_shared_secret(public_key)
            self.aes = AES(
                self.dh.derive_aes_key(),
                self.mode,
                len(self.dh.derive_aes_key()) * 8,
            )
        elif type == "hello":
            self.peer_details[sender] = data
            self.peers[data] = sock
        elif type == "message":
            if is_encrypted:
                data = self.aes.decrypt_message(data)
            print(f"Message from: {sender}")
            print(f'"{data}"')
        elif msg["type"] == "file":
            encrypted_payload = msg["data"]["payload"]
            filename = msg["data"]["filename"]

            b64_str = self.aes.decrypt_message(encrypted_payload)
            file_bytes = base64.b64decode(b64_str)

            save_dir = user_name
            os.makedirs(save_dir, exist_ok=True)

            save_path = os.path.join(save_dir, filename)
            with open(save_path, "wb") as f:
                f.write(file_bytes)
            print(f"Received file from {msg['sender']}: saved to {save_path}")

    def connect_to(self, peer_host, peer_port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((peer_host, peer_port))
        self.peers[(peer_host, peer_port)] = sock
        threading.Thread(
            target=self._handle_conn, args=(sock, (peer_host, peer_port)), daemon=True
        ).start()
        print(f"Connected to {peer_host}:{peer_port}")

    def get_encrypted_msg(self, msg):
        return self.aes.encrypt_message(msg)

    def send_msg(self, peer_addr, peer_port, message):
        payload = pickle.dumps(message)
        length = struct.pack(">I", len(payload))
        sock = self.peers.get((peer_addr, peer_port))
        if sock:
            sock.sendall(length + payload)
        else:
            print("Not connected to that peer")

    def recv_msg(self, sock):
        raw_len = self._recv_exact(sock, 4)
        msg_len = struct.unpack(">I", raw_len)[0]
        payload = self._recv_exact(sock, msg_len)
        return pickle.loads(payload)

    def _recv_exact(self, sock, n):
        buf = b""
        while len(buf) < n:
            chunk = sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("Socket closed before receiving expected data")
            buf += chunk
        return buf


if __name__ == "__main__":
    addr = "127.0.0.1"
    user_name = sys.argv[1]
    users = {"ALICE": 5000, "BOB": 5001}
    aes = None
    if users[user_name] is None:
        print("Invalid username!!!")
        sys.exit(0)
    port = users[user_name]
    p = Peer(addr, port, user_name)
    p.start()
    while True:
        cmd = input("> ")
        if cmd.startswith("connect"):
            _, name, mode, raw_len = cmd.split()
            bit_length = int(raw_len)
            if p.get_name() == name:
                print("You cannot connect with yourself!!!")
                continue
            p.connect_to(addr, users[name])
            sent_msg = {
                "type": "hello",
                "sender": user_name,
                "data": (addr, port),
                "is_encrypted": False,
            }
            p.send_msg(addr, users[name], sent_msg)
            p.set_dh_params(bit_length)
            msg = p.get_negotiating_params_from_sender()
            msg.append(mode)
            sent_msg = {
                "type": "dh_init",
                "sender": user_name,
                "data": msg,
                "is_encrypted": False,
            }
            p.send_msg(addr, users[name], sent_msg)
        elif cmd.startswith("send"):
            _, reciever_name, *msg_parts = cmd.split()
            msg = " ".join(msg_parts)
            if users[reciever_name] is None:
                print("User not Found!!!")
                continue
            encrptd_msg = p.get_encrypted_msg(msg)
            sent_msg = {
                "type": "message",
                "sender": user_name,
                "data": encrptd_msg,
                "is_encrypted": True,
            }
            p.send_msg(addr, users[reciever_name], sent_msg)
        elif cmd.startswith("file"):
            _, reciever_name, *filename_parts = cmd.split()
            filename = " ".join(filename_parts)

            if reciever_name not in users:
                print("User not Found!!!")
                continue

            if not os.path.isfile(filename):
                print(f"File not found: {filename}")
                continue

            with open(filename, "rb") as f:
                file_bytes = f.read()

            b64_str = base64.b64encode(file_bytes).decode("ascii")
            encrypted_payload = p.get_encrypted_msg(b64_str)

            sent_msg = {
                "type": "file",
                "sender": user_name,
                "data": {
                    "filename": os.path.basename(filename),
                    "payload": encrypted_payload,
                },
                "is_encrypted": True,
            }
            p.send_msg(addr, users[reciever_name], sent_msg)
            print(f"Sent file: {filename}")
