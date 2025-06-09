# Secure File Transfer System - Complete Implementation Specification

## Mission Statement

Implement a secure client-server file transfer system where a C++ client encrypts and sends files to a Python server for storage. The system uses RSA for key exchange and AES for file encryption, with CRC-32 verification and automatic retry logic.

## Quick Reference

- **Server**: Python 3.11.4, Version 3
- **Client**: C++17, Visual Studio 2022, Version 3
- **Encryption**: RSA-1024 (key exchange), AES-256-CBC (files) (can be adjusted slightly if you must.)
- **Protocol**: Binary over TCP, little-endian, custom binary protocol.
- **Dependencies**:
  - Server: PyCryptodome
  - Client: Crypto++, Boost.asio
- **Default Port**: 1256

## Architecture Overview

```
┌─────────────┐                           ┌─────────────┐
│   Client    │                           │   Server    │
│    (C++)    │                           │  (Python)   │
├─────────────┤                           ├─────────────┤
│transfer.info│──────── TCP/IP ──────────▶│ port.info   │
│  me.info    │    (Boost.asio)           │defensive.db │
│  (files)    │     Binary Protocol       │  (files)    │
└─────────────┘                           └─────────────┘
```

## Development Environment Setup

### Server (Python)

```bash
pip install pycryptodome
```

### Client (C++ with Visual Studio 2022)

1. Install Boost libraries (specifically Boost.asio)
2. Install Crypto++ library
3. Configure project to link against:
  - Boost.asio (header-only, but needs Boost.system)
  - Crypto++ (cryptlib.lib)
4. Set C++ standard to C++17 or higher

## Project Structure

```
secure_file_transfer/
├── server/
│   ├── main.py             # Entry point
│   ├── server.py           # Socket server, main loop
│   ├── client_handler.py   # Per-client connection logic
│   ├── protocol.py         # Protocol constants & structures
│   ├── crypto.py           # PyCryptodome wrapper
│   ├── database.py         # SQLite operations
│   └── port.info           # Port configuration
│
└── client/
    ├── src/
    │   ├── main.cpp        # Entry point
    │   ├── client.cpp      # Main client logic
    │   ├── protocol.h/cpp  # Protocol implementation
    │   ├── crypto.h/cpp    # Crypto++ wrapper
    │   └── network.h/cpp   # Socket operations
    ├── transfer.info       # Server IP & file to send
    └── me.info            # Client identity (after registration)
```

## Communication Protocol

### Binary Structure Rules

1. All multi-byte numeric fields are **unsigned little-endian**
2. All string fields are **fixed-size buffers**, null-terminated, padded with zeros
3. Transport is **TCP** with binary protocol
4. No assumptions about packet boundaries - may need reassembly

### Request Header Structure (Client → Server)

| Field | Size (bytes) | Type | Description |
| --- | --- | --- | --- |
| Client ID | 16  | Binary | UUID (ignored during initial registration) |
| Version | 1   | uint8 | Client version = 3 |
| Code | 2   | uint16 | Request code (see below) |
| Payload Size | 4   | uint32 | Size of following payload |
| Payload | Variable | Binary | Request-specific data |

### Request Codes and Payloads

#### Code 1025: Registration Request

| Field | Size | Type | Description |
| --- | --- | --- | --- |
| Name | 255 | char[] | Null-terminated ASCII username |

#### Code 1026: Send Public Key

| Field | Size | Type | Description |
| --- | --- | --- | --- |
| Name | 255 | char[] | Null-terminated ASCII username |
| Public Key | 160 | Binary | RSA public key in X509 format |

#### Code 1027: Reconnection Request

| Field | Size | Type | Description |
| --- | --- | --- | --- |
| Name | 255 | char[] | Null-terminated ASCII username |

#### Code 1028: Send File Chunk

| Field | Size | Type | Description |
| --- | --- | --- | --- |
| Content Size | 4   | uint32 | Total encrypted file size |
| Orig File Size | 4   | uint32 | Original file size (pre-encryption) |
| Packet Number | 2   | uint16 | Current packet (1-based) |
| Total Packets | 2   | uint16 | Total number of packets |
| File Name | 255 | char[] | Null-terminated filename |
| Message Content | Variable | Binary | Encrypted file chunk |

