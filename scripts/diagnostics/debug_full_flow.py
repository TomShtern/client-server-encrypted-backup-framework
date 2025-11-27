#!/usr/bin/env python3
# Extended debug script with unique username

import socket
import struct
import uuid


def test_full_registration_flow():
    # Test the full registration and public key exchange flow with unique username
    print("=== Full Registration Flow Test (Unique Username) ===")

    # Generate unique username
    unique_id = str(uuid.uuid4())[:8]
    test_username = f"debug_user_{unique_id}"
    print(f"Using unique username: {test_username}")

    sock = None
    try:
        # Connect to server
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)  # 10 second timeout
        print("Connecting to 127.0.0.1:1256...")
        sock.connect(("127.0.0.1", 1256))
        print("[OK] Connected to server")

        # Step 1: Registration
        print("\n--- Step 1: Registration ---")
        client_id = b"\x00" * 16  # All zeros for registration
        version = 3  # Client version
        code = 1025  # REQ_REGISTER
        username_bytes = test_username.encode("utf-8") + b"\x00" * (
            255 - len(test_username)
        )  # Padded to 255 bytes
        payload_size = len(username_bytes)

        # Pack header with little-endian format (as expected by server)
        header = client_id + struct.pack("<BHI", version, code, payload_size)

        print(f"Sending registration request (code {code})")
        sock.sendall(header)
        sock.sendall(username_bytes)
        print("[OK] Registration request sent")

        # Receive registration response
        print("Waiting for registration response...")
        response_header = sock.recv(7)
        if len(response_header) == 7:
            resp_version, resp_code, resp_payload_size = struct.unpack(
                "<BHI", response_header
            )
            print("Received registration response:")
            print(f"  Version: {resp_version}")
            print(f"  Code: {resp_code}")
            print(f"  Payload size: {resp_payload_size}")

            if resp_code == 1600:  # RESP_REGISTER_OK
                # Read the new client ID
                client_id_received = sock.recv(resp_payload_size)
                print(f"  New Client ID: {client_id_received.hex()}")
                print("[OK] Registration successful")

                # Step 2: Send public key
                print("\n--- Step 2: Send Public Key ---")
                # Use the received client ID for subsequent requests
                client_id = client_id_received
                code = 1026  # REQ_SEND_PUBLIC_KEY

                # Create a fake public key payload (255 bytes username + 160 bytes key)
                username_padded = test_username.encode("utf-8") + b"\x00" * (
                    255 - len(test_username)
                )
                fake_public_key = b"\x01" * 160  # Fake 160-byte public key
                pubkey_payload = username_padded + fake_public_key
                payload_size = len(pubkey_payload)

                # Pack header
                header = client_id + struct.pack("<BHI", version, code, payload_size)

                print(f"Sending public key request (code {code})")
                sock.sendall(header)
                sock.sendall(pubkey_payload)
                print("[OK] Public key request sent")

                # Receive public key response
                print("Waiting for public key response...")
                try:
                    response_header = sock.recv(7)
                    if len(response_header) == 7:
                        resp_version, resp_code, resp_payload_size = struct.unpack(
                            "<BHI", response_header
                        )
                        print("Received public key response:")
                        print(f"  Version: {resp_version}")
                        print(f"  Code: {resp_code}")
                        print(f"  Payload size: {resp_payload_size}")

                        if resp_code == 1602:  # RESP_PUBKEY_AES_SENT
                            # Read the payload (client_id + encrypted AES key)
                            payload = sock.recv(resp_payload_size)
                            print(f"  Payload received ({len(payload)} bytes)")
                            if (
                                len(payload) > 16
                            ):  # Should contain client_id + encrypted key
                                received_client_id = payload[:16]
                                encrypted_key = payload[16:]
                                print(
                                    f"  Client ID in response: {received_client_id.hex()}"
                                )
                                print(
                                    f"  Encrypted AES key size: {len(encrypted_key)} bytes"
                                )
                                print("[OK] Public key exchange successful")
                            else:
                                print(
                                    "[ERROR] Invalid payload size in public key response"
                                )
                        else:
                            print(f"[ERROR] Unexpected response code: {resp_code}")
                    else:
                        print(
                            f"[ERROR] Incomplete response header: {response_header.hex()}"
                        )
                except TimeoutError:
                    print("[ERROR] Timeout waiting for public key response")
                except Exception as e:
                    print(f"[ERROR] Failed to receive public key response: {e}")
            elif resp_code == 1601:  # RESP_REGISTER_FAIL
                print("[ERROR] Registration failed - username already exists")
                print(
                    "Try again with a different username or clear the server database"
                )
            else:
                print(f"[ERROR] Unexpected registration response code: {resp_code}")
        else:
            print(f"[ERROR] Incomplete registration response: {response_header.hex()}")

    except Exception as e:
        print(f"[ERROR] Registration flow test failed: {e}")
        import traceback

        traceback.print_exc()
    finally:
        try:
            if sock:
                sock.close()
        except Exception:
            pass


def main():
    print("Extended Debugging Client-Server Communication")
    print("=============================================")

    test_full_registration_flow()

    print("\n=== Test Complete ===")


if __name__ == "__main__":
    main()
