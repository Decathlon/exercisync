from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
import base64

class AES_GCM_Engine:
    key: bytes

    def __init__(self, key):
        self.key = key

    def encrypt(self, plain_str: str) -> bytes:
        my_nonce = get_random_bytes(12)
        cipher = AES.new(self.key, AES.MODE_GCM, my_nonce)
        ciphertext, tag = cipher.encrypt_and_digest(plain_str.encode())

        return base64.b64encode(my_nonce + ciphertext + tag)


    def decrypt(self, encrypted_str, is_b64=False):
        if is_b64: 
            local_encrypted_str_with_nonce = base64.b64decode(encrypted_str)
        else:
            local_encrypted_str_with_nonce = encrypted_str

        nonce = local_encrypted_str_with_nonce[0:12]
        local_encrypted_str = local_encrypted_str_with_nonce[12:]

        cipher = AES.new(self.key, AES.MODE_GCM, nonce)
        newplain_with_tag = cipher.decrypt(local_encrypted_str)

        return newplain_with_tag[:-16]