**Critical**: Large files are sent in multiple 1028 requests

#### Code 1029: CRC Valid

| Field | Size | Type | Description |
| --- | --- | --- | --- |
| File Name | 255 | char[] | Null-terminated filename |

#### Code 1030: CRC Invalid (Retry)

| Field | Size | Type | Description |
| --- | --- | --- | --- |
| File Name | 255 | char[] | Null-terminated filename |

#### Code 1031: CRC Invalid (Final Abort)

| Field | Size | Type | Description |
| --- | --- | --- | --- |
| File Name | 255 | char[] | Null-terminated filename |

### Response Header Structure (Server → Client)

| Field | Size (bytes) | Type | Description |
| --- | --- | --- | --- |
| Version | 1   | uint8 | Server version = 3 |
| Code | 2   | uint16 | Response code |
| Payload Size | 4   | uint32 | Size of following payload |
| Payload | Variable | Binary | Response-specific data |

### Response Codes and Payloads

#### Code 1600: Registration Successful

| Field | Size | Type | Description |
| --- | --- | --- | --- |
| Client ID | 16  | Binary | New UUID assigned to client |

#### Code 1601: Registration Failed

No payload (username already taken)

#### Code 1602: AES Key Sent

| Field | Size | Type | Description |
| --- | --- | --- | --- |
| Client ID | 16  | Binary | Client's UUID |
| Encrypted AES Key | Variable | Binary | RSA-encrypted AES key |

#### Code 1603: File Received with Checksum

| Field | Size | Type | Description |
| --- | --- | --- | --- |
| Client ID | 16  | Binary | Client's UUID |
| Content Size | 4   | uint32 | Encrypted file size |
| File Name | 255 | char[] | Null-terminated filename |
| Checksum | 4   | uint32 | CRC-32 checksum |

#### Code 1604: Acknowledgment

| Field | Size | Type | Description |
| --- | --- | --- | --- |
| Client ID | 16  | Binary | Client's UUID |

#### Code 1605: Reconnection Approved

Same as 1602 - sends new AES key

#### Code 1606: Reconnection Denied

| Field | Size | Type | Description |
| --- | --- | --- | --- |
| Client ID | 16  | Binary | Client's UUID |

#### Code 1607: General Server Error

No payload

## Implementation Flows

### Flow 1: First-Time Registration

```
1. Client starts, checks for me.info existence
   - If exists: Go to Flow 2 (Reconnection)
   - If not exists: Continue with registration

2. Client → Server: Request 1025 (Registration)
   - Payload: Username from transfer.info

3. Server processes registration:
   - Check if username exists
   - If exists: Response 1601 (Failed)
   - If new: Generate UUID, save user, Response 1600 (Success)

4. Client saves to me.info:
   - Line 1: Username
   - Line 2: UUID as hex string
   - Line 3: (Private key added after next step)

5. Client generates RSA key pair:
   - Private key: Save to me.info line 3 (Base64)
   - Public key: Prepare for sending

6. Client → Server: Request 1026 (Send Public Key)
   - Payload: Username + 160-byte public key

7. Server processes public key:
   - Save public key to user record
   - Generate new AES-256 key
   - Encrypt AES key with client's public RSA key
   - Response 1602 (AES Key)

8. Client decrypts AES key with private RSA key

9. File Transfer:
   a. Client reads file from transfer.info path
   b. Calculate original file CRC-32
   c. Encrypt file with AES-256-CBC (IV=zeros)
   d. Split into chunks if needed
   e. For each chunk:
      Client → Server: Request 1028 (File Chunk)

10. Server processes file:
    a. Receive all chunks (check packet numbers)
    b. Reassemble encrypted file
    c. Decrypt with stored AES key
    d. Calculate CRC-32 of decrypted file
    e. Save file to disk
    f. Response 1603 (File Received + CRC)

11. Client verifies CRC:
    - If match: Request 1029 (Valid) → Response 1604 (Ack) → END
    - If no match (attempts 1-3): Request 1030 (Invalid) → Goto step 9
    - If no match (attempt 4): Request 1031 (Abort) → END
```

