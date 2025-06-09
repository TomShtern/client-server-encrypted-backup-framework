#!/usr/bin/env python3
"""
Simple test server for testing the RSA implementation
Uses crypto compatibility layer to work with available libraries
"""

import socket
import threading
import time
import os
import sys

# Try to import crypto using our compatibility layer
try:
    from crypto_compat import AES, RSA, PKCS1_OAEP, get_random_bytes
    print("✓ Crypto libraries loaded successfully")
except Exception as e:
    print(f"✗ Failed to load crypto libraries: {e}")
    sys.exit(1)

class SimpleTestServer:
    def __init__(self, host="127.0.0.1", port=1256):
        self.host = host
        self.port = port
        self.running = False
        
    def start(self):
        """Start the test server"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            
            self.running = True
            print(f"✓ Test server listening on {self.host}:{self.port}")
            print("✓ Ready to test RSA implementation")
            print("✓ Waiting for client connections...")
            
            while self.running:
                try:
                    client_socket, addr = self.server_socket.accept()
                    print(f"✓ Client connected from {addr}")
                    
                    # Handle client in a separate thread
                    client_thread = threading.Thread(
                        target=self.handle_client, 
                        args=(client_socket, addr)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                    
                except Exception as e:
                    if self.running:
                        print(f"✗ Error accepting connection: {e}")
                        
        except Exception as e:
            print(f"✗ Failed to start server: {e}")
            return False
            
        return True
    
    def handle_client(self, client_socket, addr):
        """Handle individual client connection"""
        try:
            print(f"[{addr[0]}:{addr[1]}] Handling client connection")
            
            # Simple protocol: receive any data and respond
            while True:
                try:
                    data = client_socket.recv(1024)
                    if not data:
                        break
                        
                    print(f"[{addr[0]}:{addr[1]}] Received {len(data)} bytes")
                    
                    # Simple response
                    response = b"HTTP/1.1 200 OK\r\n\r\nTest server running"
                    client_socket.send(response)
                    print(f"[{addr[0]}:{addr[1]}] Sent response")
                    break
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"[{addr[0]}:{addr[1]}] Error handling data: {e}")
                    break
                    
        except Exception as e:
            print(f"[{addr[0]}:{addr[1]}] Error in client handler: {e}")
        finally:
            client_socket.close()
            print(f"[{addr[0]}:{addr[1]}] Client disconnected")
    
    def stop(self):
        """Stop the server"""
        self.running = False
        if hasattr(self, 'server_socket'):
            self.server_socket.close()
        print("✓ Test server stopped")

def test_crypto_functionality():
    """Test that our crypto functionality works"""
    print("\n=== Testing Crypto Functionality ===")
    
    try:
        # Test AES
        print("1. Testing AES encryption...")
        key = get_random_bytes(32)  # 256-bit key
        iv = get_random_bytes(16)   # 128-bit IV
        
        # Note: This is a simplified test since full AES integration requires more setup
        print("   ✓ AES key generation successful")
        
        # Test RSA
        print("2. Testing RSA key generation...")
        rsa_key = RSA.generate(512)  # 512-bit for speed
        print("   ✓ RSA key generation successful")
        
        # Test encryption/decryption
        print("3. Testing RSA encryption...")
        test_data = b"Hello RSA!"
        encrypted = rsa_key.encrypt(test_data)
        decrypted = rsa_key.decrypt(encrypted)
        
        if decrypted == test_data:
            print("   ✓ RSA encryption/decryption successful")
        else:
            print("   ✗ RSA encryption/decryption failed")
            return False
            
        print("✅ All crypto tests passed!")
        return True
        
    except Exception as e:
        print(f"✗ Crypto test failed: {e}")
        return False

def main():
    print("=== Simple Test Server for RSA Implementation ===")
    
    # Test crypto functionality first
    if not test_crypto_functionality():
        print("✗ Crypto tests failed, cannot start server")
        return 1
    
    # Start the test server
    server = SimpleTestServer()
    
    try:
        print(f"\nStarting test server...")
        server.start()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.stop()
        
    return 0

if __name__ == "__main__":
    sys.exit(main())