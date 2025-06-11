# Encrypted File Backup System - Comprehensive Technical Specification

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture and Core Components](#architecture-and-core-components)
3. [Server Implementation (Python)](#server-implementation-python)
4. [Client Implementation (C++)](#client-implementation-c)
5. [Communication Protocol](#communication-protocol)
6. [Encryption Specifications](#encryption-specifications)
7. [Process Flows](#process-flows)
8. [Error Handling](#error-handling)
9. [Security Considerations](#security-considerations)
10. [Database Enhancement (Optional)](#database-enhancement-optional)
11. [Development Guidelines](#development-guidelines)
12. [Appendix: Provided Wrapper Classes](#appendix-provided-wrapper-classes)

## System Overview

This specification describes a client-server system for secure file backup with encryption. Clients can register with the server, exchange encryption keys, and transfer files securely for server-side storage.

### Quick Reference - Protocol Codes

**Client Request Codes**:
- `1025` - Registration Request
- `1026` - Send Public Key  
- `1027` - Reconnection Request
- `1028` - Send File
- `1029` - CRC Valid
- `1030` - CRC Invalid, Resending
- `1031` - CRC Invalid 4th Time, Aborting

**Server Response Codes**:
- `1600` - Registration Successful
- `1601` - Registration Failed
- `1602` - Public Key Received, AES Key Sent
- `1603` - File Received, CRC Sent  
- `1604` - Generic Acknowledgement
- `1605` - Reconnection Approved, AES Key Sent
- `1606` - Reconnection Denied
- `1607` - General Server Error

### Key Features

- User registration with unique identifiers (UUID)
- RSA asymmetric encryption for secure key exchange
- AES symmetric encryption for file transfers
- CRC checksum verification for data integrity
- Automatic retry mechanism for failed transfers
- Persistent storage with reconnection support
- Multi-client support with concurrent connections

### Technology Stack

- **Server**: Python 3.11.4 with PyCryptodome library
- **Client**: C++17 with Crypto++ library, Visual Studio 2022
- **Protocol**: Binary over TCP/IP, little-endian byte order
- **Database** (Optional): SQLite for persistent storage

## Critical Interoperability Points

### MUST Requirements for Compatibility

1. **Protocol Version**: Both client and server MUST report version `3`
2. **Byte Order**: ALL multi-byte integers MUST be little-endian
3. **RSA Public Key**: MUST be exactly 160 bytes in Crypto++ X.509 format
4. **AES Key Size**: MUST be 256 bits (32 bytes) - override wrapper default
5. **Checksum**: MUST match Linux `cksum` exactly (see algorithm below)
6. **File Transfer**: MUST set packet_number=1, total_packets=1 (no chunking)
7. **String Fields**: MUST be null-terminated and padded to full field size with zeros
8. **Client ID**: Server MUST ignore this field in registration request (1025)
9. **UUID Format**: MUST be stored as 32 lowercase hex characters in me.info
10. **Static IV**: MUST be exactly 16 bytes of 0x00 for AES-CBC

### Common Implementation Mistakes to Avoid

- **Wrong AES key size**: Wrapper defaults to 16 bytes, but protocol requires 32
- **Incorrect endianness**: Using big-endian instead of little-endian
- **Wrong CRC algorithm**: Using standard CRC-32 instead of `cksum` variant  
- **Incomplete string padding**: Not padding to full 255 bytes
- **Re-registration**: Client attempting to register when me.info exists
- **Wrong RSA padding**: Using PKCS1 instead of OAEP-SHA256
- **Chunking files**: Attempting to split files into multiple packets

## Architecture and Core Components

### System Architecture

```
┌─────────────┐                    ┌─────────────┐
│   Client    │                    │   Server    │
│    (C++)    │◄──────TCP/IP──────►│  (Python)   │
│             │                    │             │
│ ┌─────────┐ │                    │ ┌─────────┐ │
│ │Crypto++ │ │                    │ │PyCrypto │ │
│ │Library  │ │                    │ │  dome   │ │
│ └─────────┘ │                    │ └─────────┘ │
└─────────────┘                    └─────────────┘
      │                                    │
      ▼                                    ▼
┌─────────────┐                    ┌─────────────┐
│Configuration│                    │   Storage   │
│   Files     │                    │Files & DB   │
└─────────────┘                    └─────────────┘
```

### Core Functionality Flow

1. Client initiates TCP connection to server
2. Client registers or reconnects using stored credentials
3. Client and server perform RSA key exchange
4. Server generates and sends AES session key encrypted with client's RSA public key
5. Client encrypts file using AES session key and transfers to server
6. Server decrypts file, calculates checksum, and sends back to client
7. Client verifies checksum; retries if mismatch (up to 3 attempts total)

## Server Implementation (Python)

### General Requirements

- **Language**: Python 3.11.4
- **Concurrency**: MUST support multiple concurrent clients using either:
  - Python threads (MUST ensure thread-safe access to shared resources)
  - `selectors` module for async I/O
- **Thread Safety Requirements** (if using threads):
  - Use locks for client dictionary access
  - Use locks for file system operations  
  - Use locks for database operations
  - Each client connection handled in separate thread
- **Protocol Version**: Server MUST identify as version `3` in all responses
- **Libraries**:
  - **Encryption**: PyCryptodome (required)
  - **Other**: Only standard Python libraries (socket, struct, os, uuid, sqlite3)

### Port Configuration

The server reads its listening port from a configuration file:

**File**: `port.info`
- **Location**: Same directory as server source code
- **Format**: Single line containing port number
- **Example**:
  ```
  1234
  ```
- **Fallback**: If file missing or invalid, issue warning and use default port `1256`
- **Important**: Server MUST NOT crash if file is missing

### Data Storage

1. **In-Memory (RAM)**:
   - Active client sessions
   - Client identifiers and usernames
   - RSA public keys (unless using database)
   - Current AES session keys

2. **File System**:
   - MUST create dedicated directory for received files
   - MUST handle duplicate filenames from different clients
   - MUST handle duplicate filenames from same client
   - Recommended naming strategies:
     - `<client_uuid>_<filename>` 
     - `<client_uuid>/<filename>` (subdirectories per client)
     - `<timestamp>_<client_uuid>_<filename>`
   - Store decrypted files only (never store encrypted versions)

3. **Database** (Optional - see [Database Enhancement](#database-enhancement-optional)):
   - SQLite database for persistent storage
   - Enables client reconnection after server restart

### Server Operational Flow

#### Startup Sequence

1. Read port from `port.info` (or use default 1256)
2. If database enabled: Initialize SQLite connection and load existing client data
3. Bind to IP address `0.0.0.0` (all interfaces) and configured port
4. Listen for incoming TCP connections in infinite loop
5. For each connection: spawn thread or use selector for handling

#### Request Processing

The server processes requests based on their code:

**Registration (Code 1025)**:
- Check if username exists (case-sensitive comparison)
- If exists: Respond with Registration Failed (1601)
- If new: 
  - Generate 16-byte UUID using `uuid.uuid4().bytes`
  - Store as 32-char hex string in database: `uuid.hex()`
  - Send raw 16 bytes in response
  - Store client data, respond with Registration Success (1600)

**Public Key Submission (Code 1026)**:
- Store/update client's 160-byte RSA public key
- Generate new 256-bit AES session key
- Encrypt AES key using client's RSA public key (RSA-OAEP with SHA-256)
- Respond with encrypted AES key (1602)

**Reconnection (Code 1027)**:
- Verify client using UUID and username
- If valid with stored public key: Generate NEW AES key, encrypt, send (1605)
- If invalid: Respond with Reconnection Denied (1606)

**File Transfer (Code 1028)**:
- Decrypt file using client's current AES session key
- Calculate CRC checksum of decrypted data
- Save decrypted file to storage directory
- Respond with calculated checksum (1603)

**CRC Confirmations (Codes 1029-1031)**:
- CRC Valid (1029): Acknowledge with 1604
- CRC Invalid Retry (1030): Prepare for file retransmission
- CRC Invalid Abort (1031): Acknowledge with 1604

### Checksum (CRC) Calculation

The checksum MUST be identical to Linux `cksum` command. This is NOT standard CRC-32.

**Algorithm Specification**:
```
1. Initialize: crc = 0x00000000 (32-bit register)
2. For each byte b in file:
      crc = (crc << 8) ^ crctab[(crc >> 24) ^ b]
3. After all file bytes, process file length:
      length = original_file_size (in bytes)
      while (length > 0):
          crc = (crc << 8) ^ crctab[(crc >> 24) ^ (length & 0xFF)]
          length >>= 8
4. Final step: crc = ~crc  (bitwise NOT / XOR with 0xFFFFFFFF)
5. Result: 32-bit checksum (4 bytes)
```

**Key Points**:
- Polynomial: `0x04C11DB7` (used to generate lookup table)
- The file length is processed as additional bytes after file data
- Process length in little-endian byte order
- Both client and server MUST implement identical algorithm
- This is specific to POSIX `cksum`, not generic CRC-32

**Testing**: Verify implementation matches `cksum <filename>` on Linux

## Client Implementation (C++)

### General Requirements

- **Language**: C++ (C++17 compatible)
- **Build Environment**: Visual Studio 2022
- **Operation Mode**: Batch mode (non-interactive)
- **Protocol Version**: Client MUST identify as version `3` in all requests
- **Libraries**:
  - **Encryption**: Crypto++ (CryptoPP)
  - **Networking**: Winsock or Boost.Asio
  - **Standard**: STL recommended

### Configuration Files

#### transfer.info

Specifies connection and transfer details for current session.

**Location**: Same directory as client executable (.exe)  
**Format**: MUST be exactly 3 lines (no empty lines, no extra lines)
```
127.0.0.1:1234
Michael Jackson
C:\data\New_product_spec.docx
```
- Line 1: Server IP:Port (no spaces)
- Line 2: Username (ASCII only, max 100 characters)
- Line 3: Full path to file for transfer

#### me.info  

Stores persistent client identity and credentials.

**Location**: Same directory as client executable  
**Format**: MUST be exactly 3 lines
```
Michael Jackson
64f3f63985f04beb81a0e43321880182
MIGdMA0GCSqGSIb3DQEBA...
```
- Line 1: Registered username (must match registration exactly)
- Line 2: UUID - MUST be exactly 32 lowercase hex characters (16 bytes)
- Line 3: RSA private key in Base64 format (no line breaks)

**Critical Implementation Notes**:
- This file is created after first successful registration
- Use atomic write (write to temp file, then rename) to prevent corruption
- File is the ONLY persistent storage for private key
- If file exists, client MUST NOT re-register

### Client Operational Flow

#### Initialization
1. Read server details and file path from `transfer.info`
2. Check for `me.info` existence

#### Registration vs Reconnection

**If `me.info` does NOT exist (First Run)**:
1. Use username from `transfer.info`
2. Send Registration Request (1025)
3. On success (1600):
   - Receive UUID from server
   - Generate 1024-bit RSA key pair
   - Save credentials to `me.info`
   - Send public key (1026)

**If `me.info` EXISTS (Subsequent Runs)**:
1. Load credentials from `me.info`
2. Decode Base64 private key
3. Send Reconnection Request (1027)
4. Handle response:
   - Success (1605): Receive new AES key
   - Denied (1606): Print error and exit

#### Key Exchange

After registration or successful reconnection:
1. Receive encrypted AES key from server
2. Decrypt using RSA private key (RSA-OAEP with SHA-256)
3. Store decrypted 256-bit AES key for file encryption

#### File Transfer

1. Calculate CRC of **original unencrypted file**
2. Encrypt file using AES-CBC with zero IV
3. Send encrypted file (1028) with packet_number=1, total_packets=1
4. Receive server's CRC (1603)
5. Compare checksums:
   - Match: Send CRC Valid (1029)
   - Mismatch: Retry up to 2 more times (3 total)
   - 3rd failure: Send CRC Abort (1031) and exit

### Error Handling

For any server error response or communication failure:
1. Print exactly: `"server responded with an error"` (lowercase, no period)
2. Retry current request up to 2 more times (3 attempts total)
3. After 3 failures: Exit with detailed error message like:
   - `"Fatal error: Registration failed after 3 attempts"`
   - `"Fatal error: File transfer failed after 3 retries due to checksum mismatch"`
   - `"Fatal error: Communication with server failed"`

## Communication Protocol

### General Characteristics

- **Transport**: TCP/IP
- **Format**: Binary
- **Byte Order**: Little-endian for ALL multi-byte numeric fields
- **Numeric Values**: Unsigned integers (unless specified otherwise)
- **Strings**: ASCII, null-terminated, padded to field size

### Message Structure

#### Request Header (Client → Server)

| Field | Size | Type | Description |
|-------|------|------|-------------|
| Client ID | 16 bytes | Binary | Client UUID (ignored for registration) |
| Version | 1 byte | uint8 | Protocol version (value: 3) |
| Code | 2 bytes | uint16 | Request code |
| Payload Size | 4 bytes | uint32 | Size of payload in bytes |

#### Response Header (Server → Client)

| Field | Size | Type | Description |
|-------|------|------|-------------|
| Version | 1 byte | uint8 | Protocol version (value: 3) |
| Code | 2 bytes | uint16 | Response code |
| Payload Size | 4 bytes | uint32 | Size of payload in bytes |

### Request Codes and Payloads

#### 1025: Registration Request

| Field | Size | Description |
|-------|------|-------------|
| Name | 255 bytes | Username (null-terminated ASCII) |

#### 1026: Send Public Key

| Field | Size | Description |
|-------|------|-------------|
| Name | 255 bytes | Username (null-terminated ASCII) |
| Public Key | 160 bytes | RSA 1024-bit key in X.509 format |

**Critical**: The 160-byte format is specific to Crypto++ X.509 encoding for 1024-bit RSA keys

#### 1027: Reconnection Request

| Field | Size | Description |
|-------|------|-------------|
| Name | 255 bytes | Username (null-terminated ASCII) |

#### 1028: Send File

| Field | Size | Description |
|-------|------|-------------|
| Content Size | 4 bytes | Encrypted file size |
| Orig File Size | 4 bytes | Original file size |
| Packet Number | 2 bytes | Current packet (always 1) |
| Total Packets | 2 bytes | Total packets (always 1) |
| File Name | 255 bytes | Filename (null-terminated ASCII) |
| Message Content | Variable | Encrypted file data |

**Important**: No file chunking - entire file sent as single packet

#### 1029: CRC Valid

| Field | Size | Description |
|-------|------|-------------|
| File Name | 255 bytes | Filename (null-terminated ASCII) |

#### 1030: CRC Invalid, Resending

| Field | Size | Description |
|-------|------|-------------|
| File Name | 255 bytes | Filename (null-terminated ASCII) |

#### 1031: CRC Invalid (4th Time), Aborting

| Field | Size | Description |
|-------|------|-------------|
| File Name | 255 bytes | Filename (null-terminated ASCII) |

### Response Codes and Payloads

#### 1600: Registration Successful

| Field | Size | Description |
|-------|------|-------------|
| Client ID | 16 bytes | New UUID for client |

#### 1601: Registration Failed
No payload

#### 1602: Public Key Received, AES Key Sent

| Field | Size | Description |
|-------|------|-------------|
| Client ID | 16 bytes | Client UUID |
| Encrypted Symmetric Key | Variable | AES key encrypted with RSA |

#### 1603: File Received, CRC Sent

| Field | Size | Description |
|-------|------|-------------|
| Client ID | 16 bytes | Client UUID |
| Content Size | 4 bytes | Encrypted file size |
| File Name | 255 bytes | Filename (null-terminated ASCII) |
| Cksum | 4 bytes | Calculated CRC checksum |

#### 1604: Generic Acknowledgement

| Field | Size | Description |
|-------|------|-------------|
| Client ID | 16 bytes | Client UUID |

#### 1605: Reconnection Approved, AES Key Sent

| Field | Size | Description |
|-------|------|-------------|
| Client ID | 16 bytes | Client UUID |
| Encrypted Symmetric Key | Variable | New AES key encrypted with RSA |

#### 1606: Reconnection Denied

| Field | Size | Description |
|-------|------|-------------|
| Client ID | 16 bytes | Client UUID |

#### 1607: General Server Error
No payload

## Encryption Specifications

### Symmetric Encryption (AES)

- **Algorithm**: AES-CBC (Cipher Block Chaining)
- **Key Size**: 256 bits (32 bytes)
- **IV**: Static all-zeros (16 bytes of 0x00)
- **Padding**: PKCS7
- **Usage**: File encryption only

**Security Note**: Static IV is a known vulnerability, acceptable only for this implementation

### Asymmetric Encryption (RSA)

- **Algorithm**: RSA
- **Key Size**: 1024 bits
- **Padding**: RSA-OAEP with SHA-256
- **Public Key Format**: X.509 (160 bytes for 1024-bit key)
- **Usage**: AES key encryption only

### Important Implementation Notes

1. **AES Key Size Discrepancy**: 
   - Specification requires 256-bit (32-byte) AES keys
   - Provided wrapper shows 16-byte default - must be overridden

2. **RSA Public Key Format**:
   - Exactly 160 bytes in Crypto++ X.509 format
   - Both client and server must handle this specific format

3. **Checksum Algorithm**:
   - Must match Linux `cksum` exactly
   - Includes file length in calculation
   - See detailed algorithm in server section

## Process Flows

### Registration and Initial File Transfer

```
Client                                      Server
  |                                           |
  |--[1025: Register "username"]------------->|
  |                                           |← Generate UUID
  |<---------[1600: UUID]---------------------|
  |← Save to me.info                          |
  |← Generate RSA keys                        |
  |                                           |
  |--[1026: Username + Public Key]----------->|
  |                                           |← Generate AES key
  |                                           |← Encrypt with client public key
  |<---------[1602: UUID + Encrypted AES]-----|
  |← Decrypt AES key                          |
  |← Calculate file CRC                       |
  |← Encrypt file with AES                    |
  |                                           |
  |--[1028: Encrypted file]------------------>|
  |                                           |← Decrypt file
  |                                           |← Calculate CRC
  |<---------[1603: CRC + file info]----------|
  |← Compare CRCs                             |
  |                                           |
  If CRC matches:                             |
  |--[1029: CRC Valid]----------------------->|
  |<---------[1604: ACK]----------------------|
  |                                           |
  If CRC mismatch (attempts 1-2):             |
  |--[1030: CRC Invalid, Resending]---------->|
  |--[1028: Encrypted file (retry)]---------->|
  |                                           |
  If CRC mismatch (attempt 3):                |
  |--[1031: CRC Invalid, Aborting]----------->|
  |<---------[1604: ACK]----------------------|
  |← Exit with error                          |
```

### Reconnection Flow

```
Client                                      Server
  |← Load me.info                             |
  |                                           |
  |--[1027: Reconnect "username"]------------>|
  |                                           |← Verify client exists
  |                                           |← Check public key stored
  |                                           |
  If client found:                            |
  |                                           |← Generate new AES key
  |<---------[1605: UUID + Encrypted AES]-----|
  |← Continue with file transfer              |
  |                                           |
  If client not found:                        |
  |<---------[1606: Reconnection Denied]------|
  |← Exit (must re-register)                  |
```

## Error Handling

### Client Error Handling

1. **Server Error Responses (1601, 1606, 1607)**:
   - Print: `"server responded with an error"`
   - Retry current request up to 2 more times
   - After 3 total attempts: Exit with detailed error

2. **File Transfer Failures**:
   - CRC mismatch: Retry file transfer up to 2 more times
   - After 3 transfers with mismatched CRC: Send abort (1031) and exit

3. **Network Errors**:
   - Handle disconnections gracefully
   - Attempt reconnection before failing

### Server Error Handling

1. **Missing Configuration**:
   - Missing `port.info`: Warn and use port 1256
   - Never crash on missing files

2. **Registration Errors**:
   - Duplicate username: Respond 1601
   - Invalid data: Respond 1607

3. **Reconnection Errors**:
   - Unknown client: Respond 1606
   - Missing public key: Respond 1606

4. **Resource Errors**:
   - Disk full: Respond 1607
   - Database errors: Respond 1607

## Security Considerations

### Known Vulnerabilities

1. **Static IV (All Zeros)**
   - Vulnerable to pattern analysis
   - Same plaintext produces same ciphertext

2. **Weak RSA Key Size**
   - 1024-bit RSA is below modern standards
   - Vulnerable to factorization attacks

3. **No Message Authentication**
   - No MAC or digital signatures
   - Vulnerable to tampering

4. **No Replay Protection**
   - No sequence numbers or timestamps
   - Old messages can be replayed

5. **Username Enumeration**
   - Different errors for existing/non-existing users
   - Allows attacker to discover valid usernames

6. **Plaintext Protocol Headers**
   - Client ID sent before authentication
   - Protocol structure visible to attackers

### Recommended Mitigations

1. Use random IV for each encryption
2. Upgrade to 2048-bit RSA minimum
3. Add HMAC for message authentication
4. Implement sequence numbers or timestamps
5. Return generic errors for security failures
6. Encrypt entire protocol messages

## Database Enhancement (Optional)

### SQLite Database Configuration

- **Database File**: `defensive.db`
- **Location**: Same directory as server executable
- **Purpose**: Persistent storage for reconnection support

### Database Schema

#### clients Table

```sql
CREATE TABLE clients (
    ID TEXT PRIMARY KEY,          -- 16-byte UUID as 32-char hex string
    Name TEXT UNIQUE NOT NULL,    -- Username (max 255 chars)
    PublicKey BLOB,              -- RSA public key (160 bytes)
    LastSeen DATETIME,           -- ISO 8601 format (YYYY-MM-DD HH:MM:SS)
    AESKey BLOB                  -- Current session AES key (32 bytes)
);
```

#### files Table

```sql
CREATE TABLE files (
    ID INTEGER PRIMARY KEY AUTOINCREMENT,
    ClientID TEXT NOT NULL,      -- Foreign key to clients.ID
    FileName TEXT NOT NULL,      -- Original filename
    PathName TEXT NOT NULL,      -- Server storage path
    Verified INTEGER,            -- Boolean (0/1)
    FOREIGN KEY (ClientID) REFERENCES clients(ID)
);
```

### Database Operations

1. **Startup**: 
   - Check if `defensive.db` exists
   - If exists: Load all client records into memory
   - If not: Create new database with schema

2. **Registration (1025)**: 
   - Insert new client record with generated UUID

3. **Key Update (1026)**: 
   - Update PublicKey field for client
   - Update LastSeen timestamp

4. **Reconnection (1027)**: 
   - Query client by UUID (from header) AND Name (from payload)
   - Both must match for successful reconnection
   - Update LastSeen timestamp

5. **File Storage (1028)**: 
   - Insert file record with Verified=0
   - Update LastSeen for client

6. **Verification (1029)**: 
   - Update Verified=1 for file
   - Update LastSeen for client

**Important Notes**:
- For reconnections (1605), ALWAYS generate NEW AES key
- The AESKey field stores current session key for active connections
- LastSeen should be updated for ALL authenticated requests
- Use transactions for multi-table operations

## Development Guidelines

### General Best Practices

1. **Version Control**: Use Git or similar
2. **Modular Design**: Separate concerns (networking, crypto, protocol)
3. **Error Handling**: Comprehensive try-catch blocks
4. **Logging**: Detailed logs for debugging
5. **Testing**: Unit tests for each component

### Server Development (Python)

```python
# Required main function structure
def main():
    server = Server()
    server.start()

if __name__ == "__main__":
    main()

# Recommended class structure
class Server:
    def __init__(self):
        self.clients = {}  # Thread-safe dict needed
        self.port = self.read_port()
        self.files_dir = "server_files"  # Create if not exists
        
    def read_port(self):
        try:
            with open('port.info', 'r') as f:
                return int(f.read().strip())
        except:
            print("Warning: port.info not found, using default port 1256")
            return 1256
            
    def handle_client(self, client_socket):
        # Thread-safe client handling
        pass
```

### Client Development (C++)

```cpp
// Recommended structure
class Client {
private:
    std::string serverIP;
    uint16_t serverPort;
    uint8_t uuid[16];
    RSAPrivateWrapper* rsaPrivate;
    
public:
    void loadConfig();
    void connect();
    void registerUser();
    void transferFile();
};
```

### Additional Implementation Details

#### Network Configuration
- **TCP Socket Options**: Consider setting TCP_NODELAY for low latency
- **Buffer Sizes**: Allocate sufficient buffers for large files (e.g., 64KB chunks for reading)
- **Timeouts**: 
  - Connection timeout: 30 seconds recommended
  - Read/Write timeout: 60 seconds for file transfers
  - Keep connection open for entire session

#### Binary Protocol Struct Packing
For C++ client, ensure proper struct packing:
```cpp
#pragma pack(push, 1)  // Windows
struct RequestHeader {
    uint8_t client_id[16];
    uint8_t version;
    uint16_t code;
    uint32_t payload_size;
};
#pragma pack(pop)
```

#### File Handling Constraints
- **Maximum file size**: 4GB (limited by uint32 for file size fields)
- **Filename encoding**: ASCII only, non-ASCII characters should be rejected
- **Path validation**: Reject paths with `..` to prevent directory traversal
- **Binary files**: System must handle all file types (text, binary, compressed)

#### Memory Management
- **Client**: Load entire file into memory for encryption (consider streaming for large files)
- **Server**: Process received data in chunks to handle large files efficiently
- **Cleanup**: Ensure proper cleanup of sensitive data (keys) from memory

### Testing Checklist

- [ ] New client registration
- [ ] File transfer with correct CRC
- [ ] File transfer with CRC mismatch and retry
- [ ] Client reconnection after restart
- [ ] Multiple concurrent clients
- [ ] Large file transfers
- [ ] Network interruption handling
- [ ] Invalid protocol messages
- [ ] Database persistence (if implemented)

## Appendix: Provided Wrapper Classes

### AESWrapper

Handles AES encryption/decryption operations.

**Key Methods**:
- `GenerateKey()`: Generate random AES key
- `encrypt()`: Encrypt data with AES-CBC
- `decrypt()`: Decrypt data with AES-CBC

**Important**: Default key length is 16 bytes but specification requires 32 bytes

### RSAWrapper

Provides RSA key generation and encryption/decryption.

**Classes**:
- `RSAPublicWrapper`: Handle public key operations
- `RSAPrivateWrapper`: Handle private key operations

**Key Constants**:
- `KEYSIZE = 160`: Public key size in X.509 format
- `BITS = 1024`: RSA key size

### Base64Wrapper

Encoding/decoding for key storage in text files.

**Methods**:
- `encode()`: Convert binary to Base64
- `decode()`: Convert Base64 to binary

### Usage Example

```cpp
// Required Crypto++ includes
#include <osrng.h>      // For AutoSeededRandomPool
#include <rsa.h>        // For RSA operations
#include <base64.h>     // For Base64 encoding
#include <aes.h>        // For AES operations
#include <modes.h>      // For CBC mode
#include <filters.h>    // For StreamTransformationFilter

// Generate RSA keys
RSAPrivateWrapper rsaPrivate;
std::string publicKey = rsaPrivate.getPublicKey();  // 160 bytes

// AES encryption with correct key size
unsigned char aesKey[32];  // 256 bits - NOT the default 16!
AESWrapper aes(aesKey, 32);
std::string encrypted = aes.encrypt(plaintext.c_str(), plaintext.length());

// Base64 encode private key for me.info storage
std::string privateKeyBase64 = Base64Wrapper::encode(rsaPrivate.getPrivateKey());
```

---

*This specification provides complete implementation details for the encrypted file backup system. All components must strictly adhere to the protocol for interoperability.*

## Implementation Summary for LLMs

### Core System Facts
- **Server**: Python 3.11.4 with PyCryptodome, multi-threaded or async
- **Client**: C++17 with Crypto++, Visual Studio 2022, batch mode
- **Protocol**: Binary TCP, version 3, little-endian, no chunking
- **Encryption**: RSA-1024 with OAEP-SHA256, AES-256-CBC with zero IV
- **Checksum**: Linux `cksum` algorithm (NOT standard CRC-32)

### Critical Implementation Rules
1. **NEVER** re-register if `me.info` exists
2. **ALWAYS** generate new AES key on reconnection
3. **ALWAYS** use 32-byte AES keys (not wrapper default)
4. **ALWAYS** send files as single packet (no chunking)
5. **ALWAYS** pad strings to 255 bytes with null termination
6. **ALWAYS** use little-endian for ALL numeric fields
7. **ALWAYS** calculate CRC on decrypted (original) file data
8. **NEVER** store encrypted files on server
9. **NEVER** send RSA private key to server
10. **ALWAYS** bind server to 0.0.0.0 for all interfaces

### Message Flow Summary
1. New client: 1025→1600→1026→1602→1028→1603→(1029/1030/1031)→1604
2. Returning client: 1027→(1605/1606)→[if 1605: continue with file transfer]
3. File retry: Can send 1028 up to 3 times total before giving up

### Key Data Formats
- **UUID**: 16 bytes binary in protocol, 32 hex chars in files
- **RSA Public Key**: Exactly 160 bytes in Crypto++ X.509 format
- **Strings**: 255 bytes, ASCII, null-terminated, zero-padded
- **Port**: Read from `port.info` or default to 1256
- **Config Files**: Exactly 3 lines each, no empty lines