### Flow 2: Reconnection

```
1. Client starts, detects me.info exists
   - Read username, UUID, private key

2. Client → Server: Request 1027 (Reconnection)
   - Payload: Username

3. Server checks database:
   - If user exists AND has public key:
     * Generate NEW AES key
     * Encrypt with stored public key
     * Response 1605 (Reconnection Approved)
   - If user not found OR no public key:
     * Response 1606 (Reconnection Denied)

4. If approved: Continue from Flow 1, Step 8
   If denied: Delete me.info, restart as Flow 1
```

## Critical Implementation Details

### Encryption Specifications

**RSA (Key Exchange)**

- Algorithm: RSA
- Key Size: 1024 bits
- Public Key Format: X509 (results in 160 bytes)
- Usage: Only for encrypting AES keys

**AES (File Encryption)**

- Algorithm: AES-256-CBC
- Key Size: 256 bits (32 bytes)
- IV: All zeros (simplified for assignment)
- Padding: PKCS7

### CRC Calculation

- Algorithm: CRC-32 (must match Linux `cksum` command)
- Python: Use `zlib.crc32(data) & 0xffffffff`
- C++: Use Crypto++ CRC32 or equivalent
- Calculate on original file (before encryption)

### File Chunking

- Large files MUST be split into multiple packets
- Each packet has current/total packet numbers
- Recommended chunk size: 1MB or less
- Server must reassemble in correct order

### Configuration Files

**port.info**

```
1234
```

- Single line with port number
- If missing: Use 1256, show warning, don't crash

**transfer.info**

```
127.0.0.1:1234
Michael Jackson
New_product_spec.docx
```

- Line 1: Server IP:Port
- Line 2: Username (max 100 chars)
- Line 3: File path to send

**me.info**

```
Michael Jackson
64f3f63985f04beb81a0e43321880182
MIGdMA0GCSqGSIb3DQEBA...
```

- Line 1: Username
- Line 2: UUID (32 hex chars)
- Line 3: Private RSA key (Base64)

### Database Schema

```sql
CREATE TABLE clients (
    ID TEXT PRIMARY KEY,           -- 16-byte UUID as hex
    Name TEXT UNIQUE NOT NULL,     -- Username
    PublicKey BLOB NOT NULL,       -- 160-byte public key
    LastSeen DATETIME,             -- Last activity
    AESKey BLOB                    -- 32-byte AES key
);

CREATE TABLE files (
    ID TEXT,                       -- Client UUID (FK)
    FileName TEXT NOT NULL,        -- Original filename
    PathName TEXT NOT NULL,        -- Server storage path
    Verified INTEGER NOT NULL,     -- 0/1 for CRC verification
    FOREIGN KEY(ID) REFERENCES clients(ID)
);
```

## Core Components to Implement

### Server (Python)

**main.py**

```python
def main():
    # 1. Load port from port.info (default 1256)
    # 2. Initialize database (if implemented)
    # 3. Create server socket
    # 4. Start accepting clients
```

**protocol.py**

```python
# Constants
VERSION = 3
DEFAULT_PORT = 1256

# Request codes
REQ_REGISTER = 1025
REQ_PUBLIC_KEY = 1026
# ... etc

# Response codes  
RES_REGISTER_SUCCESS = 1600
# ... etc

# Structures using struct module
def pack_response_header(code, payload_size):
    return struct.pack('<BHI', VERSION, code, payload_size)
```

**crypto.py**

```python
from Cryptodome.PublicKey import RSA
from Cryptodome.Cipher import AES, PKCS1_OAEP
import zlib

def calculate_crc(data):
    return zlib.crc32(data) & 0xffffffff
```

### Client (C++)

**protocol.h**

