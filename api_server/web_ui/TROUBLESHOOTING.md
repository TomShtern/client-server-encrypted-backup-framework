# Web UI Troubleshooting Guide

## Quick Start: Running the Web UI Correctly

### Recommended Startup Procedure

**IMPORTANT**: Always use these steps to ensure clean startup:

```bash
# Step 1: Kill any existing API server processes (prevents connection leaks)
# Windows PowerShell:
Get-Process python | Where-Object {$_.CommandLine -like "*cyberbackup_api_server*"} | Stop-Process -Force

# Or using tasklist/taskkill:
tasklist | findstr python
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *cyberbackup_api_server*"

# Step 2: Verify port 9090 is free
netstat -ano | findstr ":9090"
# If anything shows up, kill that PID: taskkill /F /PID <PID>

# Step 3: Start the API server cleanly
cd C:\Users\tom7s\Desktopp\Claude_Folder_2\Client_Server_Encrypted_Backup_Framework
python api_server/cyberbackup_api_server.py

# Step 4: Wait for startup message
# Look for: "Running on http://127.0.0.1:9090"

# Step 5: Open browser
# Navigate to: http://127.0.0.1:9090/
# Do a hard refresh (Ctrl+Shift+R) to bypass cache
```

### What You Should See

**Server Console:**
```
======================================================================
* CyberBackup 3.0 API Server - REAL Integration
======================================================================
* API Server: http://localhost:9090
* Client GUI: http://localhost:9090/
* Health Check: http://localhost:9090/health

[ROCKET] Starting Flask API server with WebSocket support...
[OK] Unified File Monitor: Watching C:\...\received_files
 * Serving Flask app 'cyberbackup_api_server'
 * Running on http://127.0.0.1:9090
Press CTRL+C to quit
```

**Browser Console (F12 → Console):**
```
[App] Initializing CyberBackup client...
[ConnectionMonitor] Starting health checks
[SocketClient] Socket.IO client initialized
```

**Successful HTTP Requests in Server Log:**
```
127.0.0.1 - - [DD/Mon/YYYY HH:MM:SS] "GET / HTTP/1.1" 200 -
127.0.0.1 - - [DD/Mon/YYYY HH:MM:SS] "GET /css/styles.css HTTP/1.1" 200 -
127.0.0.1 - - [DD/Mon/YYYY HH:MM:SS] "GET /js/core-utils.js HTTP/1.1" 200 -
```

---

## Common Issues and Solutions

### Issue 1: Infinite Loading Spinner (Blank White Page)

**Symptoms:**
- Browser shows blank white page
- Loading spinner spins forever
- No console errors in browser DevTools
- Server log shows "Running on http://127.0.0.1:9090" but NO HTTP requests

**Root Cause:**
Connection leak in Flask server - the server process has exhausted its file descriptor limit due to connections stuck in CLOSE_WAIT state.

**How to Diagnose:**
```bash
# Check for connections stuck in CLOSE_WAIT
netstat -ano | findstr ":9090"

# Look for many lines like this:
# TCP    127.0.0.1:9090    127.0.0.1:xxxxx    CLOSE_WAIT    <PID>
```

If you see **10+ connections in CLOSE_WAIT state**, the server is zombie and cannot handle new requests.

**Solution:**
```bash
# 1. Kill the zombie server process
# Find the PID from netstat output
taskkill /F /PID <PID>

# Or kill all Python processes (nuclear option)
taskkill /F /IM python.exe

# 2. Wait 5 seconds for port to be fully released
timeout /t 5

# 3. Start fresh
python api_server/cyberbackup_api_server.py

# 4. Hard refresh browser (Ctrl+Shift+R)
```

**Prevention:**
- Don't run multiple instances of the API server
- Always kill the server with Ctrl+C (graceful shutdown)
- If server becomes unresponsive, kill and restart immediately
- Monitor connection count: `netstat -ano | findstr ":9090" | find /c "ESTABLISHED"`

---

### Issue 2: Server Already Running (Port Conflict)

**Symptoms:**
```
OSError: [WinError 10048] Only one usage of each socket address is normally permitted
```

