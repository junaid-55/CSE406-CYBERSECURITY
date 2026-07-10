from BitVector import BitVector
from aes_helpers import Sbox, InvSbox, Rcon, Mixer, InvMixer
from typing import List, Optional, final
import time


class AES:
    def __init__(self, key, mode="ECB", key_size=128):
        self.org_key = key
        self.key = self.add_padding(key, key_size // 8, False)
        t0 = time.perf_counter() * 1000
        self.expanded_key = self.key_expansion(BitVector(textstring=self.key))
        t1 = time.perf_counter() * 1000
        self.key_schedule_time = t1 - t0
        self.mode = mode

    def get_original_key(self):
        return self.org_key

    def get_padded_key(self):
        return self.key

    def get_key_chedule_time_ms(self):
        return self.key_schedule_time

    def add_padding(self, text, block_size=16, is_text=True):
        if not is_text:
            if len(text) < block_size:
                num_gap = block_size - len(text)
                text += num_gap * chr(num_gap)
            return text[:block_size]
        num_gap = block_size - len(text) % block_size
        if (len(text) >= block_size or num_gap % block_size == 0) and not is_text:
            return text[:block_size]
        # have to fix the issue later
        # hex_pad_value = f"{num_gap:02x}"
        text += num_gap * chr(num_gap)
        return text

    def forward_round(self, msg, round_num, is_last):
        state: List[List[Optional[BitVector]]] = [
            [None for _ in range(4)] for _ in range(4)
        ]
        for i in range(16):
            temp = msg[i * 8 : (i + 1) * 8]
            state[i % 4][i // 4] = BitVector(intVal=Sbox[temp.int_val()], size=8)
        for i in range(4):
            state[i] = state[i][i:] + state[i][:i]
        new_state: List[List[Optional[BitVector]]] = [
            [None for _ in range(4)] for _ in range(4)
        ]
        if not is_last:
            _AES_MODULUS = BitVector(bitstring="100011011")
            for column in range(4):
                for i in range(4):
                    mixed_val = BitVector(intVal=0, size=8)
                    for j in range(4):
                        mixer_val = BitVector(intVal=Mixer[i][j], size=8)
                        product = mixer_val.gf_multiply_modular(
                            state[j][column], _AES_MODULUS, 8
                        )
                        mixed_val ^= product
                    new_state[i][column] = mixed_val
            state = new_state
        new_msg = BitVector(size=0)
        for column in range(4):
            for row in range(4):
                new_msg += state[row][column]
        return new_msg ^ self.expanded_key[round_num]

    def backward_round(self, msg, round_num, is_last):
        state: List[List[Optional[BitVector]]] = [
            [None for _ in range(4)] for _ in range(4)
        ]

        for i in range(16):
            temp = msg[i * 8 : (i + 1) * 8]
            state[i % 4][i // 4] = BitVector(intVal=InvSbox[temp.int_val()], size=8)

        for r in range(4):
            shift = (4 - r) % 4
            state[r] = state[r][shift:] + state[r][:shift]

        count = 0
        for column in range(4):
            for row in range(4):
                state[row][column] ^= self.expanded_key[round_num][count : count + 8]
                count += 8

        new_state: List[List[Optional[BitVector]]] = [
            [None for _ in range(4)] for _ in range(4)
        ]
        if not is_last:
            _AES_MODULUS = BitVector(bitstring="100011011")
            for column in range(4):
                for i in range(4):
                    mixed_val = BitVector(intVal=0, size=8)
                    for j in range(4):
                        mixer_val = BitVector(intVal=InvMixer[i][j], size=8)
                        product = mixer_val.gf_multiply_modular(
                            state[j][column], _AES_MODULUS, 8
                        )
                        mixed_val ^= product
                    new_state[i][column] = mixed_val
            state = new_state
        new_msg = BitVector(size=0)
        for column in range(4):
            for row in range(4):
                new_msg += state[row][column]
        return new_msg

    def cipher(self, msg):
        msg = msg ^ self.expanded_key[0]
        round = len(self.expanded_key) - 1
        for i in range(1, round):
            msg = self.forward_round(msg, i, False)
        msg = self.forward_round(msg, round, True)
        return msg

    def decipher(self, cipher_text):
        msg = BitVector(hexstring=cipher_text)
        msg ^= self.expanded_key[-1]
        round = len(self.expanded_key) - 1
        for i in range(1, round):
            msg = self.backward_round(msg, round - i, False)
        msg = self.backward_round(msg, 0, True)
        return msg

    def encrypt_message(self, plain_text):
        padded_text = self.add_padding(plain_text, 16, True)
        num_blocks = len(padded_text) // 16
        cipher_text = ""
        iv = BitVector(intVal=0, size=128)
        if self.mode == "CBC":
            iv = BitVector(size=128).gen_random_bits(128)
            cipher_text += iv.get_bitvector_in_hex()
        for i in range(num_blocks):
            current_text = BitVector(textstring=padded_text[i * 16 : (i + 1) * 16])
            current_cipher = self.cipher(current_text ^ iv)
            if self.mode == "CBC":
                iv = current_cipher
            cipher_text += current_cipher.get_bitvector_in_hex()
        return cipher_text

    def decrypt_message(self, cipher_text, return_padded=False):
        iv = BitVector(intVal=0, size=128)
        if self.mode == "CBC":
            iv = BitVector(hexstring=cipher_text[0:32])
            cipher_text = cipher_text[32:]
        num_blocks = len(cipher_text) // 32
        deciphered_hex = ""
        for i in range(num_blocks):
            deciphered_bits = self.decipher(cipher_text[i * 32 : (i + 1) * 32])
            deciphered_hex += (deciphered_bits ^ iv).get_bitvector_in_hex()
            if self.mode == "CBC":
                iv = BitVector(hexstring=cipher_text[i * 32 : (i + 1) * 32])
        deciphered_text = bytes.fromhex(deciphered_hex).decode("utf-8")
        if return_padded:
            return deciphered_text
        pad_len = ord(deciphered_text[-1])
        clean_text = deciphered_text[:-pad_len]
        return clean_text

    def key_expansion(self, key):
        expanded_key = []
        words = []
        words_in_key = key.size // 32
        round = words_in_key + 6
        for i in range(words_in_key):
            words.append(key[i * 32 : i * 32 + 32])

        for i in range(words_in_key, (round + 1) * 4):
            temp = words[i - 1]
            if i % words_in_key == 0:
                temp = temp[8:32] + temp[0:8]
                for j in range(4):
                    byte_val = temp[j * 8 : (j + 1) * 8].int_val()
                    temp[j * 8 : (j + 1) * 8] = BitVector(intVal=Sbox[byte_val], size=8)
                temp[0:8] = temp[0:8] ^ BitVector(
                    intVal=Rcon[i // words_in_key], size=8
                )
            elif words_in_key == 8 and i % words_in_key == 4:
                temp = temp.deep_copy()
                for j in range(4):
                    byte_val = temp[j * 8 : (j + 1) * 8].int_val()
                    temp[j * 8 : (j + 1) * 8] = BitVector(intVal=Sbox[byte_val], size=8)

            temp = words[i - words_in_key] ^ temp
            words.append(temp)

        for i in range(len(words)):
            if i % 4 == 0:
                bv = BitVector(size=0)
                expanded_key.append(bv)
            expanded_key[len(expanded_key) - 1] = (
                expanded_key[len(expanded_key) - 1] + words[i]
            )
        return expanded_key


def hex_string(text):
    return " ".join(f"{ord(c):02x}" for c in text)


if __name__ == "__main__":
    key = input("Enter key: ")
    mode = input("Enter Mode (CBC / ECB): ")
    key_size = int(input("Enter key size ( 128 / 192 / 256): "))
    str = input("Enter plain text: ")
    aes = AES(key, mode, key_size)

    print(f"---------------------- AES / {mode} ----------------------")
    print("\nKey:")
    print(f"In ASCII: {aes.get_original_key()}")
    print(f"In HEX: {hex_string(aes.get_original_key())}")
    print(f"In ASCII (After padding): {aes.get_padded_key()}")
    print(f"In HEX(After padding: {hex_string(aes.get_padded_key())}")

    print("\nPlaintext:")
    print(f"In ASCII: {str}")
    print(f"In HEX: {hex_string(str)}")
    print(f"In ASCII (After padding): {aes.add_padding(str)}")
    print(f"In HEX(After padding: {repr(hex_string(aes.add_padding(str)))}")

    print("\nCiphered text:")

    t0 = time.perf_counter() * 1000
    cipher = aes.encrypt_message(str)
    t1 = time.perf_counter() * 1000

    ascii_str = bytes.fromhex(cipher).decode("latin-1")
    cipher_hex = hex_string(ascii_str)
    if mode == "CBC":
        print("(IV is the first 16 bytes, followed by the actual cipher text)")
    print(f"In HEX: {cipher_hex}")
    print(f"In ASCII: {repr(ascii_str)}")

    print("\nDeciphered text:")
    print("Before Unpadding:")

    t2 = time.perf_counter() * 1000
    final_text_padded = aes.decrypt_message(cipher, True)
    t3 = time.perf_counter() * 1000

    print(f"In ASCII: {final_text_padded}")
    print(f"In HEX: {hex_string(final_text_padded)}")
    print("After Unpadding:")
    final_text = aes.decrypt_message(cipher)
    print(f"In ASCII: {final_text}")
    print(f"In HEX: {hex_string(final_text)}")

    print("\nExecution time details:")
    print(f"Key Schedule Time: {aes.get_key_chedule_time_ms()} ms")
    print(f"Encryption Time  : {t1 - t0} ms")
    print(f"Decryption Time  :{t3 - t2} ms")