```cpp
#pragma pack(push, 1)  // Ensure no padding

struct RequestHeader {
    uint8_t client_id[16];
    uint8_t version;
    uint16_t code;
    uint32_t payload_size;
};

struct ResponseHeader {
    uint8_t version;
    uint16_t code;
    uint32_t payload_size;
};

#pragma pack(pop)

const uint8_t VERSION = 3;
const uint16_t REQ_REGISTER = 1025;
// ... etc
```

**Required Libraries**

- **Boost.asio**: For all TCP networking operations
- **Crypto++**: For RSA and AES encryption
- **STL**: Recommended for containers and algorithms

**crypto.cpp**

```cpp
#include <cryptopp/rsa.h>
#include <cryptopp/aes.h>
#include <cryptopp/modes.h>
#include <cryptopp/crc.h>

class CryptoManager {
    CryptoPP::RSA::PrivateKey privateKey;
    CryptoPP::RSA::PublicKey publicKey;
    std::vector<uint8_t> aesKey;

public:
    void generateRSAKeyPair();
    std::vector<uint8_t> getPublicKey();  // X509 format
    // ... etc
};
```

**network.cpp**

```cpp
#include <boost/asio.hpp>
#include <boost/asio/ip/tcp.hpp>

namespace asio = boost::asio;
using tcp = asio::ip::tcp;

class NetworkClient {
    asio::io_context io_context;
    tcp::socket socket{io_context};

public:
    void connect(const std::string& host, uint16_t port);
    void send(const std::vector<uint8_t>& data);
    std::vector<uint8_t> receive(size_t expected_size);

    // Example implementation for binary protocol
    void sendRequest(uint16_t code, const std::vector<uint8_t>& payload) {
        RequestHeader header;
        // Fill header fields...

        // Send header
        asio::write(socket, asio::buffer(&header, sizeof(header)));

        // Send payload if any
        if (!payload.empty()) {
            asio::write(socket, asio::buffer(payload));
        }
    }
};
```

## Error Handling Requirements

1. **Network Errors**:
  - Use Boost.asio error codes for handling
  - Retry 3 times with exponential backoff
  - Handle `boost::system::error_code` in all async operations
2. **Protocol Errors**: Log and send appropriate error response
3. **File Errors**: Check disk space, handle permission issues
4. **Concurrency**: Use locks for shared resources
5. **Validation**: Check all input sizes before processing
6. **Boost.asio specifics**:
  - Handle connection timeouts using `deadline_timer`
  - Use `async_read` with completion conditions for exact byte counts
  - Catch `boost::system::system_error` exceptions

## Testing Checklist

- [ ] Single client registration and file transfer
- [ ] Multiple concurrent clients
- [ ] Large file transfer (> 10MB) with chunking
- [ ] CRC mismatch retry logic (all 4 attempts)
- [ ] Reconnection after server restart
- [ ] Missing configuration files
- [ ] Invalid protocol messages
- [ ] Network disconnection during transfer
- [ ] Database persistence (if implemented)

## Submission Requirements

1. **Source Code Only**
  
  - Server: `.py` files only
  - Client: `.h` and `.cpp` files only
  - No binaries or project files
  - Client must link against Boost.asio and Crypto++
2. **Demo and testing **
  
  - Show both server and client windows
  - Demonstrate registration and file transfer
  - Transfer ~100KB binary file
3. **Security Analysis Document** (part 3)
  
  - Identify protocol vulnerabilities
  - Propose fixes
  - Use vulnerability table format from Unit 3(ask the user about it when you get to it)
4. **Archive**: Single `.zip` file with all components
  

## Appendix: Advanced Implementation Details & Critical Warnings

This section contains supplementary information critical for ensuring interoperability and avoiding common implementation errors. It should be considered as important as the main specification.

### A.1 Critical Interoperability Rules & Common Pitfalls

Failure to adhere to the following rules will lead to a non-functional system. These points expand on the core specification and highlight common developer mistakes.

1. **AES Key Size is Non-Negotiable**: The AES key **MUST** be **256 bits (32 bytes)**. Some cryptographic libraries or provided wrappers may default to 128 bits (16 bytes). You must explicitly override this to use the required 32-byte key size.
  
