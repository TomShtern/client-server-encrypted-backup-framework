#!/usr/bin/env python3
"""
Simple connection test
"""
import socket
import json

def test_connection():
    try:
        print("Testing connection to server...")
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect(('127.0.0.1', 1256))
        print("Connected successfully!")
        
        # Send a simple test message
        test_msg = {"type": "test"}
        msg_str = json.dumps(test_msg)
        msg_bytes = msg_str.encode('utf-8')
        
        # Send length first
        length = len(msg_bytes)
        s.send(length.to_bytes(4, byteorder='big'))
        s.send(msg_bytes)
        print("Message sent")
        
        # Try to receive response
        try:
            length_bytes = s.recv(4)
            if len(length_bytes) == 4:
                length = int.from_bytes(length_bytes, byteorder='big')
                response_bytes = s.recv(length)
                response = json.loads(response_bytes.decode('utf-8'))
                print(f"Response: {response}")
            else:
                print("No proper response received")
        except Exception as e:
            print(f"Error receiving response: {e}")
        
        s.close()
        print("Connection test completed")
        
    except Exception as e:
        print(f"Connection test failed: {e}")

if __name__ == "__main__":
    test_connection()
