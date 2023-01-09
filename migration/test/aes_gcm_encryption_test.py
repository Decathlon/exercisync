from unittest import TestCase
from migration.infrastructure.aes_gcm_encryption import AES_GCM_Engine

class AES_GCM_EngineTest(TestCase):
    
    def test_constant_representation(self):
        # Given
        string_to_encrypt = "test string to encrypt 1234"
        key = b"1234567812345678"
        
        # When
        ae_engine = AES_GCM_Engine(key)
        encrypted_str = ae_engine.encrypt(string_to_encrypt)
        decrypted_str = ae_engine.decrypt(encrypted_str, is_b64=True)

        # Then
        self.assertEqual(string_to_encrypt, decrypted_str)
        