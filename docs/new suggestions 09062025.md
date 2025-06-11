<UPDATED_CODE># Realistic Enhancement Suggestions for Client-Server Encrypted Backup Framework

## Table of Contents
1. [Immediate Practical Improvements](#immediate-practical-improvements)
2. [User Experience Enhancements](#user-experience-enhancements)
3. [Operational & Maintenance Features](#operational--maintenance-features)
4. [Security Hardening](#security-hardening)
5. [Performance Optimizations](#performance-optimizations)
6. [Enterprise-Ready Features](#enterprise-ready-features)
7. [Modern Development Practices](#modern-development-practices)
8. [Deployment & Infrastructure](#deployment--infrastructure)

---

## Immediate Practical Improvements

### 📁 **File Management Enhancements**

#### **Incremental Backup Support**
```cpp:client/src/incremental_backup.cpp
// Track file changes for incremental backups
class IncrementalBackup {
    struct FileSnapshot {
        std::string filepath;
        std::time_t last_modified;
        uint64_t file_size;
        std::string checksum;
    };
    
    std::vector<std::string> getChangedFiles(const std::string& directory) {
        // Compare current state with last snapshot
        // Only backup modified/new files
        // Reduce bandwidth and storage usage
        // SQLite database for tracking changes
    }
    
    void createSnapshot(const std::string& directory) {
        // Save current directory state
        // File modification times
        // File sizes and checksums
        // Hierarchical directory structure
    }
};
```

#### **File Compression**
```python:server/compression.py
# Add compression before encryption
import zlib
import lz4

class FileCompressor:
    def compress_file(self, file_data, algorithm='zlib'):
        """Compress file data before encryption"""
        if algorithm == 'zlib':
            return zlib.compress(file_data, level=6)
        elif algorithm == 'lz4':
            return lz4.frame.compress(file_data)
        elif algorithm == 'gzip':
            return gzip.compress(file_data)
        
    def get_compression_ratio(self, original_size, compressed_size):
        return (1 - compressed_size / original_size) * 100
```

#### **Directory Backup Support**
```cpp:client/src/directory_backup.cpp
// Backup entire directories recursively
class DirectoryBackup {
    void backupDirectory(const std::filesystem::path& directory) {
        // Recursive directory traversal
        // Maintain directory structure
        // Handle symbolic links
        // Skip system/temporary files
        
        for (const auto& entry : std::filesystem::recursive_directory_iterator(directory)) {
            if (entry.is_regular_file()) {
                this->backupSingleFile(entry.path());
            }
        }
    }
    
    void restoreDirectory(const std::string& backup_id, const std::filesystem::path& restore_path) {
        // Recreate directory structure
        // Restore file permissions
        // Handle file conflicts
        // Progress reporting
    }
};
```

### 🔄 **Resume & Recovery**

#### **Transfer Resume Capability**
```python:server/transfer_manager.py
# Resume interrupted transfers
class TransferManager:
    def save_transfer_state(self, transfer_id, bytes_sent, total_bytes):
        """Save transfer progress to disk"""
        state = {
            'transfer_id': transfer_id,
            'bytes_sent': bytes_sent,
            'total_bytes': total_bytes,
            'timestamp': datetime.now(),
            'chunk_map': self.completed_chunks
        }
        
        with open(f'transfer_{transfer_id}.state', 'w') as f:
            json.dump(state, f)
    
    def resume_transfer(self, transfer_id):
        """Resume from last saved state"""
        try:
            with open(f'transfer_{transfer_id}.state', 'r') as f:
                state = json.load(f)
                return self.continue_from_chunk(state['chunk_map'])
        except FileNotFoundError:
            return self.start_new_transfer()
```

#### **Automatic Retry with Exponential Backoff**
```cpp:client/src/retry_manager.cpp
// Robust retry mechanism
class RetryManager {
    bool executeWithRetry(std::function<bool()> operation, int maxRetries = 3) {
        int attempt = 0;
        int delay = 1000; // Start with 1 second
        
        while (attempt < maxRetries) {
            if (operation()) {
                return true; // Success
            }
            
            attempt++;
            if (attempt < maxRetries) {
                std::this_thread::sleep_for(std::chrono::milliseconds(delay));
                delay *= 2; // Exponential backoff
            }
        }
        
        return false; // All attempts failed
    }
};
```

---

## User Experience Enhancements

### 🖥️ **Command Line Interface Improvements**

#### **Interactive Configuration Wizard**
```python:server/config_wizard.py
# User-friendly setup process
class ConfigurationWizard:
    def run_setup_wizard(self):
        """Interactive setup for first-time users"""
        print("Welcome to Secure Backup Setup!")
        
        # Server configuration
        server_ip = input("Enter server IP address [127.0.0.1]: ") or "127.0.0.1"
        server_port = input("Enter server port [1256]: ") or "1256"
        
        # User credentials
        username = input("Enter your username: ")
        
        # File selection
        backup_path = input("Enter path to backup: ")
        
        # Save configuration
        self.save_configuration(server_ip, server_port, username, backup_path)
        print("Configuration saved successfully!")
```

#### **Progress Indicators and Status**
```cpp:client/src/progress_indicator.cpp
// Visual progress feedback
class ProgressIndicator {
    void showTransferProgress(uint64_t bytesTransferred, uint64_t totalBytes) {
        double percentage = (double)bytesTransferred / totalBytes * 100;
        int barWidth = 50;
        int progress = (int)(percentage / 100 * barWidth);
        
        std::cout << "\r[";
        for (int i = 0; i < barWidth; ++i) {
            if (i < progress) std::cout << "=";
            else if (i == progress) std::cout << ">";
            else std::cout << " ";
        }
        std::cout << "] " << std::fixed << std::setprecision(1) 
                  << percentage << "% (" 
                  << formatBytes(bytesTransferred) << "/" 
                  << formatBytes(totalBytes) << ")";
        std::cout.flush();
    }
    
    std::string formatBytes(uint64_t bytes) {
        const char* units[] = {"B", "KB", "MB", "GB", "TB"};
        int unit = 0;
        double size = bytes;
        
        while (size >= 1024 && unit < 4) {
            size /= 1024;
            unit++;
        }
        
        return std::to_string((int)size) + " " + units[unit];
    }
};
```

### 📋 **Configuration Management**

#### **Configuration File Validation**
```python:server/config_validator.py
# Validate configuration files
class ConfigValidator:
    def validate_transfer_info(self, filepath):
        """Validate transfer.info format"""
        try:
            with open(filepath, 'r') as f:
                lines = f.readlines()
            
            if len(lines) < 3:
                raise ValueError("transfer.info must have at least 3 lines")
            
            # Validate server address
            server_line = lines[0].strip()
            if ':' not in server_line:
                raise ValueError("Invalid server address format")
            
            ip, port = server_line.split(':')
            if not self.is_valid_ip(ip) or not self.is_valid_port(port):
                raise ValueError("Invalid IP address or port")
            
            # Validate username
            username = lines[1].strip()
            if len(username) == 0 or len(username) > 100:
                raise ValueError("Username must be 1-100 characters")
            
            # Validate file path
            filepath = lines[2].strip()
            if not os.path.exists(filepath):
                raise ValueError(f"File not found: {filepath}")
            
            return True
            
        except Exception as e:
            print(f"Configuration validation error: {e}")
            return False
```

#### **Multiple Profile Support**
```cpp:client/src/profile_manager.cpp
// Support multiple backup profiles
class ProfileManager {
    struct BackupProfile {
        std::string name;
        std::string server_address;
        uint16_t server_port;
        std::string username;
        std::vector<std::string> backup_paths;
        std::string schedule; // "daily", "weekly", etc.
    };
    
    void createProfile(const std::string& profileName) {
        BackupProfile profile;
        profile.name = profileName;
        
        // Interactive profile creation
        std::cout << "Creating profile: " << profileName << std::endl;
        // ... collect profile information
        
        this->saveProfile(profile);
    }
    
    void listProfiles() {
        std::cout << "Available backup profiles:" << std::endl;
        for (const auto& profile : this->loadAllProfiles()) {
            std::cout << "  - " << profile.name 
                      << " (" << profile.server_address << ")" << std::endl;
        }
    }
};
```

---

## Operational & Maintenance Features

### 📊 **Logging and Monitoring**

#### **Structured Logging**
```python:server/structured_logger.py
# Comprehensive logging system
import logging
import json
from datetime import datetime

class StructuredLogger:
    def __init__(self, log_file="backup.log"):
        self.logger = logging.getLogger("SecureBackup")
        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def log_transfer_start(self, filename, file_size, client_id):
        event = {
            'event_type': 'transfer_start',
            'filename': filename,
            'file_size': file_size,
            'client_id': client_id,
            'timestamp': datetime.now().isoformat()
        }
        self.logger.info(json.dumps(event))
    
    def log_security_event(self, event_type, client_id, details):
        event = {
            'event_type': 'security_event',
            'security_event_type': event_type,
            'client_id': client_id,
            'details': details,
            'timestamp': datetime.now().isoformat()
        }
        self.logger.warning(json.dumps(event))
```

#### **Health Check Endpoints**
```python:server/health_checker.py
# Server health monitoring
class HealthChecker:
    def check_server_health(self):
        """Comprehensive server health check"""
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'checks': {}
        }
        
        # Database connectivity
        try:
            self.database.execute("SELECT 1")
            health_status['checks']['database'] = 'ok'
        except Exception as e:
            health_status['checks']['database'] = f'error: {str(e)}'
            health_status['status'] = 'unhealthy'
        
        # Disk space
        disk_usage = shutil.disk_usage('/')
        free_space_gb = disk_usage.free / (1024**3)
        if free_space_gb < 1:  # Less than 1GB free
            health_status['checks']['disk_space'] = f'warning: {free_space_gb:.1f}GB free'
            health_status['status'] = 'degraded'
        else:
            health_status['checks']['disk_space'] = f'ok: {free_space_gb:.1f}GB free'
        
        # Memory usage
        memory = psutil.virtual_memory()
        if memory.percent > 90:
            health_status['checks']['memory'] = f'warning: {memory.percent}% used'
            health_status['status'] = 'degraded'
        else:
            health_status['checks']['memory'] = f'ok: {memory.percent}% used'
        
        return health_status
```

### 🔧 **Administrative Tools**

#### **Client Management Interface**
```python:server/admin_interface.py
# Server administration tools
class AdminInterface:
    def list_connected_clients(self):
        """Show currently connected clients"""
        clients = self.database.execute("""
            SELECT id, name, last_seen, 
                   COUNT(f.filename) as file_count,
                   SUM(f.file_size) as total_size
            FROM clients c
            LEFT JOIN files f ON c.id = f.client_id
            WHERE c.last_seen > datetime('now', '-1 hour')
            GROUP BY c.id, c.name, c.last_seen
        """).fetchall()
        
        print(f"{'Client ID':<36} {'Name':<20} {'Files':<8} {'Size':<12} {'Last Seen'}")
        print("-" * 90)
        for client in clients:
            print(f"{client[0]:<36} {client[1]:<20} {client[3]:<8} "
                  f"{self.format_size(client[4]):<12} {client[2]}")
    
    def revoke_client_access(self, client_id):
        """Revoke access for a specific client"""
        self.database.execute(
            "UPDATE clients SET active = 0 WHERE id = ?", 
            (client_id,)
        )
        print(f"Access revoked for client: {client_id}")
    
    def cleanup_old_files(self, days_old=30):
        """Remove files older than specified days"""
        cutoff_date = datetime.now() - timedelta(days=days_old)
        
        old_files = self.database.execute("""
            SELECT pathname FROM files 
            WHERE created_date < ?
        """, (cutoff_date,)).fetchall()
        
        for file_path in old_files:
            try:
                os.remove(file_path[0])
                print(f"Removed old file: {file_path[0]}")
            except OSError as e:
                print(f"Error removing {file_path[0]}: {e}")
        
        # Clean up database records
        self.database.execute("DELETE FROM files WHERE created_date < ?", (cutoff_date,))
```

---

## Security Hardening

### 🔐 **Authentication Improvements**

#### **Rate Limiting**
````python:server/rate_limiter.py
# Prevent brute force attacks
from collections import defaultdict
from time import time

class RateLimiter:
    def __init__(self, max_attempts=5, window_seconds=300):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.attempts = defaultdict(list)
    
    def is_allowed(self, client_ip):
        """Check if client is allowed to make request"""
        now = time()
        client_attempts = self.attempts[client_ip]
        
        # Remove old attempts outside the window

        self.attempts[client_ip] = [
            attempt_time for attempt_time in client_attempts 
            if now - attempt_time < self.window_seconds
        ]
        
        # Check if under the limit
        if len(self.attempts[client_ip]) >= self.max_attempts:
            return False
        
        # Record this attempt
        self.attempts[client_ip].append(now)
        return True
    
    def get_lockout_time(self, client_ip):
        """Get remaining lockout time in seconds"""
        if client_ip not in self.attempts:
            return 0
        
        oldest_attempt = min(self.attempts[client_ip])
        time_since_oldest = time() - oldest_attempt
        return max(0, self.window_seconds - time_since_oldest)
```

#### **Input Validation and Sanitization**
```cpp:client/src/input_validator.cpp
// Robust input validation
class InputValidator {
    bool isValidUsername(const std::string& username) {
        // Length check
        if (username.length() == 0 || username.length() > 100) {
            return false;
        }
        
        // Character whitelist (alphanumeric + safe symbols)
        const std::regex valid_pattern("^[a-zA-Z0-9._-]+$");
        if (!std::regex_match(username, valid_pattern)) {
            return false;
        }
        
        // Prevent reserved names
        const std::vector<std::string> reserved = {
            "admin", "root", "system", "null", "undefined"
        };
        
        std::string lower_username = username;
        std::transform(lower_username.begin(), lower_username.end(), 
                      lower_username.begin(), ::tolower);
        
        return std::find(reserved.begin(), reserved.end(), lower_username) == reserved.end();
    }
    
    bool isValidFilename(const std::string& filename) {
        // Prevent path traversal attacks
        if (filename.find("..") != std::string::npos ||
            filename.find("/") != std::string::npos ||
            filename.find("\\") != std::string::npos) {
            return false;
        }
        
        // Length check
        if (filename.length() == 0 || filename.length() > 255) {
            return false;
        }
        
        // Prevent dangerous filenames
        const std::vector<std::string> dangerous = {
            "CON", "PRN", "AUX", "NUL", "COM1", "LPT1"
        };
        
        return std::find(dangerous.begin(), dangerous.end(), filename) == dangerous.end();
    }
    
    std::vector<uint8_t> sanitizePayload(const std::vector<uint8_t>& payload, size_t maxSize) {
        // Size validation
        if (payload.size() > maxSize) {
            throw std::invalid_argument("Payload too large");
        }
        
        // Return copy to prevent modification of original
        return std::vector<uint8_t>(payload.begin(), payload.end());
    }
};
```

### 🛡️ **Security Monitoring**

#### **Intrusion Detection**
```python:server/intrusion_detector.py
# Basic intrusion detection system
class IntrusionDetector:
    def __init__(self):
        self.suspicious_patterns = [
            r'\.\./',  # Path traversal
            r'<script',  # XSS attempts
            r'union.*select',  # SQL injection
            r'exec\(',  # Code execution
        ]
        self.failed_attempts = defaultdict(int)
        self.alert_threshold = 10
    
    def analyze_request(self, client_ip, request_data):
        """Analyze incoming request for suspicious patterns"""
        request_str = str(request_data).lower()
        
        for pattern in self.suspicious_patterns:
            if re.search(pattern, request_str, re.IGNORECASE):
                self.log_security_event(
                    'suspicious_pattern_detected',
                    client_ip,
                    {'pattern': pattern, 'request': request_str[:100]}
                )
                return False
        
        return True
    
    def record_failed_attempt(self, client_ip, attempt_type):
        """Record failed authentication/authorization attempts"""
        self.failed_attempts[client_ip] += 1
        
        if self.failed_attempts[client_ip] >= self.alert_threshold:
            self.trigger_security_alert(client_ip, attempt_type)
    
    def trigger_security_alert(self, client_ip, event_type):
        """Trigger security alert for suspicious activity"""
        alert = {
            'timestamp': datetime.now().isoformat(),
            'client_ip': client_ip,
            'event_type': event_type,
            'failed_attempts': self.failed_attempts[client_ip],
            'severity': 'high'
        }
        
        # Log to security log
        logging.getLogger('security').critical(json.dumps(alert))
        
        # Could also send email, webhook, etc.
        self.send_security_notification(alert)
```

#### **Audit Trail**
```python:server/audit_logger.py
# Comprehensive audit logging
class AuditLogger:
    def __init__(self, audit_file="audit.log"):
        self.audit_logger = logging.getLogger("audit")
        handler = logging.FileHandler(audit_file)
        formatter = logging.Formatter('%(asctime)s - AUDIT - %(message)s')
        handler.setFormatter(formatter)
        self.audit_logger.addHandler(handler)
        self.audit_logger.setLevel(logging.INFO)
    
    def log_user_action(self, user_id, action, resource, result, client_ip=None):
        """Log user actions for compliance"""
        audit_event = {
            'user_id': user_id,
            'action': action,
            'resource': resource,
            'result': result,
            'client_ip': client_ip,
            'timestamp': datetime.now().isoformat(),
            'session_id': self.get_session_id()
        }
        
        self.audit_logger.info(json.dumps(audit_event))
    
    def log_system_event(self, event_type, details):
        """Log system-level events"""
        system_event = {
            'event_type': 'system',
            'system_event': event_type,
            'details': details,
            'timestamp': datetime.now().isoformat()
        }
        
        self.audit_logger.info(json.dumps(system_event))
    
    def generate_audit_report(self, start_date, end_date, user_id=None):
        """Generate audit report for specified period"""
        # Read audit log and filter by date range and user
        # Generate summary statistics
        # Export to CSV or PDF format
        pass
```

---

## Performance Optimizations

### ⚡ **Network Optimizations**

#### **Connection Pooling**
```cpp:client/src/connection_pool.cpp
// Reuse connections for better performance
class ConnectionPool {
private:
    std::queue<std::unique_ptr<tcp::socket>> available_connections;
    std::mutex pool_mutex;
    std::string server_host;
    uint16_t server_port;
    size_t max_connections;
    
public:
    ConnectionPool(const std::string& host, uint16_t port, size_t max_conn = 10)
        : server_host(host), server_port(port), max_connections(max_conn) {}
    
    std::unique_ptr<tcp::socket> getConnection() {
        std::lock_guard<std::mutex> lock(pool_mutex);
        
        if (!available_connections.empty()) {
            auto conn = std::move(available_connections.front());
            available_connections.pop();
            
            // Test if connection is still alive
            if (isConnectionAlive(conn.get())) {
                return conn;
            }
        }
        
        // Create new connection
        return createNewConnection();
    }
    
    void returnConnection(std::unique_ptr<tcp::socket> conn) {
        std::lock_guard<std::mutex> lock(pool_mutex);
        
        if (available_connections.size() < max_connections && 
            isConnectionAlive(conn.get())) {
            available_connections.push(std::move(conn));
        }
        // Otherwise, connection will be destroyed
    }
    
private:
    bool isConnectionAlive(tcp::socket* socket) {
        // Simple check - try to read with timeout
        boost::system::error_code ec;
        socket->available(ec);
        return !ec;
    }
};
```

#### **Adaptive Chunk Sizing**
```python:server/adaptive_chunking.py
# Dynamically adjust chunk size based on network conditions
class AdaptiveChunking:
    def __init__(self):
        self.current_chunk_size = 64 * 1024  # Start with 64KB
        self.min_chunk_size = 8 * 1024       # 8KB minimum
        self.max_chunk_size = 2 * 1024 * 1024  # 2MB maximum
        self.transfer_times = []
        self.adjustment_threshold = 5  # Adjust after 5 measurements
    
    def get_optimal_chunk_size(self):
        """Calculate optimal chunk size based on recent performance"""
        if len(self.transfer_times) < self.adjustment_threshold:
            return self.current_chunk_size
        
        # Calculate average transfer rate
        recent_times = self.transfer_times[-self.adjustment_threshold:]
        avg_time = sum(recent_times) / len(recent_times)
        
        # Adjust chunk size based on performance
        if avg_time < 0.1:  # Very fast - increase chunk size
            self.current_chunk_size = min(
                self.current_chunk_size * 2, 
                self.max_chunk_size
            )
        elif avg_time > 1.0:  # Slow - decrease chunk size
            self.current_chunk_size = max(
                self.current_chunk_size // 2, 
                self.min_chunk_size
            )
        
        return self.current_chunk_size
    
    def record_transfer_time(self, chunk_size, transfer_time):
        """Record transfer performance for optimization"""
        self.transfer_times.append(transfer_time)
        
        # Keep only recent measurements
        if len(self.transfer_times) > 20:
            self.transfer_times = self.transfer_times[-20:]
```

### 💾 **Storage Optimizations**

#### **File Deduplication**
```python:server/file_deduplicator.py
# Eliminate duplicate files to save storage
import hashlib

class FileDeduplicator:
    def __init__(self, storage_path):
        self.storage_path = storage_path
        self.hash_index = {}  # hash -> file_path mapping
        self.load_existing_hashes()
    
    def calculate_file_hash(self, file_data):
        """Calculate SHA-256 hash of file content"""
        hasher = hashlib.sha256()
        hasher.update(file_data)
        return hasher.hexdigest()
    
    def store_file_deduplicated(self, file_data, filename, client_id):
        """Store file with deduplication"""
        file_hash = self.calculate_file_hash(file_data)
        
        if file_hash in self.hash_index:
            # File already exists - create reference instead of duplicate
            existing_path = self.hash_index[file_hash]
            reference_path = self.create_file_reference(
                existing_path, filename, client_id
            )
            
            return {
                'stored_path': reference_path,
                'deduplicated': True,
                'original_path': existing_path,
                'space_saved': len(file_data)
            }
        else:
            # New file - store normally
            storage_path = self.get_storage_path(filename, client_id)
            
            with open(storage_path, 'wb') as f:
                f.write(file_data)
            
            self.hash_index[file_hash] = storage_path
            self.save_hash_index()
            
            return {
                'stored_path': storage_path,
                'deduplicated': False,
                'space_saved': 0
            }
    
    def create_file_reference(self, original_path, filename, client_id):
        """Create a reference/link to existing file"""
        ref_path = self.get_storage_path(filename, client_id)
        
        # Create hard link (or symbolic link on some systems)
        try:
            os.link(original_path, ref_path)
        except OSError:
            # Fallback to copying if hard links not supported
            shutil.copy2(original_path, ref_path)
        
        return ref_path
```

#### **Database Optimization**
```python:server/database_optimizer.py
# Optimize database operations
class DatabaseOptimizer:
    def __init__(self, db_connection):
        self.db = db_connection
        self.setup_optimizations()
    
    def setup_optimizations(self):
        """Apply database optimizations"""
        # Create indexes for common queries
        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_clients_name 
            ON clients(Name)
        """)
        
        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_files_client_id 
            ON files(ID)
        """)
        
        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_files_filename 
            ON files(FileName)
        """)
        
        # Enable WAL mode for better concurrency
        self.db.execute("PRAGMA journal_mode=WAL")
        
        # Optimize SQLite settings
        self.db.execute("PRAGMA synchronous=NORMAL")
        self.db.execute("PRAGMA cache_size=10000")
        self.db.execute("PRAGMA temp_store=MEMORY")
    
    def batch_insert_files(self, file_records):
        """Efficiently insert multiple file records"""
        self.db.executemany("""
            INSERT INTO files (ID, FileName, PathName, Verified)
            VALUES (?, ?, ?, ?)
        """, file_records)
        
        self.db.commit()
    
    def cleanup_database(self):
        """Perform database maintenance"""
        # Remove orphaned records
        self.db.execute("""
            DELETE FROM files 
            WHERE ID NOT IN (SELECT ID FROM clients)
        """)
        
        # Vacuum to reclaim space
        self.db.execute("VACUUM")
        
        # Update statistics
        self.db.execute("ANALYZE")
```

---

## Enterprise-Ready Features

### 🏢 **Multi-User Support**

#### **User Groups and Permissions**
```python:server/user_manager.py
# Role-based access control
class UserManager:
    def __init__(self, db_connection):
        self.db = db_connection
        self.setup_user_tables()
    
    def setup_user_tables(self):
        """Create user management tables"""
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS user_groups (
                group_id TEXT PRIMARY KEY,
                group_name TEXT UNIQUE NOT NULL,
                description TEXT,
                created_date DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS user_group_members (
                user_id TEXT,
                group_id TEXT,
                added_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, group_id),
                FOREIGN KEY (user_id) REFERENCES clients(ID),
                FOREIGN KEY (group_id) REFERENCES user_groups(group_id)
            )
        """)
        
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS permissions (
                permission_id TEXT PRIMARY KEY,
                permission_name TEXT UNIQUE NOT NULL,
                description TEXT
            )
        """)
        
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS group_permissions (
                group_id TEXT,
                permission_id TEXT,
                granted_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (group_id, permission_id),
                FOREIGN KEY (group_id) REFERENCES user_groups(group_id),
                FOREIGN KEY (permission_id) REFERENCES permissions(permission_id)
            )
        """)
    
    def create_group(self, group_name, description=""):
        """Create a new user group"""
        group_id = str(uuid.uuid4())
        
        self.db.execute("""
            INSERT INTO user_groups (group_id, group_name, description)
            VALUES (?, ?, ?)
        """, (group_id, group_name, description))
        
        return group_id
    
    def add_user_to_group(self, user_id, group_id):
        """Add user to a group"""
        self.db.execute("""
            INSERT OR IGNORE INTO user_group_members (user_id, group_id)
            VALUES (?, ?)
        """, (user_id, group_id))
    
    def check_user_permission(self, user_id, permission_name):
        """Check if user has specific permission"""
        result = self.db.execute("""
            SELECT COUNT(*) FROM user_group_members ugm
            JOIN group_permissions gp ON ugm.group_id = gp.group_id
            JOIN permissions p ON gp.permission_id = p.permission_id
            WHERE ugm.user_id = ? AND p.permission_name = ?
        """, (user_id, permission_name)).fetchone()
        
        return result[0] > 0
```

#### **Quota Management**
```python:server/quota_manager.py
# Storage quota management
class QuotaManager:
    def __init__(self, db_connection):
        self.db = db_connection
        self.setup_quota_tables()
    
    def setup_quota_tables(self):
        """Create quota management tables"""
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS user_quotas (
                user_id TEXT PRIMARY KEY,
                storage_limit_bytes INTEGER NOT NULL,
                file_count_limit INTEGER DEFAULT NULL,
                created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES clients(ID)
            )
        """)
        
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS quota_usage (
                user_id TEXT PRIMARY KEY,
                storage_used_bytes INTEGER DEFAULT 0,
                file_count INTEGER DEFAULT 0,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES clients(ID)
            )
        """)
    
    def set_user_quota(self, user_id, storage_limit_gb, file_count_limit=None):
        """Set storage quota for user"""
        storage_limit_bytes = storage_limit_gb * 1024 * 1024 * 1024
        
        self.db.execute("""
            INSERT OR REPLACE INTO user_quotas 
            (user_id, storage_limit_bytes, file_count_limit)
            VALUES (?, ?, ?)
        """, (user_id, storage_limit_bytes, file_count_limit))
    
    def check_quota_before_upload(self, user_id, file_size):
        """Check if user can upload file without exceeding quota"""
        quota_info = self.db.execute("""
            SELECT uq.storage_limit_bytes, uq.file_count_limit,
                   COALESCE(qu.storage_used_bytes, 0) as current_usage,
                   COALESCE(qu.file_count, 0) as current_files
            FROM user_quotas uq
            LEFT JOIN quota_usage qu ON uq.user_id = qu.user_id
            WHERE uq.user_id = ?
        """, (user_id,)).fetchone()
        
        if not quota_info:
            return True  # No quota set
        
        storage_limit, file_limit, current_usage, current_files = quota_info
        
        # Check storage quota
        if current_usage + file_size > storage_limit:
            return False, f"Storage quota exceeded. Limit: {storage_limit}, Current: {current_usage}, Requested: {file_size}"
        
        # Check file count quota
        if file_limit and current_files >= file_limit:
            return False, f"File count quota exceeded. Limit: {file_limit}, Current: {current_files}"
        
        return True, "OK"
    
    def update_quota_usage(self, user_id, file_size_delta, file_count_delta=0):
        """Update user's quota usage"""
        self.db.execute("""
            INSERT OR REPLACE INTO quota_usage 
            (user_id, storage_used_bytes, file_count, last_updated)
            VALUES (
                ?, 
                COALESCE((SELECT storage_used_bytes FROM quota_usage WHERE user_id = ?), 0) + ?,
                COALESCE((SELECT file_count FROM quota_usage WHERE user_id = ?), 0) + ?,
                CURRENT_TIMESTAMP
            )
        """, (user_id, user_id, file_size_delta, user_id, file_count_delta))
```

### 📈 **Backup Scheduling**

#### **Automated Backup Scheduler**
```python:server/backup_scheduler.py
# Automated backup scheduling
import schedule
import threading
from datetime import datetime, timedelta

class BackupScheduler:
    def __init__(self):
        self.scheduled_jobs = {}
        self.scheduler_thread = None
        self.running = False
    
    def start_scheduler(self):
        """Start the background scheduler thread"""
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            return
        
        self.running = True
        self.scheduler_thread = threading.Thread(target=self._run_scheduler)
        self.scheduler_thread.daemon = True
        self.scheduler_thread.start()
    
    def _run_scheduler(self):
        """Background thread to run scheduled jobs"""
        while self.running:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    def schedule_user_backup(self, user_id, backup_paths, frequency='daily', time='02:00'):
        """Schedule automatic backup for user"""
        job_id = f"backup_{user_id}"
        
        def backup_job():
            try:
                self.execute_scheduled_backup(user_id, backup_paths)
            except Exception as e:
                logging.error(f"Scheduled backup failed for user {user_id}: {e}")
        
        # Remove existing job if any
        if job_id in self.scheduled_jobs:
            schedule.cancel_job(self.scheduled_jobs[job_id])
        
        # Schedule new job
        if frequency == 'daily':
            job = schedule.every().day.at(time).do(backup_job)
        elif frequency == 'weekly':
            job = schedule.every().week.at(time).do(backup_job)
        elif frequency == 'monthly':
            job = schedule.every(30).days.at(time).do(backup_job)
        
        self.scheduled_jobs[job_id] = job
        
        logging.info(f"Scheduled {frequency} backup for user {user_id} at {time}")
    
    def execute_scheduled_backup(self, user_id, backup_paths):
        """Execute a scheduled backup"""
        logging.info(f"Starting scheduled backup for user {user_id}")
        
        # Trigger client backup (would need client-side scheduling or server-initiated backup)
        # This is a simplified example - real implementation would need more coordination
        
        backup_result = {
            'user_id': user_id,
            'backup_paths': backup_paths,
            'start_time': datetime.now(),
            'status': 'completed',
            'files_backed_up': 0,
            'total_size': 0
        }
        
        # Log backup completion
        self.log_backup_completion(backup_result)
```

#### **Backup Retention Policies**
```python:server/retention_manager.py
# Manage backup retention policies
class RetentionManager:
    def __init__(self, db_connection):
        self.db = db_connection
        self.setup_retention_tables()
    
    def setup_retention_tables(self):
        """Create retention policy tables"""
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS retention_policies (
                policy_id TEXT PRIMARY KEY,
                policy_name TEXT UNIQUE NOT NULL,
                daily_retention_days INTEGER DEFAULT 7,
                weekly_retention_weeks INTEGER DEFAULT 4,
                monthly_retention_months INTEGER DEFAULT 12,
                yearly_retention_years INTEGER DEFAULT 7,
                created_date DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS user_retention_policies (
                user_id TEXT,
                policy_id TEXT,
                assigned_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id),
                FOREIGN KEY (user_id) REFERENCES clients(ID),
                FOREIGN KEY (policy_id) REFERENCES retention_policies(policy_id)
            )
        """)
        
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS backup_versions (
                version_id TEXT PRIMARY KEY,
                user_id TEXT,
                file_path TEXT,
                backup_date DATETIME,
                file_size INTEGER,
                checksum TEXT,
                retention_category TEXT, -- 'daily', 'weekly', 'monthly', 'yearly'
                FOREIGN KEY (user_id) REFERENCES clients(ID)
            )
        """)
    
    def create_retention_policy(self, policy_name, daily=7, weekly=4, monthly=12, yearly=7):
        """Create a new retention policy"""
        policy_id = str(uuid.uuid4())
        
        self.db.execute("""
            INSERT INTO retention_policies 
            (policy_id, policy_name, daily_retention_days, weekly_retention_weeks,
             monthly_retention_months, yearly_retention_years)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (policy_id, policy_name, daily, weekly, monthly, yearly))
        
        return policy_id
    
    def apply_retention_policy(self, user_id):
        """Apply retention policy to user's backups"""
        # Get user's retention policy
        policy = self.db.execute("""
            SELECT rp.* FROM retention_policies rp
            JOIN user_retention_policies urp ON rp.policy_id = urp.policy_id
            WHERE urp.user_id = ?
        """, (user_id,)).fetchone()
        
        if not policy:
            return  # No policy assigned
        
        now = datetime.now()
        
        # Calculate cutoff dates
        daily_cutoff = now - timedelta(days=policy['daily_retention_days'])
        weekly_cutoff = now - timedelta(weeks=policy['weekly_retention_weeks'])
        monthly_cutoff = now - timedelta(days=policy['monthly_retention_months'] * 30)
        yearly_cutoff = now - timedelta(days=policy['yearly_retention_years'] * 365)
        
        # Delete expired backups
        expired_backups = self.db.execute("""
            SELECT version_id, file_path FROM backup_versions
            WHERE user_id = ? AND (
                (retention_category = 'daily' AND backup_date < ?) OR
                (retention_category = 'weekly' AND backup_date < ?) OR
                (retention_category = 'monthly' AND backup_date < ?) OR
                (retention_category = 'yearly' AND backup_date < ?)
            )
        """, (user_id, daily_cutoff, weekly_cutoff, monthly_cutoff, yearly_cutoff)).fetchall()
        
        for backup in expired_backups:
            # Delete physical file
            try:
                os.remove(backup['file_path'])
            except OSError:
                pass  # File might already be deleted
            
            # Remove from database
            self.db.execute("DELETE FROM backup_versions WHERE version_id = ?", 
                          (backup['version_id'],))
        
        logging.info(f"Applied retention policy for user {user_id}, removed {len(expired_backups)} expired backups")
```

---

## Modern Development Practices

### 🧪 **Testing Framework**

#### **Unit Testing for Server**
```python:tests/test_server_components.py
# Comprehensive unit tests for server components
import unittest
import tempfile
import os
from unittest.mock import Mock, patch

class TestCryptoOperations(unittest.TestCase):
    def setUp(self):
        self.crypto_manager = CryptoManager()
    
    def test_aes_encryption_decryption(self):
        """Test AES encryption and decryption"""
        original_data = b"This is test data for encryption"
        key = os.urandom(32)  # 256-bit key
        
        encrypted = self.crypto_manager.encrypt_aes(original_data, key)
        decrypted = self.crypto_manager.decrypt_aes(encrypted, key)
        
        self.assertEqual(original_data, decrypted)
        self.assertNotEqual(original_data, encrypted)
    
    def test_rsa_key_generation(self):
        """Test RSA key pair generation"""
        private_key, public_key = self.crypto_manager.generate_rsa_keypair()
        
        self.assertIsNotNone(private_key)
        self.assertIsNotNone(public_key)
        
        # Test encryption/decryption
        test_data = b"Test message"
        encrypted = self.crypto_manager.encrypt_rsa(test_data, public_key)
        decrypted = self.crypto_manager.decrypt_rsa(encrypted, private_key)
        
        self.assertEqual(test_data, decrypted)
    
    def test_crc_calculation(self):
        """Test CRC-32 calculation matches expected values"""
        test_cases = [
            (b"hello", 0x3610a686),
            (b"world", 0x8c736521),
            (b"", 0x00000000)
        ]
        
        for data, expected_crc in test_cases:
            calculated_crc = self.crypto_manager.calculate_crc32(data)
            self.assertEqual(calculated_crc, expected_crc)

class TestProtocolHandling(unittest.TestCase):
    def setUp(self):
        self.protocol_handler = ProtocolHandler()
    
    def test_request_parsing(self):
        """Test binary request parsing"""
        # Create test request
        client_id = b'\x01' * 16
        version = 3
        code = 1025  # Registration
        payload = b"testuser" + b'\x00' * (255 - 8)  # Padded username
        
        request_data = struct.pack('<16sBHI', client_id, version, code, len(payload)) + payload
        
        parsed = self.protocol_handler.parse_request(request_data)
        
        self.assertEqual(parsed['client_id'], client_id)
        self.assertEqual(parsed['version'], version)
        self.assertEqual(parsed['code'], code)
        self.assertEqual(parsed['payload_size'], len(payload))
    
    def test_response_creation(self):
        """Test binary response creation"""
        version = 3
        code = 1600  # Registration successful
        client_id = b'\x01' * 16
        
        response = self.protocol_handler.create_response(code, client_id)
        
        # Parse response to verify
        parsed_version, parsed_code, payload_size = struct.unpack('<BHI', response[:7])
        parsed_client_id = response[7:23]
        
        self.assertEqual(parsed_version, version)
        self.assertEqual(parsed_code, code)
        self.assertEqual(parsed_client_id, client_id)

class TestDatabaseOperations(unittest.TestCase):
    def setUp(self):
        # Use in-memory database for testing
        self.db_manager = DatabaseManager(':memory:')
        self.db_manager.initialize_database()
    
    def test_client_registration(self):
        """Test client registration process"""
        username = "testuser"
        client_id = str(uuid.uuid4())
        
        # Register client
        result = self.db_manager.register_client(username, client_id)
        self.assertTrue(result)
        
        # Verify client exists
        client = self.db_manager.get_client_by_name(username)
        self.assertIsNotNone(client)
        self.assertEqual(client['Name'], username)
        self.assertEqual(client['ID'], client_id)
    
    def test_duplicate_username_rejection(self):
        """Test that duplicate usernames are rejected"""
        username = "testuser"
        client_id1 = str(uuid.uuid4())
        client_id2 = str(uuid.uuid4())
        
        # First registration should succeed
        result1 = self.db_manager.register_client(username, client_id1)
        self.assertTrue(result1)
        
        # Second registration with same username should fail
        result2 = self.db_manager.register_client(username, client_id2)
        self.assertFalse(result2)

if __name__ == '__main__':
    unittest.main()
```

#### **Integration Testing**
```python:tests/test_integration.py
# Integration tests for client-server communication
import unittest
import threading
import time
import socket
from unittest.mock import patch

class TestClientServerIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Start test server"""
        cls.server_thread = threading.Thread(target=cls.start_test_server)
        cls.server_thread.daemon = True
        cls.server_thread.start()
        time.sleep(1)  # Give server time to start
    
    @classmethod
    def start_test_server(cls):
        """Start a test server instance"""
        from server.main import create_server
        server = create_server(port=12560)  # Use different port for testing
        server.run()
    
    def test_full_registration_flow(self):
        """Test complete client registration flow"""
        # Create test client
        client = TestClient('127.0.0.1', 12560)
        
        # Test registration
        result = client.register('testuser_integration')
        self.assertTrue(result['success'])
        self.assertIn('client_id', result)
        
        # Test public key exchange
        result = client.send_public_key()
        self.assertTrue(result['success'])
        self.assertIn('aes_key', result)
    
    def test_file_transfer_flow(self):
        """Test complete file transfer flow"""
        client = TestClient('127.0.0.1', 12560)
        
        # Register and setup encryption
        client.register('testuser_file_transfer')
        client.send_public_key()
        
        # Create test file
        test_data = b"This is test file content for integration testing"
        test_filename = "integration_test.txt"
        
        # Transfer file
        result = client.transfer_file(test_filename, test_data)
        self.assertTrue(result['success'])
        self.assertIn('checksum', result)
        
        # Verify CRC
        expected_crc = calculate_crc32(test_data)
        self.assertEqual(result['checksum'], expected_crc)

class TestClient:
    """Test client for integration testing"""
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.client_id = None
        self.aes_key = None
        self.private_key = None
        self.public_key = None
    
    def connect(self):
        """Establish connection to server"""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.host, self.port))
    
    def register(self, username):
        """Register with server"""
        self.connect()
        
        # Send registration request
        request = self.create_registration_request(username)
        self.socket.send(request)
        
        # Receive response
        response = self.receive_response()
        
        if response['code'] == 1600:  # Registration successful
            self.client_id = response['payload']
            return {'success': True, 'client_id': self.client_id}
        else:
            return {'success': False, 'error': 'Registration failed'}
```

### 📊 **Performance Monitoring**

#### **Performance Metrics Collection**
```python:server/performance_monitor.py
# Collect and analyze performance metrics
import time
import psutil
from collections import defaultdict, deque
from threading import Lock

class PerformanceMonitor:
    def __init__(self, max_samples=1000):
        self.max_samples = max_samples
        self.metrics = defaultdict(lambda: deque(maxlen=max_samples))
        self.lock = Lock()
        self.start_time = time.time()
    
    def record_metric(self, metric_name, value, timestamp=None):
        """Record a performance metric"""
        if timestamp is None:
            timestamp = time.time()
        
        with self.lock:
            self.metrics[metric_name].append({
                'value': value,
                'timestamp': timestamp
            })
    
    def record_transfer_performance(self, file_size, transfer_time, client_id):
        """Record file transfer performance"""
        throughput = file_size / transfer_time if transfer_time > 0 else 0
        
        self.record_metric('transfer_throughput', throughput)
        self.record_metric('transfer_time', transfer_time)
        self.record_metric('file_size', file_size)
        
        # Per-client metrics
        self.record_metric(f'client_{client_id}_throughput', throughput)
    
    def record_system_metrics(self):
        """Record system resource usage"""
        # CPU usage
        cpu_percent = psutil.cpu_percent()
        self.record_metric('cpu_usage', cpu_percent)
        
        # Memory usage
        memory = psutil.virtual_memory()
        self.record_metric('memory_usage', memory.percent)
        self.record_metric('memory_available', memory.available)
        
        # Disk usage
        disk = psutil.disk_usage('/')
        self.record_metric('disk_usage', disk.percent)
        self.record_metric('disk_free', disk.free)
        
        # Network I/O
        network = psutil.net_io_counters()
        self.record_metric('network_bytes_sent', network.bytes_sent)
        self.record_metric('network_bytes_recv', network.bytes_recv)
    
    def get_metric_summary(self, metric_name, time_window=3600):
        """Get summary statistics for a metric"""
        with self.lock:
            if metric_name not in self.metrics:
                return None
            
            current_time = time.time()
            cutoff_time = current_time - time_window
            
            # Filter recent samples
            recent_samples = [
                sample for sample in self.metrics[metric_name]
                if sample['timestamp'] >= cutoff_time
            ]
            
            if not recent_samples:
                return None
            
            values = [sample['value'] for sample in recent_samples]
            
            return {
                'count': len(values),
                'min': min(values),
                'max': max(values),
                'avg': sum(values) / len(values),
                'latest': values[-1] if values else None
            }
    
    def generate_performance_report(self):
        """Generate comprehensive performance report"""
        report = {
            'uptime': time.time() - self.start_time,
            'timestamp': time.time(),
            'metrics': {}
        }
        
        # Key metrics to include in report
        key_metrics = [
            'transfer_throughput', 'transfer_time', 'cpu_usage',
            'memory_usage', 'disk_usage', 'active_connections'
        ]
        
        for metric in key_metrics:
            summary = self.get_metric_summary(metric)
            if summary:
                report['metrics'][metric] = summary
        
        return report
```

#### **Automated Performance Alerts**
```python:server/performance_alerts.py
# Automated performance alerting system
class PerformanceAlerter:
    def __init__(self, monitor, alert_config):
        self.monitor = monitor
        self.alert_config = alert_config
        self.alert_history = defaultdict(list)
        self.cooldown_period = 300  # 5 minutes between similar alerts
    
    def check_performance_thresholds(self):
        """Check all configured performance thresholds"""
        alerts = []
        
        for metric_name, config in self.alert_config.items():
            summary = self.monitor.get_metric_summary(metric_name, config.get('window', 300))
            
            if not summary:
                continue
            
            # Check thresholds
            if 'max_threshold' in config and summary['avg'] > config['max_threshold']:
                alert = self.create_alert(
                    'threshold_exceeded',
                    metric_name,
                    f"{metric_name} average ({summary['avg']:.2f}) exceeds threshold ({config['max_threshold']})"
                )
                alerts.append(alert)
            
            if 'min_threshold' in config and summary['avg'] < config['min_threshold']:
                alert = self.create_alert(
                    'threshold_below',
                    metric_name,
                    f"{metric_name} average ({summary['avg']:.2f}) below threshold ({config['min_threshold']})"
                )
                alerts.append(alert)
        
        # Send alerts that aren't in cooldown
        for alert in alerts:
            if self.should_send_alert(alert):
                self.send_alert(alert)
    
    def create_alert(self, alert_type, metric_name, message):
        """Create performance alert"""
        return {
            'type': alert_type,
            'metric': metric_name,
            'message': message,
            'timestamp': time.time(),
            'severity': self.get_alert_severity(alert_type, metric_name)
        }
    
    def should_send_alert(self, alert):
        """Check if alert should be sent (not in cooldown)"""
        alert_key = f"{alert['type']}_{alert['metric']}"
        recent_alerts = [
            a for a in self.alert_history[alert_key]
            if time.time() - a['timestamp'] < self.cooldown_period
        ]
        
        return len(recent_alerts) == 0
    
    def send_alert(self, alert):
        """Send performance alert"""
        # Log alert
        logging.warning(f"PERFORMANCE ALERT: {alert['message']}")
        
        # Record in history
        alert_key = f"{alert['type']}_{alert['metric']}"
        self.alert_history[alert_key].append(alert)
        
        # Could also send email, webhook, etc.
        if alert['severity'] == 'critical':
            self.send_critical_alert_notification(alert)
```

---

## Deployment & Infrastructure

### 🐳 **Containerization**

#### **Docker Configuration**
```dockerfile:docker/server/Dockerfile
# Server Docker configuration
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY server/ ./server/
COPY docs/ ./docs/

# Create necessary directories
RUN mkdir -p /app/data /app/logs /app/uploads

# Set environment variables
ENV PYTHONPATH=/app
ENV BACKUP_DATA_DIR=/app/data
ENV BACKUP_LOG_DIR=/app/logs
ENV BACKUP_UPLOAD_DIR=/app/uploads

# Expose port
EXPOSE 1256

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import socket; socket.create_connection(('localhost', 1256), timeout=5)"

# Run application
CMD ["python", "-m", "server.main"]
```

```dockerfile:docker/client/Dockerfile
# Client Docker configuration (for testing/CI)
FROM ubuntu:22.04

# Install dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    libboost-all-dev \
    libcrypto++-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy source code