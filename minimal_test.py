#!/usr/bin/env python3
print("Starting test...")
try:
    import socket
    print("Socket imported")
    
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5)
    print("Socket created")
    
    s.connect(('127.0.0.1', 1256))
    print("Connected to server")
    
    s.close()
    print("Test completed successfully")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
