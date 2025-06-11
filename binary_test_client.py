#!/usr/bin/env python3
"""
Binary Protocol Test Client for Encrypted Backup Framework
Uses the correct 23-byte binary protocol format
"""

import socket
import struct
import os
import sys
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP, AES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad
import base64

# Protocol constants (from the C++ code and specification)
CLIENT_VERSION = 3
CLIENT_ID_SIZE = 16

# Request codes
REQ_REGISTER = 1025
REQ_SEND_PUBLIC_KEY = 1026
REQ_RECONNECT = 1027
REQ_SEND_FILE = 1028
REQ_CRC_OK = 1029

# Response codes
RESP_REG_OK = 1600
RESP_REG_FAIL = 1601
RESP_AES_KEY_SENT = 1602
RESP_FILE_RECEIVED_CRC = 1603
RESP_ACK = 1604
RESP_RECONNECT_OK = 1605
RESP_RECONNECT_FAIL = 1606
RESP_GENERIC_SERVER_ERROR = 1607

class BinaryProtocolClient:
    def __init__(self, server_host='127.0.0.1', server_port=1256):
        self.server_host = server_host
        self.server_port = server_port
        self.socket = None
        self.username = None
        self.client_id = bytes(16)  # 16 zero bytes initially
        self.private_key = None
        self.public_key = None
        self.aes_key = None
        
    def connect(self):
        """Connect to the backup server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)
            self.socket.connect((self.server_host, self.server_port))
            print(f"✅ Connected to server at {self.server_host}:{self.server_port}")
            return True
        except Exception as e:
            print(f"❌ Failed to connect: {e}")
            return False
            
    def disconnect(self):
        """Disconnect from the server"""
        if self.socket:
            self.socket.close()
            self.socket = None
            print("🔌 Disconnected from server")
            
    def send_request(self, code, payload=b''):
        """Send a binary protocol request"""
        try:
            # Construct 23-byte header in little-endian format
            header = bytearray(23)
            
            # Client ID (16 bytes) - all zeros for registration
            header[0:16] = self.client_id
            
            # Version (1 byte)
            header[16] = CLIENT_VERSION
            
            # Code (2 bytes, little-endian)
            header[17:19] = struct.pack('<H', code)
            
            # Payload size (4 bytes, little-endian)
            header[19:23] = struct.pack('<I', len(payload))
            
            # Send header
            self.socket.send(header)
            
            # Send payload if any
            if payload:
                self.socket.send(payload)
                
            print(f"📤 Sent request: Code={code}, PayloadSize={len(payload)}")
            return True
            
        except Exception as e:
            print(f"❌ Error sending request: {e}")
            return False
            
    def receive_response(self):
        """Receive a binary protocol response"""
        try:
            # Receive response header (7 bytes: version + code + payload_size)
            header = self.socket.recv(7)
            if len(header) != 7:
                print(f"❌ Invalid response header length: {len(header)}")
                return None, None
                
            # Parse header
            version = header[0]
            code = struct.unpack('<H', header[1:3])[0]
            payload_size = struct.unpack('<I', header[3:7])[0]
            
            print(f"📥 Response: Version={version}, Code={code}, PayloadSize={payload_size}")
            
            # Receive payload if any
            payload = b''
            if payload_size > 0:
                payload = self.socket.recv(payload_size)
                if len(payload) != payload_size:
                    print(f"❌ Incomplete payload: expected {payload_size}, got {len(payload)}")
                    return None, None
                    
            return code, payload
            
        except Exception as e:
            print(f"❌ Error receiving response: {e}")
            return None, None
            
    def generate_keys(self):
        """Generate RSA key pair"""
        try:
            key = RSA.generate(1024)  # 1024-bit as specified
            self.private_key = key
            self.public_key = key.publickey()
            print("🔑 Generated 1024-bit RSA key pair")
            return True
        except Exception as e:
            print(f"❌ Error generating keys: {e}")
            return False
            
    def register_user(self, username):
        """Register a new user with the server"""
        self.username = username
        
        # Prepare payload: 255-byte username field, null-terminated
        payload = bytearray(255)
        username_bytes = username.encode('utf-8')
        if len(username_bytes) > 254:  # Leave room for null terminator
            print(f"❌ Username too long: {len(username_bytes)} bytes")
            return False
            
        payload[:len(username_bytes)] = username_bytes
        # Rest remains zero (null-terminated)
        
        # Send registration request
        if not self.send_request(REQ_REGISTER, payload):
            return False
            
        # Receive response
        code, response_payload = self.receive_response()
        if code is None:
            return False
            
        if code == RESP_REG_OK:
            if len(response_payload) >= 16:
                self.client_id = response_payload[:16]
                print(f"✅ Registration successful!")
                print(f"   Client ID: {self.client_id.hex()}")
                return True
            else:
                print(f"❌ Invalid registration response payload size: {len(response_payload)}")
                return False
        else:
            print(f"❌ Registration failed with code: {code}")
            return False
            
    def send_public_key(self):
        """Send public key to server"""
        if not self.generate_keys():
            return False
            
        try:
            # Export public key in DER format
            public_key_der = self.public_key.export_key(format='DER')
            print(f"🔑 Public key DER size: {len(public_key_der)} bytes")
            
            # Prepare payload: 255-byte name field + DER key
            payload = bytearray(255)
            username_bytes = self.username.encode('utf-8')
            payload[:len(username_bytes)] = username_bytes
            payload.extend(public_key_der)
            
            # Send public key request
            if not self.send_request(REQ_SEND_PUBLIC_KEY, payload):
                return False
                
            # Receive response
            code, response_payload = self.receive_response()
            if code is None:
                return False
                
            if code == RESP_AES_KEY_SENT:
                print(f"✅ Public key accepted! Received AES key (encrypted)")
                print(f"   Encrypted AES key size: {len(response_payload)} bytes")
                
                # Decrypt AES key with our private key
                cipher_rsa = PKCS1_OAEP.new(self.private_key)
                self.aes_key = cipher_rsa.decrypt(response_payload)
                print(f"🔓 Decrypted AES key: {len(self.aes_key)} bytes")
                return True
            else:
                print(f"❌ Public key rejected with code: {code}")
                return False
                
        except Exception as e:
            print(f"❌ Error sending public key: {e}")
            return False

def main():
    """Main test function"""
    print("🔒 BINARY PROTOCOL TEST CLIENT")
    print("===============================\n")
    
    client = BinaryProtocolClient()
    
    try:
        # Connect to server
        if not client.connect():
            return False
            
        # Test user registration
        username = f"testuser_{get_random_bytes(4).hex()}"
        print(f"🧪 Testing registration with username: {username}")
        
        if not client.register_user(username):
            print("❌ Registration test failed")
            return False
            
        # Test public key exchange
        print(f"🧪 Testing public key exchange...")
        
        if not client.send_public_key():
            print("❌ Public key exchange test failed")
            return False
            
        print("\n✅ ALL TESTS COMPLETED SUCCESSFULLY!")
        print("   - TCP connection established")
        print("   - Binary protocol communication working")
        print("   - User registration successful")
        print("   - RSA key pair generated")
        print("   - Public key exchange successful")
        print("   - AES key received and decrypted")
        
        return True
        
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
        return False
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        client.disconnect()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