**Solution:**
```bash
# Find what's using port 9090
netstat -ano | findstr ":9090"

# Kill that process
taskkill /F /PID <PID>

# Start server again
python api_server/cyberbackup_api_server.py
```

---

### Issue 3: JavaScript Errors on Page Load

**Symptoms:**
- Browser console shows red errors
- Page partially loads but some functionality broken

**Common Errors:**

#### "Missing required element: #someId"
**Cause:** HTML and JavaScript are out of sync - JS expects DOM elements that don't exist.

**Solution:**
```bash
# Check if you're using the correct HTML file
# Should be: api_server/web_ui/index.html

# Verify with:
curl http://127.0.0.1:9090/ | findstr "title"
# Should show: <title>CyberBackup 3.0</title>
```

#### "Cannot read properties of null"
**Cause:** JavaScript trying to access DOM elements before they exist.

**Solution:** This was fixed in core-utils.js by moving DOM initialization to DOMContentLoaded event. Ensure you have the latest version:

```javascript
// core-utils.js should have:
let dom = {};

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeDom);
} else {
  initializeDom();
}
```

---

### Issue 4: Files Not Loading (404 Errors)

**Symptoms:**
```
127.0.0.1 - - [DD/Mon/YYYY HH:MM:SS] "GET /js/app.js HTTP/1.1" 404 -
```

**Solution:**
```bash
# Verify web_ui directory structure
dir api_server\web_ui\js
# Should show: app.js, core-utils.js, services.js, enhancements.js

# If files are missing, check you're in the right directory
cd C:\Users\tom7s\Desktopp\Claude_Folder_2\Client_Server_Encrypted_Backup_Framework
```

---

### Issue 5: CSS Not Loading (Page Has No Styles)

**Symptoms:**
- Page loads but looks like unstyled HTML
- No colors, no layout, plain text

**Solution:**
```bash
# Verify CSS files exist
dir api_server\web_ui\css
# Should show: styles.css, enhancements.css

# Check server log for CSS requests
# Should see:
# 127.0.0.1 - - [...] "GET /css/styles.css HTTP/1.1" 200 -

# If 404, verify HTML references correct paths
curl http://127.0.0.1:9090/ | findstr "stylesheet"
# Should show:
# <link rel="stylesheet" href="css/styles.css" />
# <link rel="stylesheet" href="css/enhancements.css" />
```

---

## Advanced Debugging

### Enable Debug Logging

**Flask Server Debug:**
```python
# In cyberbackup_api_server.py, change:
socketio.run(app, debug=True)  # Enable debug mode
```

**Browser Console Logging:**
```javascript
// In browser console, enable verbose logging:
localStorage.setItem('debug', '*');
// Reload page
```

### Monitor Server Health

**Check Server is Responsive:**
```bash
# Quick health check
curl http://127.0.0.1:9090/health

# Expected response:
# {"status":"healthy","api_server":"running", ...}

# If curl hangs for more than 3 seconds, server is zombie
```

**Monitor Active Connections:**
```bash
# Watch connection count in real-time
# PowerShell:
while ($true) {
    $count = (netstat -ano | findstr ":9090" | Measure-Object).Count;
    Write-Host "Connections: $count";
    Start-Sleep -Seconds 2
}
```

### Clean Restart (Nuclear Option)

**When Nothing Else Works:**
```bash
# 1. Kill ALL Python processes
taskkill /F /IM python.exe

# 2. Wait for ports to be released
timeout /t 10

# 3. Clear browser cache completely
# Chrome: Ctrl+Shift+Delete → "All time" → Clear data
# Or use Incognito: Ctrl+Shift+N

# 4. Start server fresh
python api_server/cyberbackup_api_server.py

# 5. Navigate to http://127.0.0.1:9090/ in incognito/private window
```

---

## Technical Details: The Connection Leak Issue

### What Happened (December 5, 2025)

**Symptom Chain:**
1. Page showed blank white screen with infinite loading spinner
2. Browser DevTools showed no console errors
3. Server log showed "Running on http://127.0.0.1:9090"
4. But NO HTTP requests appeared in server log
5. curl commands to server hung indefinitely