2. **RSA Padding Scheme**: The RSA encryption used to protect the AES key **MUST** use **OAEP with SHA-256** padding. Using other padding schemes (like the older PKCS1_v1_5) will result in a key that the other party cannot decrypt.
  
3. **The cksum Algorithm is NOT Standard CRC-32**: You cannot use a standard library's CRC32 function and expect it to match. The POSIX cksum algorithm has a unique final step where the total file length is processed. (See the deep-dive below).
  
4. **Client Registration Logic**: A client **MUST NOT** send a registration request (Code 1025) if a me.info file already exists. The presence of this file signals that the client must start with the Reconnection flow (Code 1027).
  
5. **Server Handling of Client ID**: During an initial registration request (Code 1025), the Client ID field in the header will be uninitialized. The server **MUST** ignore this field for this specific request code.
  
6. **Static IV is Required**: The specification requires a static, all-zero Initialization Vector (IV) for AES-CBC. While this is a security vulnerability, it is a requirement for interoperability in this assignment. Do not use a random IV.
  

### A.2 Algorithm Deep Dive: POSIX cksum

To achieve an identical checksum on both the Python server and C++ client, you must implement this specific algorithm, which differs from a standard CRC-32 calculation.

**Algorithm Steps**:

1. Initialize a 32-bit unsigned integer crc to 0.
  
2. For each byte b in the **original, unencrypted file data**, update the crc register.
  
3. **After processing all file bytes**, you must then process the file's original length. For each byte l in the 32-bit little-endian representation of the file's length, update the crc register in the same manner.
  
4. The final cksum value is the bitwise NOT of the final crc register (e.g., ~crc or crc ^ 0xFFFFFFFF).
  

This process ensures that two files with the same content but different lengths will have different checksums, a key feature of the cksum command. The polynomial used for the CRC-32 table is 0x04C11DB7.

### A.3 Server Concurrency & Thread Safety

If implementing the Python server using threads, you must ensure that shared resources are protected to prevent race conditions.

- **Client Dictionary/State**: Any global dictionary or object holding client information (UUIDs, sockets, AES keys) **MUST** be protected by a threading.Lock.
  
- **File System Access**: While many OS-level file operations are atomic, it is good practice to use a lock if your logic involves checking for a file's existence and then writing to it, to prevent race conditions between threads.
  
- **Database Connections**: If using the SQLite enhancement, ensure that either each thread gets its own database connection or that all database writes are serialized through a single, locked queue.
  

### A.4 Client-Side Error Handling Requirements

The client has specific, testable error-handling behavior.

- **Generic Error Message**: Upon receiving any error response from the server (e.g., 1601, 1606, 1607) or encountering a network failure, the client should first print the exact lowercase message: "server responded with an error".
  
- **Retry Logic**: After printing the message, the client should retry the last failed operation up to **2 more times** (for a total of 3 attempts).
  
- **Fatal Exit**: If the operation still fails after 3 total attempts, the client must exit with a detailed Fatal error message explaining the cause (e.g., "Fatal error: Registration failed after 3 attempts.").
  

### A.5 Security Vulnerability Analysis (For Part 3)

The protocol as specified for this assignment contains several intentional vulnerabilities for analysis. A complete solution to Part 3 of the assignment should identify:

1. **Static IV**: Allows an attacker to identify repeated blocks of data. **Fix**: Use a unique, randomly generated IV for each encryption and prepend it to the ciphertext.
  
2. **No Message Authentication**: Ciphertext can be tampered with in transit. **Fix**: Add a Message Authentication Code (MAC), such as an HMAC-SHA256 of the ciphertext, to each message.
  
3. **Username Enumeration**: The server gives different responses for registered vs. unregistered users, allowing an attacker to guess valid usernames. **Fix**: Return a single, generic "Authentication Failed" error for all related failures.
  
4. **Replay Attacks**: A captured request (e.g., a file transfer) could be resent by an attacker. **Fix**: Implement sequence numbers or a one-time nonce in the protocol.