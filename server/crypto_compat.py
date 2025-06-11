"""
Compatibility layer for crypto operations using python3-cryptography
This provides PyCryptodome-compatible interface using the installed cryptography library
"""

try:
    # Try to use PyCryptodome first
    from Crypto.Cipher import AES
    from Crypto.PublicKey import RSA
    from Crypto.Cipher import PKCS1_OAEP
    from Crypto.Util.Padding import pad, unpad
    from Crypto.Random import get_random_bytes
    print("Using PyCryptodome")
    
except ImportError:
    print("PyCryptodome not available, using cryptography library compatibility layer")
    
    # Fallback to cryptography library with compatibility interface
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives import padding, serialization, hashes
    from cryptography.hazmat.primitives.asymmetric import rsa, padding as asym_padding
    from cryptography.hazmat.backends import default_backend
    import os
    
    # Create PyCryptodome-like interface
    class AES:
        BLOCKSIZE = 16
        
        @staticmethod
        def new(key, mode_obj, iv=None):
            return AESCompat(key, mode_obj, iv)
    
    class AESCompat:
        def __init__(self, key, mode_obj, iv=None):
            self.key = key
            self.iv = iv or os.urandom(16)
            
            if hasattr(mode_obj, 'MODE_CBC'):
                # CBC mode
                cipher = Cipher(algorithms.AES(key), modes.CBC(self.iv), backend=default_backend())
                self.encryptor = cipher.encryptor()
                self.decryptor = cipher.decryptor()
            else:
                raise ValueError("Unsupported AES mode")
        
        def encrypt(self, data):
            # Add PKCS7 padding
            padder = padding.PKCS7(128).padder()
            padded_data = padder.update(data) + padder.finalize()
            return self.encryptor.update(padded_data) + self.encryptor.finalize()
        
        def decrypt(self, data):
            decrypted = self.decryptor.update(data) + self.decryptor.finalize()
            # Remove PKCS7 padding
            unpadder = padding.PKCS7(128).unpadder()
            return unpadder.update(decrypted) + unpadder.finalize()
    
    class MODE_CBC:
        pass
    
    class RSA:
        @staticmethod
        def generate(bits):
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=bits,
                backend=default_backend()
            )
            return RSAKeyCompat(private_key)
        
        @staticmethod
        def import_key(data):
            try:
                if isinstance(data, str):
                    data = data.encode()
                private_key = serialization.load_der_private_key(
                    data, password=None, backend=default_backend()
                )
                return RSAKeyCompat(private_key)
            except:
                # Try as public key
                public_key = serialization.load_der_public_key(
                    data, backend=default_backend()
                )
                return RSAKeyCompat(None, public_key)
    
    class RSAKeyCompat:
        def __init__(self, private_key=None, public_key=None):
            self.private_key = private_key
            self.public_key = public_key or (private_key.public_key() if private_key else None)
        
        def encrypt(self, data):
            if isinstance(data, str):
                data = data.encode()
            return self.public_key.encrypt(
                data,
                asym_padding.PKCS1v15()
            )
        
        def decrypt(self, data):
            return self.private_key.decrypt(
                data,
                asym_padding.PKCS1v15()
            )
        
        def export_key(self, format='DER'):
            if format == 'DER':
                return self.private_key.private_key_serialization(
                    encoding=serialization.Encoding.DER,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                )
            else:
                raise ValueError("Unsupported format")
    
    class PKCS1_OAEP:
        def __init__(self, key):
            self.key = key
        
        def encrypt(self, data):
            return self.key.encrypt(data)
        
        def decrypt(self, data):
            return self.key.decrypt(data)
        
        @staticmethod
        def new(key):
            return PKCS1_OAEP(key)
    
    def pad(data, block_size):
        padder = padding.PKCS7(block_size * 8).padder()
        return padder.update(data) + padder.finalize()
    
    def unpad(data, block_size):
        unpadder = padding.PKCS7(block_size * 8).unpadder()
        return unpadder.update(data) + unpadder.finalize()
    
    def get_random_bytes(length):
        return os.urandom(length)
    
    # Set mode constants
    AES.MODE_CBC = MODE_CBC()