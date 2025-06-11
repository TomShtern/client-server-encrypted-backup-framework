#!/usr/bin/env python3
"""
Simple Python test client for the Encrypted Backup Framework
Tests registration, key exchange, and file upload functionality
"""

import socket
import json
import os
import sys
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP, AES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad
import base64

class BackupClient:
    def __init__(self, server_host='127.0.0.1', server_port=1256):
        self.server_host = server_host
        self.server_port = server_port
        self.socket = None
        self.username = None
        self.user_id = None
        self.private_key = None
        self.public_key = None
        self.server_public_key = None
        
    def connect(self):
        """Connect to the backup server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.server_host, self.server_port))
            print(f"Connected to server at {self.server_host}:{self.server_port}")
            return True
        except Exception as e:
            print(f"Failed to connect: {e}")
            return False
            
    def disconnect(self):
        """Disconnect from the server"""
        if self.socket:
            self.socket.close()
            self.socket = None
            print("Disconnected from server")
            
    def send_message(self, message):
        """Send a message to the server"""
        try:
            message_str = json.dumps(message)
            message_bytes = message_str.encode('utf-8')
            # Send length first, then message
            length = len(message_bytes)
            self.socket.send(length.to_bytes(4, byteorder='big'))
            self.socket.send(message_bytes)
            return True
        except Exception as e:
            print(f"Error sending message: {e}")
            return False
            
    def receive_message(self):
        """Receive a message from the server"""
        try:
            # Receive length first
            length_bytes = self.socket.recv(4)
            if len(length_bytes) != 4:
                return None
            length = int.from_bytes(length_bytes, byteorder='big')
            
            # Receive the actual message
            message_bytes = b''
            while len(message_bytes) < length:
                chunk = self.socket.recv(length - len(message_bytes))
                if not chunk:
                    return None
                message_bytes += chunk
                
            message_str = message_bytes.decode('utf-8')
            return json.loads(message_str)
        except Exception as e:
            print(f"Error receiving message: {e}")
            return None
            
    def generate_keys(self):
        """Generate RSA key pair"""
        try:
            key = RSA.generate(2048)
            self.private_key = key
            self.public_key = key.publickey()
            print("Generated RSA key pair")
            return True
        except Exception as e:
            print(f"Error generating keys: {e}")
            return False
            
    def register_user(self, username):
        """Register a new user with the server"""
        self.username = username
        
        if not self.generate_keys():
            return False
            
        # Export public key
        public_key_pem = self.public_key.export_key().decode('utf-8')
        
        # Send registration request
        register_msg = {
            "type": "register",
            "username": username,
            "public_key": public_key_pem
        }
        
        if not self.send_message(register_msg):
            return False
            
        # Receive response
        response = self.receive_message()
        if not response:
            return False
            
        if response.get("status") == "success":
            self.user_id = response.get("user_id")
            print(f"Registration successful! User ID: {self.user_id}")
            return True
        else:
            print(f"Registration failed: {response.get('message', 'Unknown error')}")
            return False
            
    def request_server_key(self):
        """Request the server's public key"""
        key_request = {
            "type": "get_server_key"
        }
        
        if not self.send_message(key_request):
            return False
            
        response = self.receive_message()
        if not response:
            return False
            
        if response.get("status") == "success":
            server_key_pem = response.get("public_key")
            self.server_public_key = RSA.import_key(server_key_pem.encode('utf-8'))
            print("Received server public key")
            return True
        else:
            print(f"Failed to get server key: {response.get('message', 'Unknown error')}")
            return False
            
    def upload_file(self, file_path):
        """Upload a file to the server"""
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return False
            
        if not self.server_public_key:
            print("Server public key not available")
            return False
            
        try:
            # Read file content
            with open(file_path, 'rb') as f:
                file_content = f.read()
                
            filename = os.path.basename(file_path)
            print(f"Uploading file: {filename} ({len(file_content)} bytes)")
            
            # Generate AES key for file encryption
            aes_key = get_random_bytes(32)  # 256-bit AES key
            
            # Encrypt file content with AES
            cipher_aes = AES.new(aes_key, AES.MODE_CBC)
            file_content_padded = pad(file_content, AES.block_size)
            encrypted_content = cipher_aes.encrypt(file_content_padded)
            
            # Encrypt AES key with server's RSA public key
            cipher_rsa = PKCS1_OAEP.new(self.server_public_key)
            encrypted_aes_key = cipher_rsa.encrypt(aes_key)
            
            # Prepare upload message
            upload_msg = {
                "type": "upload",
                "user_id": self.user_id,
                "filename": filename,
                "encrypted_key": base64.b64encode(encrypted_aes_key).decode('utf-8'),
                "iv": base64.b64encode(cipher_aes.iv).decode('utf-8'),
                "encrypted_content": base64.b64encode(encrypted_content).decode('utf-8')
            }
            
            if not self.send_message(upload_msg):
                return False
                
            # Receive response
            response = self.receive_message()
            if not response:
                return False
                
            if response.get("status") == "success":
                print(f"File uploaded successfully! File ID: {response.get('file_id')}")
                return True
            else:
                print(f"Upload failed: {response.get('message', 'Unknown error')}")
                return False
                
        except Exception as e:
            print(f"Error uploading file: {e}")
            return False
            
    def list_files(self):
        """List files for the current user"""
        list_msg = {
            "type": "list",
            "user_id": self.user_id
        }
        
        if not self.send_message(list_msg):
            return False
            
        response = self.receive_message()
        if not response:
            return False
            
        if response.get("status") == "success":
            files = response.get("files", [])
            print(f"\nFiles for user {self.username} (ID: {self.user_id}):")
            if files:
                for file_info in files:
                    print(f"  - {file_info['filename']} (ID: {file_info['file_id']}, Size: {file_info['size']} bytes)")
            else:
                print("  No files found")
            return True
        else:
            print(f"Failed to list files: {response.get('message', 'Unknown error')}")
            return False

def main():
    """Main test function"""
    print("=== Encrypted Backup Framework - Test Client ===\n")
    
    # Create test file if it doesn't exist
    test_file = "test_upload.txt"
    if not os.path.exists(test_file):
        with open(test_file, 'w') as f:
            f.write("This is a test file for the encrypted backup system.\n")
            f.write("It contains some sample data to verify upload functionality.\n")
            f.write("Generated by test_client.py\n")
    
    client = BackupClient()
    
    try:
        # Connect to server
        if not client.connect():
            return False
            
        # Test user registration
        username = f"test_user_{get_random_bytes(4).hex()}"
        if not client.register_user(username):
            return False
            
        # Get server public key
        if not client.request_server_key():
            return False
            
        # Upload test file
        if not client.upload_file(test_file):
            return False
            
        # List files
        if not client.list_files():
            return False
            
        print("\n=== All tests completed successfully! ===")
        return True
        
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        return False
    except Exception as e:
        print(f"Test failed with error: {e}")
        return False
    finally:
        client.disconnect()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
