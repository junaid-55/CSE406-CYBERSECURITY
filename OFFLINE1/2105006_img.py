import sys
import os
import struct
import importlib.util

spec1 = importlib.util.spec_from_file_location("aes_module", "2105006_aes.py")
aes_module = importlib.util.module_from_spec(spec1)
spec1.loader.exec_module(aes_module)

AES = aes_module.AES


def split_filename(path):
    dir_name, base = os.path.split(path)
    name, ext = os.path.splitext(base)
    return name, ext


def encrypt_bytes(raw, aes):
    """Encrypt raw bytes without PKCS7 padding growth — zero-pad to block size, truncate back."""
    pad_len = (-len(raw)) % 16
    padded = raw + bytes(pad_len)
    text_form = padded.decode("latin-1")
    cipher_hex = aes.encrypt_message(text_form)  # no-padding variant, see note below
    cipher_bytes = bytes.fromhex(cipher_hex)
    return cipher_bytes[: len(raw)]


def process_file(path, name, ext, mode):
    with open(path, "rb") as f:
        raw = f.read()

    key = "BUET CSE20 Batch"  # replace with your actual key source
    aes = AES(key, mode=mode)

    if ext.lower() == ".bmp":
        pixel_offset = struct.unpack("<I", raw[10:14])[0]
        header = raw[:pixel_offset]
        pixel_data = raw[pixel_offset:]
        encrypted_pixels = encrypt_bytes(pixel_data, aes)
        output_bytes = header + encrypted_pixels
    else:
        output_bytes = encrypt_bytes(raw, aes)

    return output_bytes


if __name__ == "__main__":
    input_path = sys.argv[1]
    name, ext = split_filename(input_path)

    output_dir = "CIPHER"
    os.makedirs(output_dir, exist_ok=True)

    for mode in ["ECB", "CBC"]:
        encrypted = process_file(input_path, name, ext, mode)
        out_path = os.path.join(output_dir, f"{name}_ciphered_{mode.lower()}{ext}")
        with open(out_path, "wb") as f:
            f.write(encrypted)
        print(f"Wrote {out_path}")
