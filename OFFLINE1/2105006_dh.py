import enum
import random
from sys import argv
import time
import sys
import hashlib


class PrimeGenerator:
    def __init__(self, seed=42):
        self.set_seed(seed)

    def set_seed(self, seed=42):
        random.seed(seed)

    def get_n_bit_odd_number(self, n):
        return random.getrandbits(n - 1) << 1 | (1 << (n - 1)) | 1

    def generate_prime(self, bit_length):
        while True:
            q = self.get_n_bit_odd_number(bit_length - 1)
            if self.is_prime(q):
                n = 2 * q + 1
                if self.is_prime(n):
                    return n

    def is_prime(self, n, k=20):
        if n == 2 or n == 3:
            return True
        if n % 2 == 0:
            return False
        r = 0
        d = n - 1
        while d % 2 == 0:
            d = d // 2
            r += 1
        for _ in range(k):
            if not self.miller_test(n, d, r):
                return False
        return True

    def miller_test(self, n, d, r):
        a = random.randint(2, n - 2)
        x = pow(a, d, n)
        if x == 1 or x == n - 1:
            return True
        for _ in range(r - 1):
            x = (x * x) % n
            if x == 1:
                return False
            if x == n - 1:
                return True
        return False


class DHParameters:
    def __init__(self, bit_length):
        self.bit_length = bit_length

    def generate(self, seed=42):
        prime_gen = PrimeGenerator(seed)
        self.p = prime_gen.generate_prime(self.bit_length)
        self.g = self.generator(self.p)

    def get_bit_length(self):
        return self.bit_length

    def get_generator(self):
        return self.g

    def set_generator(self, g):
        self.g = g

    def get_prime(self):
        return self.p

    def set_prime(self, p):
        self.p = p

    def generator(self, p):
        options = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31]
        for option in options:
            if option > 1 and option < p and self.valid_generator(option, p):
                return option
        while True:
            option = random.randint(2, p - 1)
            if self.valid_generator(option, p):
                return option

    def valid_generator(self, g, p):
        return pow(g, (p - 1) // 2, p) != 1 and pow(g, 2, p) != 1


class DH:
    def __init__(self, name, params):
        self.name = name
        self.params = params

    def get_public_key(self):
        return self.public_key

    def get_shared_secret_string(self):
        return bin(self.shared_secret)[2:]

    def derive_aes_key(self):
        key_bytes = self.params.get_bit_length() // 8
        total_bytes = (self.shared_secret.bit_length() + 7) // 8
        raw = self.shared_secret.to_bytes(
            max(total_bytes, 1),
            byteorder="big",
        )
        digest = hashlib.sha256(raw).digest()
        key_slice = digest[:key_bytes]

        return key_slice.decode("latin-1")

    def set_other_public_key(self, other_public_key):
        self.other_public_key = other_public_key

    def generate_keys(self):
        self.private_key = self.generate_private_key(self.params.get_bit_length())
        self.public_key = self.generate_public_key(
            self.private_key, self.params.get_generator(), self.params.get_prime()
        )

    def generate_private_key(self, bit_length):
        private_key_length = bit_length + random.randint(0, 20)
        return random.getrandbits(private_key_length)

    def generate_public_key(self, private_key, g, p):
        return pow(g, private_key, p)

    def generate_shared_secret(self, other_public_key):
        self.other_public_key = other_public_key
        self.shared_secret = pow(
            other_public_key, self.private_key, self.params.get_prime()
        )


def print_table(results):
    header = f"{'k':<8}{'A':<15}{'B':<15}{'shared key s':<15}"
    print(header)
    print("-" * len(header))
    for row in results:
        print(
            f"{row['k']:<8}"
            f"{row['time_A']:<15.4f}"
            f"{row['time_B']:<15.4f}"
            f"{row['time_s']:<15.4f}"
        )


if __name__ == "__main__":
    seed = 42
    random.seed(seed)
    round = int(sys.argv[1]) if len(sys.argv) == 2 else 5
    key_sizes = [128, 192, 256]
    a = []
    b = []
    s = []

    header = f"{'k':<8}{'A':<15}{'B':<15}{'shared key s':<15}"
    print(header)
    for key_size in key_sizes:
        temp_a = 0
        temp_b = 0
        temp_s = 0
        for i in range(round):
            params = DHParameters(bit_length=key_size)
            params.generate(seed=random.randint(0, 100))
            t0 = time.perf_counter()
            alice = DH("Alice", params)
            alice.generate_keys()
            t1 = time.perf_counter()
            bob = DH("Bob", params)
            bob.generate_keys()
            t2 = time.perf_counter()
            secret_alice = alice.generate_shared_secret(bob.public_key)
            secret_bob = bob.generate_shared_secret(alice.public_key)
            t3 = time.perf_counter()
            temp_a += t1 - t0
            temp_b += t2 - t1
            temp_s += t3 - t2
        a_str = f"{(temp_a / round) * 1000:.4f} ms"
        b_str = f"{(temp_b / round) * 1000:.4f} ms"
        s_str = f"{(temp_s / round) * 1000:.4f} ms"
        print(f"{key_size:<8}{a_str:<15}{b_str:<15}{s_str:<15}")