**Root Cause Analysis:**

```bash
# netstat revealed the problem:
netstat -ano | findstr ":9090"

# Output showed 29+ connections in CLOSE_WAIT:
TCP  127.0.0.1:9090  127.0.0.1:49667  CLOSE_WAIT  26780
TCP  127.0.0.1:9090  127.0.0.1:49753  CLOSE_WAIT  26780
TCP  127.0.0.1:9090  127.0.0.1:49956  CLOSE_WAIT  26780
# ... 26 more lines ...
```

**What is CLOSE_WAIT?**
- TCP connection state where client closed the connection
- But server never called `close()` on its socket
- Socket remains open, consuming a file descriptor
- Eventually exhausts server's fd limit (typically 1024 on Windows)

**Why Did Requests Hang?**
- Server could still `accept()` new connections (listening socket OK)
- But couldn't allocate file descriptors to handle them
- Requests entered accept queue but never got processed
- Result: infinite hang from client perspective

**The Fix:**
```bash
# Kill zombie process
taskkill /F /PID 26780

# Start fresh server
python api_server/cyberbackup_api_server.py

# Immediately saw successful requests:
# 127.0.0.1 - - [...] "GET / HTTP/1.1" 200 -
# 127.0.0.1 - - [...] "GET /css/styles.css HTTP/1.1" 200 -
```

### Why Flask Server Leaks Connections

**Contributing Factors:**

1. **Flask Development Server Limitations:**
   - Not production-grade
   - Poor connection cleanup under load
   - No connection timeout enforcement

2. **WebSocket Connection Management:**
   - Socket.IO creates persistent connections
   - Browser refreshes during development don't always close cleanly
   - Server cleanup thread may not keep up

3. **Multiple Server Instances:**
   - Running multiple API servers accidentally
   - Each holding partial connection state
   - Port conflicts causing zombie processes

### Prevention Best Practices

**For Development:**
```python
# In cyberbackup_api_server.py:

# Force connection close on all HTTP responses
@app.after_request
def force_connection_close(response):
    response.headers["Connection"] = "close"
    response.headers["Keep-Alive"] = "timeout=1, max=1"
    return response

# Aggressive WebSocket cleanup
socketio = SocketIO(
    app,
    ping_interval=10,   # More frequent pings
    ping_timeout=20,    # Shorter timeout
    always_connect=False  # Don't keep alive unnecessarily
)
```

**For Production:**
- Use production WSGI server (gunicorn, waitress, uWSGI)
- Enable connection pooling
- Set hard connection limits
- Monitor fd usage: `lsof -p <PID> | wc -l` (Linux) or Process Explorer (Windows)

---

## File Change History

**December 5, 2025 - Connection Leak Fix:**

**Files Modified:**
- `api_server/web_ui/js/core-utils.js`: Moved DOM initialization to DOMContentLoaded
- `api_server/web_ui/css/enhancements.css`: Created minimal version (previously deleted)
- `api_server/web_ui/index.html`: Restored enhancements.css link

**Issue Resolved:**
- Server connection leak (29+ CLOSE_WAIT connections)
- Solution: Kill zombie process (PID 26780), restart fresh

**Prevention Added:**
- This troubleshooting guide
- Updated CLAUDE.md with startup procedures

---

## Quick Reference Commands

```bash
# Check if server is running
netstat -ano | findstr ":9090"

# Kill all Python processes
taskkill /F /IM python.exe

# Start API server
cd C:\Users\tom7s\Desktopp\Claude_Folder_2\Client_Server_Encrypted_Backup_Framework
python api_server/cyberbackup_api_server.py

# Test server health
curl http://127.0.0.1:9090/health

# Hard refresh browser
Ctrl + Shift + R

# Open browser incognito
Ctrl + Shift + N (Chrome)
Ctrl + Shift + P (Firefox)
```

---

**Last Updated:** December 5, 2025
**Related Files:**
- `api_server/web_ui/CLAUDE.md` - Web GUI architecture
- `CLAUDE.md` - Main project documentation
- `api_server/cyberbackup_api_server.py` - Flask API server
