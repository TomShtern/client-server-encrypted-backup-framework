/**
 * CyberBackup Client - Services
 * Bundled: api-client, socket-client, connection-metrics, connection-monitor, file-manager, theme-manager, log-store, advanced-settings
 */

// --- Dual Server Status Helper ---
/**
 * Updates the dual server status indicators in the header.
 * @param {Object} status - Status object
 * @param {boolean} status.apiOnline - Whether the API server is online
 * @param {boolean} status.backupOnline - Whether the backup server is online
 * @param {number} [status.latency] - Optional latency in milliseconds
 */
function updateDualServerStatus({ apiOnline, backupOnline, latency }) {
  const webServerEl = document.getElementById('webServerStatus');
  const backupServerEl = document.getElementById('backupServerStatus');

  if (webServerEl) {
    const dot = webServerEl.querySelector('.status-dot');
    const text = webServerEl.querySelector('.status-text');
    if (dot) {
      dot.className = 'status-dot ' + (apiOnline ? 'online' : 'offline');
    }
    if (text) {
      text.textContent = apiOnline ? 'Online' : 'Offline';
    }
  }

  if (backupServerEl) {
    const dot = backupServerEl.querySelector('.status-dot');
    const text = backupServerEl.querySelector('.status-text');
    if (dot) {
      dot.className = 'status-dot ' + (backupOnline ? 'online' : 'offline');
    }
    if (text) {
      if (backupOnline) {
        text.textContent = latency ? `Ready (${Math.round(latency)}ms)` : 'Ready';
      } else {
        text.textContent = 'Offline';
      }
    }
  }
}

// --- services/api-client.js ---
const DEFAULT_TIMEOUT = 20000;

function withTimeout(promise, timeoutMs = DEFAULT_TIMEOUT) {
  return Promise.race([
    promise,
    new Promise((_, reject) => {
      setTimeout(() => reject(new Error('Request timed out')), timeoutMs);
    }),
  ]);
}

function normalizeResponse(response) {
  const contentType = response.headers.get('content-type') || '';
  const isJson = contentType.includes('application/json');
  return (isJson ? response.json() : response.text()).then((payload) => ({ response, payload }));
}

/**
 * REST API client for communicating with the CyberBackup server.
 * Handles connection, backup operations, and status polling.
 */
class ApiClient {
  /**
   * @param {string} [baseUrl=''] - Base URL for API endpoints (e.g., 'http://localhost:9090')
   */
  constructor(baseUrl = '') {
    this.baseUrl = baseUrl;
  }

  #buildUrl(path) {
    if (!path.startsWith('/')) {
      return `${this.baseUrl}/${path}`;
    }
    return `${this.baseUrl}${path}`;
  }

  /**
   * Performs a health check on the API server.
   * @async
   * @returns {Promise<Object>} Health status payload including system metrics
   * @throws {Error} If health check fails
   */
  async health() {
    const { response, payload } = await withTimeout(
      fetch(this.#buildUrl('/api/health'), {
        headers: { 'Cache-Control': 'no-cache' },
      }),
      8000,
    ).then(normalizeResponse);
    if (!response.ok) {
      throw new Error(payload?.error || 'Health check failed');
    }
    return payload;
  }

  /**
   * Connects to the backup server with the provided configuration.
   * @async
   * @param {Object} config - Connection configuration
   * @param {string} config.username - Username for the backup server
   * @param {string} config.host - Backup server host
   * @param {number} config.port - Backup server port
   * @returns {Promise<Object>} Connection response with server details
   * @throws {Error} If connection fails
   */
  async connect(config) {
    const body = JSON.stringify(config);
    const { response, payload } = await withTimeout(
      fetch(this.#buildUrl('/api/connect'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body,
      }),
    ).then(normalizeResponse);
    if (!response.ok || !payload?.success) {
      throw new Error(payload?.error || payload?.message || 'Failed to connect');
    }
    return payload;
  }

  /**
   * Disconnects from the backup server.
   * @async
   * @returns {Promise<Object>} Disconnection response
   * @throws {Error} If disconnection fails
   */
  async disconnect() {
    const { response, payload } = await withTimeout(
      fetch(this.#buildUrl('/api/disconnect'), { method: 'POST' }),
    ).then(normalizeResponse);
    if (!response.ok || !payload?.success) {
      throw new Error(payload?.error || 'Failed to disconnect');
    }
    return payload;
  }

  /**
   * Starts a backup operation for the specified file.
   * @async
   * @param {Object} options - Backup options
   * @param {File} options.file - File to backup (required)
   * @param {string} [options.username] - Username for authentication
   * @param {string} [options.host] - Backup server host
   * @param {number} [options.port] - Backup server port
   * @param {Object} [options.options={}] - Additional backup options (chunk_size_mb, retry_limit, etc.)
   * @returns {Promise<Object>} Backup job information including job_id
   * @throws {TypeError} If file is not a File instance
   * @throws {Error} If backup start fails
   */
  async startBackup({ file, username, host, port, options = {} }) {
    if (!(file instanceof File)) {
      throw new TypeError('A valid file must be provided');
    }
    const form = new FormData();
    form.append('file', file, file.name);
    if (username) form.append('username', username);
    if (host) form.append('host', host);
    if (port) form.append('port', String(port));

    for (const [key, value] of Object.entries(options)) {
      if (value === undefined || value === null || value === '') return;
      form.append(key, String(value));
    }

    const { response, payload } = await withTimeout(
      fetch(this.#buildUrl('/api/start_backup'), {
        method: 'POST',
        body: form,
      }),
      60000,
    ).then(normalizeResponse);
    if (!response.ok || !payload?.success) {
      throw new Error(payload?.error || payload?.message || 'Backup start failed');
    }
    return payload;
  }

  /**
   * Retrieves the current status of a backup job.
   * @async
   * @param {string} [jobId] - Job ID to check status for. If omitted, returns general status
   * @returns {Promise<Object>} Job status including progress, bytes_transferred, etc.
   * @throws {Error} If status request fails
   */
  async status(jobId) {
    const origin = globalThis.location?.origin ?? 'http://localhost';
    const url = new URL(this.#buildUrl('/api/status'), origin);
    if (jobId) {
      url.searchParams.set('job_id', jobId);
    }
    const { response, payload } = await withTimeout(
      fetch(url.toString(), { headers: { 'Cache-Control': 'no-cache' } }),
      10000,
    ).then(normalizeResponse);
    if (!response.ok) {
      throw new Error(payload?.error || 'Status request failed');
    }
    return payload;
  }

  /**
   * Pauses the currently running backup job.
   * @async
   * @returns {Promise<Object>} Pause operation response
   * @throws {Error} If pause command fails
   */
  async pause() {
    return this.#command('/api/pause');
  }

  /**
   * Resumes the currently paused backup job.
   * @async
   * @returns {Promise<Object>} Resume operation response
   * @throws {Error} If resume command fails
   */
  async resume() {
    return this.#command('/api/resume');
  }

  /**
   * Stops the currently running backup job.
   * @async
   * @returns {Promise<Object>} Stop operation response
   * @throws {Error} If stop command fails
   */
  async stop() {
    return this.#command('/api/stop');
  }

  #command(path) {
    return withTimeout(fetch(this.#buildUrl(path), { method: 'POST' })).then(async (response) => {
      const { payload } = await normalizeResponse(response);
      if (!response.ok || !payload?.success) {
        throw new Error(payload?.error || `Command failed: ${path}`);
      }
      return payload;
    });
  }
}

// --- services/socket-client.js ---
const DEFAULT_OPTIONS = {
  transports: ['websocket'],
  autoConnect: false,
  reconnection: true,
  reconnectionAttempts: Infinity,
  reconnectionDelay: 1500,
  reconnectionDelayMax: 8000,
  timeout: 8000,
  withCredentials: true,
};

const DEFAULT_SOCKET_URL =
  typeof globalThis.location === 'object' && globalThis.location
    ? globalThis.location.origin
    : '';

/**
 * WebSocket client for real-time communication with the backup server.
 * Handles connection events, progress updates, and status notifications using Socket.IO.
 */
class SocketClient {
  /**
   * @param {Object} config - Socket client configuration
   * @param {string} [config.url] - WebSocket server URL (defaults to current origin)
   * @param {Object} [config.options={}] - Socket.IO options (transports, reconnection settings, etc.)
   * @param {Function} [config.onConnect] - Callback when socket connects
   * @param {Function} [config.onDisconnect] - Callback when socket disconnects (receives disconnect reason)
   * @param {Function} [config.onError] - Callback for connection errors
   * @param {Function} [config.onStatus] - Callback for status updates
   * @param {Function} [config.onProgress] - Callback for progress updates during backup
   * @param {Function} [config.onFileReceipt] - Callback when file is received by server
   */
  constructor({ url = DEFAULT_SOCKET_URL, options = {}, onConnect, onDisconnect, onError, onStatus, onProgress, onFileReceipt }) {
    this.url = url ?? DEFAULT_SOCKET_URL;
    this.options = { ...DEFAULT_OPTIONS, ...options };
    this.onConnect = typeof onConnect === 'function' ? onConnect : () => { };
    this.onDisconnect = typeof onDisconnect === 'function' ? onDisconnect : () => { };
    this.onError = typeof onError === 'function' ? onError : () => { };
    this.onStatus = typeof onStatus === 'function' ? onStatus : () => { };
    this.onProgress = typeof onProgress === 'function' ? onProgress : () => { };
    this.onFileReceipt = typeof onFileReceipt === 'function' ? onFileReceipt : () => { };

    this.socket = null;
    this.currentJobId = null;
    this.ioFactory = null;
  }

  /**
   * Starts the WebSocket connection and sets up event listeners.
   * Loads Socket.IO library from CDN if not already available.
   * @async
   */
  async start() {
    try {
      const ioFactory = await this.#ensureIoFactory();
      this.socket = ioFactory(this.url, this.options);
    } catch (error) {
      console.warn('Socket initialization failed', error);
      this.onError(error instanceof Error ? error : new Error('Socket initialization failed'));
      return;
    }

    this.socket.on('connect', () => {
      this.onConnect();
      if (this.currentJobId) {
        this.requestStatus(this.currentJobId);
      }
    });

    this.socket.on('disconnect', (reason) => {
      this.onDisconnect(reason);
    });

    this.socket.on('connect_error', (error) => {
      this.onError(error);
    });

    this.socket.on('status', (payload) => {
      this.onStatus(payload);
    });

    this.socket.on('status_response', (payload) => {
      this.onStatus(payload);
    });

    this.socket.on('progress_update', (payload) => {
      if (this.currentJobId && payload?.job_id && payload.job_id !== this.currentJobId) {
        return;
      }
      this.onProgress(payload);
    });

    this.socket.on('file_receipt', (payload) => {
      this.onFileReceipt(payload);
    });

    this.socket.connect();
  }

  /**
   * Closes the WebSocket connection.
   */
  stop() {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
  }

  /**
   * Sets the current job ID to watch for progress updates.
   * Automatically requests status for the specified job.
   * @param {string} jobId - Job ID to monitor
   */
  watchJob(jobId) {
    this.currentJobId = jobId;
    this.requestStatus(jobId);
  }

  /**
   * Clears the current job ID being watched.
   */
  clearJob() {
    this.currentJobId = null;
  }

  /**
   * Requests status update for a specific job ID.
   * @param {string} jobId - Job ID to request status for
   */
  requestStatus(jobId) {
    if (!this.socket || !jobId) {
      return;
    }
    this.socket.emit('request_status', { job_id: jobId });
  }

  async #ensureIoFactory() {
    if (this.ioFactory) {
      return this.ioFactory;
    }

    if (globalThis.io) {
      this.ioFactory = globalThis.io;
      return this.ioFactory;
    }

    try {
      // Add 5-second timeout to CDN load
      const timeoutPromise = new Promise((_, reject) =>
        setTimeout(() => reject(new Error('Socket.IO CDN load timeout after 5s')), 5000)
      );

      const loadPromise = import('https://cdn.jsdelivr.net/npm/socket.io-client@4.7.5/dist/socket.io.esm.min.js');

      const module = await Promise.race([loadPromise, timeoutPromise]);
      this.ioFactory = module.io;
      return this.ioFactory;
    } catch (error) {
      throw error instanceof Error ? error : new Error('Unable to load Socket.IO client library');
    }
  }
}

// --- services/connection-metrics.js ---
function evaluateConnectionQuality({ latencyMs, successRate }) {
  if (!Number.isFinite(latencyMs)) {
    return 'offline';
  }
  if (latencyMs < 80 && (successRate ?? 1) > 0.95) {
    return 'excellent';
  }
  if (latencyMs < 150 && (successRate ?? 1) > 0.85) {
    return 'good';
  }
  if (latencyMs < 300) {
    return 'fair';
  }
  return 'poor';
}

function getQualityLabel(quality) {
  switch (quality) {
    case 'excellent':
      return '● Excellent';
    case 'good':
      return '● Good';
    case 'fair':
      return '● Fair';
    case 'poor':
      return '● Poor';
    default:
      return '● Offline';
  }
}

// --- services/connection-monitor.js ---
const DEFAULT_INTERVAL = 15000;  // Reduced from 7000ms for performance

/**
 * Periodically monitors the connection health to the API/backup server.
 * Evaluates connection quality and provides metrics to subscribers.
 */
class ConnectionMonitor {
  /**
   * @param {Object} config - Monitor configuration
   * @param {ApiClient} config.api - API client instance for health checks
   * @param {number} [config.interval=15000] - Polling interval in milliseconds
   * @param {Function} [config.onResult] - Callback receiving health check results
   */
  constructor({ api, interval = DEFAULT_INTERVAL, onResult }) {
    this.api = api;
    this.interval = interval;
    this.onResult = typeof onResult === 'function' ? onResult : () => { };
    this.#timerManager = new TimerManager();
    this.inFlight = null;
  }

  #timerManager;

  /**
   * Starts periodic health checking.
   * Performs an immediate health check and sets up interval polling.
   */
  start() {
    this.#timerManager.start(() => this.#tick(), this.interval);
    this.#tick();
  }

  /**
   * Stops periodic health checking.
   * Clears any pending health check request.
   */
  stop() {
    this.#timerManager.stop();
    this.inFlight = null;
  }

  /**
   * Forces an immediate health check, bypassing any rate limiting.
   */
  forcePing() {
    this.#tick(true);
  }

  async #tick(force = false) {
    if (this.inFlight && !force) {
      return;
    }

    const started = performance.now();
    const request = this.api
      .health()
      .then((payload) => {
        const latency = performance.now() - started;
        console.log('[ConnectionMonitor] Health check response:', payload);


        const metrics = payload?.system_metrics || payload?.systemMetrics || null;

        // Check multiple possible response formats
        const backupServer = payload?.backup_server || payload?.backup_server_status || payload?.backup_server_state;
        const apiServer = payload?.api_server || payload?.api_server_status;
        const apiStatus = payload?.status;

        // Consider connected if:
        // 1. API server is running (means web API is responding)
        // 2. Backup server is running
        // 3. Overall status is healthy/ok
        const isApiServerRunning = apiServer === 'running' || apiServer === 'active' || apiServer === 'healthy';
        const isBackupRunning = backupServer === 'running' || backupServer === 'active' || backupServer === 'healthy';
        const isHealthy = apiStatus === 'healthy' || apiStatus === 'ok' || apiStatus === 'running';

        const connected = isApiServerRunning || isBackupRunning || isHealthy || Boolean(payload?.success);

        const quality = evaluateConnectionQuality({ latencyMs: latency, successRate: connected ? 1 : 0 });

        console.log('[ConnectionMonitor] Connection status:', {
          connected,
          isApiServerRunning,
          isBackupRunning,
          isHealthy,
          quality,
          latency,
          payload
        });

        // Update dual server status indicators in the UI
        updateDualServerStatus({
          apiOnline: true, // If we got here, API is responding
          backupOnline: isBackupRunning,
          latency
        });

        this.onResult({
          ok: true,
          latency,
          metrics,
          connected,
          quality,
          apiServerOnline: true,
          backupServerOnline: isBackupRunning,
          timestamp: Date.now(),
        });
      })
      .catch((error) => {
        console.error('[ConnectionMonitor] Health check failed:', error);
        // API server is offline if health check fails
        updateDualServerStatus({
          apiOnline: false,
          backupOnline: false
        });
        this.onResult({ ok: false, error, timestamp: Date.now() });
      })
      .finally(() => {
        if (this.inFlight === request) {
          this.inFlight = null;
        }
      });

    this.inFlight = request;
    return request;
  }
}

// --- services/file-manager.js ---
const RECENT_STORAGE_KEY = 'cyberbackup-recent-files';
const MAX_RECENT = 5;

/**
 * Manages file selection, drag-drop, recent files, and UI updates.
 * Handles file persistence to localStorage and announces selections for accessibility.
 */
class FileManager {
  /**
   * @param {Object} config - File manager configuration
   * @param {HTMLElement} [config.dropZone] - Drop zone element for drag-drop
   * @param {HTMLInputElement} [config.fileInput] - File input element
   * @param {HTMLElement} [config.selectButton] - Button to open file picker
   * @param {HTMLElement} [config.clearButton] - Button to clear selected file
   * @param {HTMLElement} [config.recentButton] - Button to show recent files
   * @param {HTMLElement} [config.nameLabel] - Display element for file name
   * @param {HTMLElement} [config.infoLabel] - Display element for file info (size, type)
   * @param {HTMLElement} [config.fileIcon] - Display element for file icon
   * @param {HTMLElement} [config.fileNameDisplay] - Display element for file name (new design)
   * @param {HTMLElement} [config.fileMetadata] - Display element for file metadata
   * @param {HTMLElement} [config.fileTypeBadge] - Display element for file type badge
   * @param {HTMLElement} [config.fileModified] - Display element for modification date
   * @param {ScreenReaderAnnouncer} [config.announcer] - Screen reader announcer instance
   * @param {Function} [config.onRecent] - Callback when recent file is selected
   */
  constructor({ dropZone, fileInput, selectButton, clearButton, recentButton, nameLabel, infoLabel, fileIcon, fileNameDisplay, fileMetadata, fileTypeBadge, fileModified, announcer, onRecent }) {
    this.dropZone = dropZone;
    this.fileInput = fileInput;
    this.selectButton = selectButton;
    this.clearButton = clearButton;
    this.recentButton = recentButton;
    this.nameLabel = nameLabel;
    this.infoLabel = infoLabel;

    // New File Card Elements
    this.fileIcon = fileIcon;
    this.fileNameDisplay = fileNameDisplay;
    this.fileMetadata = fileMetadata;
    this.fileTypeBadge = fileTypeBadge;
    this.fileModified = fileModified;

    this.announcer = announcer;
    this.onRecent = onRecent;

    this.currentFile = null;
    this.currentFileMeta = null;
    this.recent = this.#loadRecent();

    this.#attachEvents();
    this.#updateUI();
  }

  /**
   * Gets the currently selected file.
   * @type {File|null}
   */
  get file() {
    return this.currentFile;
  }

  /**
   * Clears the currently selected file and resets the UI.
   */
  clear() {
    this.currentFile = null;
    this.currentFileMeta = null;
    if (this.fileInput) {
      this.fileInput.value = '';
    }
    this.#updateUI();
  }

  // Handler references for cleanup
  #selectButtonHandler = null;
  #fileInputHandler = null;
  #clearButtonHandler = null;
  #recentButtonHandler = null;
  #dragOverHandler = null;
  #dragLeaveHandler = null;
  #dropHandler = null;
  #dropZoneClickHandler = null;

  #attachEvents() {
    // Select button click (optional - may not exist in new design)
    if (this.selectButton) {
      this.#selectButtonHandler = (e) => {
        e.stopPropagation(); // Prevent bubbling if inside drop zone
        this.fileInput?.click();
      };
      this.selectButton.addEventListener('click', this.#selectButtonHandler);
    }

    // File input change
    if (this.fileInput) {
      this.#fileInputHandler = (event) => {
        const input = event.target;
        const file = input.files?.[0];
        if (file) {
          this.#handleFile(file);
        }
      };
      this.fileInput.addEventListener('change', this.#fileInputHandler);
    }

    // Clear button (optional)
    if (this.clearButton) {
      this.#clearButtonHandler = (e) => {
        e.stopPropagation(); // Prevent bubbling
        this.clear();
        this.announcer?.announce('File cleared');
      };
      this.clearButton.addEventListener('click', this.#clearButtonHandler);
    }

    // Recent files button (optional)
    if (this.recentButton) {
      this.#recentButtonHandler = () => this.#showRecent();
      this.recentButton.addEventListener('click', this.#recentButtonHandler);
    }

    // Drop zone drag and drop + click to select
    if (this.dropZone) {
      this.#dragOverHandler = (event) => {
        event.preventDefault();
        this.dropZone?.classList.add('drag-over');
      };
      this.#dragLeaveHandler = () => this.dropZone?.classList.remove('drag-over');
      this.#dropHandler = (event) => {
        event.preventDefault();
        this.dropZone?.classList.remove('drag-over');
        if (event.dataTransfer?.files?.[0]) {
          this.#handleFile(event.dataTransfer.files[0]);
        }
      };
      this.#dropZoneClickHandler = (event) => {
        // Don't trigger if clicking on a button inside
        if (event.target.tagName === 'BUTTON' || event.target.closest('button')) return;
        this.fileInput?.click();
      };

      this.dropZone.addEventListener('dragover', this.#dragOverHandler);
      this.dropZone.addEventListener('dragleave', this.#dragLeaveHandler);
      this.dropZone.addEventListener('drop', this.#dropHandler);
      this.dropZone.addEventListener('click', this.#dropZoneClickHandler);
    }
  }

  #handleFile(file) {
    this.currentFile = file;
    this.currentFileMeta = {
      name: file.name,
      size: file.size,
      type: file.type || 'application/octet-stream',
      lastModified: file.lastModified,
    };
    this.#updateUI();
    this.#saveRecent(this.currentFileMeta);
    this.announcer?.announce(`Selected ${file.name}, size ${formatBytes(file.size)}`);
  }

  #updateUI() {
    // Update drop zone text if using new design
    const dropZoneText = this.dropZone?.querySelector('.drop-zone-text');

    if (!this.currentFileMeta) {
      // Reset to placeholder state
      if (dropZoneText) {
        dropZoneText.textContent = 'Drag & drop a file here';
        dropZoneText.classList.remove('file-selected');
      }
      if (this.nameLabel) {
        const namePlaceholder = this.nameLabel.dataset.placeholder || 'Drag & drop a file here';
        this.nameLabel.textContent = namePlaceholder;
        this.nameLabel.classList.add('placeholder');
      }
      if (this.infoLabel) {
        const infoPlaceholder = this.infoLabel.dataset.placeholder || 'Size — • Type —';
        this.infoLabel.textContent = infoPlaceholder;
        this.infoLabel.classList.add('placeholder');
      }
      if (this.clearButton) {
        this.clearButton.disabled = true;
      }
      this.dropZone?.classList.remove('file-selected', 'file-invalid');
      return;
    }

    const { name, size, type, lastModified } = this.currentFileMeta;

    // Add file-selected class with animation
    this.dropZone?.classList.add('file-selected');
    this.dropZone?.classList.remove('file-invalid');

    // Update drop zone text for new design (hidden but kept for fallback)
    if (dropZoneText) {
      dropZoneText.textContent = `${name} (${formatBytes(size)})`;
      dropZoneText.classList.add('file-selected');
    }

    // Update new file card elements
    if (this.fileNameDisplay) {
      this.fileNameDisplay.textContent = name;
      this.fileNameDisplay.title = name;
    }

    if (this.fileTypeBadge) {
      const ext = name.includes('.') ? name.split('.').pop().toUpperCase() : 'FILE';
      this.fileTypeBadge.textContent = ext.substring(0, 8); // Limit length
    }

    if (this.fileModified && lastModified) {
      const date = new Date(lastModified);
      this.fileModified.textContent = date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
    }

    if (this.fileIcon) {
      this.fileIcon.innerHTML = this.#getFileIcon(name);
    }

    // Update old-style labels if they exist
    if (this.nameLabel) {
      this.nameLabel.textContent = name;
      this.nameLabel.classList.remove('placeholder');
    }
    if (this.infoLabel) {
      this.infoLabel.textContent = `${formatBytes(size)} • ${type}`;
      this.infoLabel.classList.remove('placeholder');
    }

    if (this.clearButton) {
      this.clearButton.disabled = false;
    }
  }

  #getFileIcon(filename) {
    const ext = filename.split('.').pop().toLowerCase();

    // Default icon
    let iconPath = `<path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"></path><polyline points="13 2 13 9 20 9"></polyline>`;

    // Simple extension matching
    if (['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg'].includes(ext)) {
      // Image
      iconPath = `<rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><circle cx="8.5" cy="8.5" r="1.5"></circle><polyline points="21 15 16 10 5 21"></polyline>`;
    } else if (['mp4', 'mov', 'avi', 'mkv'].includes(ext)) {
      // Video
      iconPath = `<rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18"></rect><line x1="7" y1="2" x2="7" y2="22"></line><line x1="17" y1="2" x2="17" y2="22"></line><line x1="2" y1="12" x2="22" y2="12"></line><line x1="2" y1="7" x2="7" y2="7"></line><line x1="2" y1="17" x2="7" y2="17"></line><line x1="17" y1="17" x2="22" y2="17"></line><line x1="17" y1="7" x2="22" y2="7"></line>`;
    } else if (['mp3', 'wav', 'ogg'].includes(ext)) {
      // Audio
      iconPath = `<path d="M9 18V5l12-2v13"></path><circle cx="6" cy="18" r="3"></circle><circle cx="18" cy="16" r="3"></circle>`;
    } else if (['zip', 'rar', '7z', 'tar', 'gz'].includes(ext)) {
      // Archive
      iconPath = `<path d="M21 8v13H3V8"></path><path d="M1 3h22v5H1z"></path><path d="M10 12h4"></path>`;
    } else if (['pdf', 'doc', 'docx', 'txt'].includes(ext)) {
      // Document
      iconPath = `<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline>`;
    }

    return `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${iconPath}</svg>`;
  }

  #showRecent() {
    if (!this.recent.length) {
      this.announcer?.announce('No recent files yet');
      return;
    }
    const newest = this.recent[0];
    const formattedSize = formatBytes(newest.size);
    const message = `Recent: ${newest.name} (${formattedSize})`;
    this.announcer?.announce(message);
    if (typeof this.onRecent === 'function') {
      this.onRecent({ ...newest, formattedSize });
    }
  }

  #saveRecent(meta) {
    if (!meta?.name) return;
    this.recent = [meta, ...this.recent.filter((entry) => entry.name !== meta.name)].slice(0, MAX_RECENT);
    try {
      localStorage.setItem(RECENT_STORAGE_KEY, JSON.stringify(this.recent));
    } catch (error) {
      console.warn('Failed to persist recent files', error);
    }
  }

  #loadRecent() {
    try {
      const stored = localStorage.getItem(RECENT_STORAGE_KEY);
      if (!stored) return [];
      const parsed = JSON.parse(stored);
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  }

  /**
   * Cleans up all event listeners and references.
   * Must be called before destroying the manager instance to prevent memory leaks.
   */
  destroy() {
    // Remove select button listener
    if (this.selectButton && this.#selectButtonHandler) {
      this.selectButton.removeEventListener('click', this.#selectButtonHandler);
      this.#selectButtonHandler = null;
    }

    // Remove file input listener
    if (this.fileInput && this.#fileInputHandler) {
      this.fileInput.removeEventListener('change', this.#fileInputHandler);
      this.#fileInputHandler = null;
    }

    // Remove clear button listener
    if (this.clearButton && this.#clearButtonHandler) {
      this.clearButton.removeEventListener('click', this.#clearButtonHandler);
      this.#clearButtonHandler = null;
    }

    // Remove recent button listener
    if (this.recentButton && this.#recentButtonHandler) {
      this.recentButton.removeEventListener('click', this.#recentButtonHandler);
      this.#recentButtonHandler = null;
    }

    // Remove drop zone listeners
    if (this.dropZone) {
      if (this.#dragOverHandler) {
        this.dropZone.removeEventListener('dragover', this.#dragOverHandler);
        this.#dragOverHandler = null;
      }
      if (this.#dragLeaveHandler) {
        this.dropZone.removeEventListener('dragleave', this.#dragLeaveHandler);
        this.#dragLeaveHandler = null;
      }
      if (this.#dropHandler) {
        this.dropZone.removeEventListener('drop', this.#dropHandler);
        this.#dropHandler = null;
      }
      if (this.#dropZoneClickHandler) {
        this.dropZone.removeEventListener('click', this.#dropZoneClickHandler);
        this.#dropZoneClickHandler = null;
      }
    }

    // Clear references
    this.dropZone = null;
    this.fileInput = null;
    this.selectButton = null;
    this.clearButton = null;
    this.recentButton = null;
  }
}

// --- services/theme-manager.js ---
const THEME_STORAGE_KEY = 'cyberbackup-theme';

/**
 * Manages application theme switching between dark and light modes.
 * Persists theme preference to localStorage and updates DOM accordingly.
 */
class ThemeManager {
  /**
   * @param {HTMLElement} [toggleElement] - Button or checkbox element to toggle theme
   */
  constructor(toggleElement) {
    this.toggleElement = toggleElement;
    this.root = document.documentElement;
    this.current = this.#load() || 'theme-dark';
    this.apply(this.current);

    if (this.toggleElement) {
      // Check if it's a checkbox (new design) or button (old design)
      if (this.toggleElement.type === 'checkbox') {
        this.toggleElement.checked = this.current === 'theme-light';
        this.toggleElement.addEventListener('change', () => this.toggle());
      } else {
        this.toggleElement.addEventListener('click', () => this.toggle());
      }
      this.#updateLabel();
    }
  }

  /**
   * Toggles between dark and light theme.
   * Updates DOM, localStorage, and toggle element state.
   */
  toggle() {
    this.current = this.current === 'theme-dark' ? 'theme-light' : 'theme-dark';
    this.apply(this.current);
    this.#save(this.current);
    this.#updateLabel();
  }

  /**
   * Applies a theme class to the document root.
   * @param {string} themeClass - Theme class name ('theme-dark' or 'theme-light')
   */
  apply(themeClass) {
    this.root.classList.remove('theme-dark', 'theme-light');
    this.root.classList.add(themeClass);
  }

  #updateLabel() {
    if (!this.toggleElement) return;
    const isLight = this.current === 'theme-light';

    // Handle checkbox (new design)
    if (this.toggleElement.type === 'checkbox') {
      this.toggleElement.checked = isLight;
      this.toggleElement.setAttribute('aria-label', `Switch to ${isLight ? 'dark' : 'light'} mode`);
    } else {
      // Handle button (old design)
      const iconSpan = this.toggleElement.querySelector('.theme-icon');
      if (iconSpan) {
        iconSpan.textContent = isLight ? '🌙' : '☀️';
      } else {
        this.toggleElement.textContent = isLight ? '🌙 Dark mode' : '☀️ Light mode';
      }
      this.toggleElement.setAttribute('aria-label', `Switch to ${isLight ? 'dark' : 'light'} mode`);
    }
  }

  #save(theme) {
    try {
      localStorage.setItem(THEME_STORAGE_KEY, theme);
    } catch (error) {
      console.warn('Failed to persist theme preference', error);
    }
  }

  #load() {
    try {
      return localStorage.getItem(THEME_STORAGE_KEY);
    } catch {
      return null;
    }
  }
}

// --- services/log-store.js ---
const LEVEL_PRIORITY = new Set(['info', 'warn', 'error']);
const MAX_LOG_ENTRIES = 500; // Synchronize with DOM limit below

function normalizeLevel(level) {
  if (!level) return 'info';
  const normalized = level.toString().toLowerCase();
  if (LEVEL_PRIORITY.has(normalized)) {
    return normalized;
  }
  return 'info';
}

// Level icons for visual indicators
const LEVEL_ICONS = {
  info: `<svg class="log-level-icon" width="14" height="14" viewBox="0 0 14 14" fill="none">
    <circle cx="7" cy="7" r="6" stroke="currentColor" stroke-width="1.5"/>
    <path d="M7 6v4M7 4.5v.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
  </svg>`,
  warn: `<svg class="log-level-icon" width="14" height="14" viewBox="0 0 14 14" fill="none">
    <path d="M7 1L13 12H1L7 1z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>
    <path d="M7 5v3M7 9.5v.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
  </svg>`,
  error: `<svg class="log-level-icon" width="14" height="14" viewBox="0 0 14 14" fill="none">
    <circle cx="7" cy="7" r="6" stroke="currentColor" stroke-width="1.5"/>
    <path d="M5 5l4 4M9 5l-4 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
  </svg>`,
};

/**
 * Stores and renders activity logs with filtering, search, and export capabilities.
 * Manages in-memory log entries and renders them incrementally for performance.
 */
class LogStore {
  #entries;
  #filter;
  #autoScroll;
  #container;
  #emptyState;
  #countElement;
  #lastRenderedId;
  #nextId;
  #renderPending;
  #rowTemplate;

  /**
   * @param {HTMLElement} container - Container element for log entries
   */
  constructor(container) {
    this.#entries = [];
    this.#filter = 'all';
    this.#autoScroll = true;
    this.#container = container;
    this.#emptyState = document.getElementById('logsEmptyState');
    this.#countElement = document.getElementById('logEntryCount');
    this.#lastRenderedId = 0;
    this.#nextId = 1;
    this.#renderPending = false;
    this.#rowTemplate = this.#buildRowTemplate();
    // Set up event delegation for log action buttons
    this.#setupEventDelegation();
  }

  #buildRowTemplate() {
    const row = document.createElement('div');
    row.className = 'log-entry';
    row.innerHTML = `
      <div class="log-indicator"></div>
      <div class="log-icon-wrapper"></div>
      <span class="log-timestamp"></span>
      <span class="log-level-badge"></span>
      <span class="log-message"></span>
      <div class="log-actions">
        <button class="log-action-mini" data-action="copy" title="Copy to clipboard">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
        </button>
        <button class="log-action-mini" data-action="pin" title="Pin this log">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="17" x2="12" y2="22"></line><path d="M5 17h14v-1.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V6h1a2 2 0 0 0 0-4H8a2 2 0 0 0 0 4h1v4.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24Z"></path></svg>
        </button>
      </div>
    `;
    return row;
  }

  #setupEventDelegation() {
    if (!this.#container) return;
    this.#container.addEventListener('click', (e) => {
      const btn = e.target.closest('.log-action-mini');
      if (!btn) return;
      const entry = btn.closest('.log-entry');
      if (!entry) return;
      const { action } = btn.dataset;
      if (action === 'copy') {
        const msg = entry.querySelector('.log-message');
        if (msg) navigator.clipboard.writeText(msg.textContent);
      } else if (action === 'pin') {
        entry.classList.toggle('pinned');
      }
    });
  }

  /**
   * Sets the log filter to show only entries of a specific level.
   * @param {string} filter - Filter value: 'all', 'info', 'warn', or 'error'
   */
  setFilter(filter) {
    if (this.#filter === filter) return;
    this.#filter = filter;
    // Filter changed - need full rebuild
    this.#lastRenderedId = 0;
    this.render(true);
  }

  /**
   * Enables or disables automatic scrolling to new log entries.
   * @param {boolean} enabled - True to auto-scroll, false to disable
   */
  setAutoScroll(enabled) {
    this.#autoScroll = Boolean(enabled);
  }

  /**
   * Adds a new log entry to the store.
   * @param {string} message - Log message
   * @param {Object} [options] - Log options
   * @param {string} [options.level='info'] - Log level: 'info', 'warn', or 'error'
   * @param {string} [options.phase] - Optional phase/stage identifier
   * @param {Date} [options.timestamp=now] - Timestamp for the log entry
   */
  add(message, { level = 'info', phase, timestamp = new Date() } = {}) {
    const entry = {
      id: this.#nextId++,
      timestamp: timestamp instanceof Date ? timestamp : new Date(timestamp),
      message,
      phase: phase || null,
      level: normalizeLevel(level),
    };
    this.#entries.push(entry);

    // Keep only last MAX_LOG_ENTRIES entries in memory
    if (this.#entries.length > MAX_LOG_ENTRIES) {
      this.#entries.shift(); // Remove oldest
    }

    this.#requestRender();
  }

  /**
   * Clears all log entries.
   */
  clear() {
    this.#entries = [];
    this.#lastRenderedId = 0;
    this.render(true);
  }

  /**
   * Exports all log entries as a formatted string.
   * @returns {string} Log entries formatted as ISO timestamp with level and message
   */
  export() {
    const lines = [];
    for (const entry of this.#entries) {
      const iso = entry.timestamp.toISOString();
      const phase = entry.phase ? `[${entry.phase}] ` : '';
      lines.push(`${iso} [${entry.level.toUpperCase()}] ${phase}${entry.message}`);
    }
    return lines.join('\n');
  }

  #formatTime(date) {
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    });
  }

  #requestRender() {
    if (this.#renderPending) return;
    this.#renderPending = true;
    requestAnimationFrame(() => this.render());
  }

  /**
   * Renders new log entries to the DOM.
   * Uses incremental rendering for performance - only renders new entries since last render.
   * @param {boolean} [forceRebuild=false] - If true, clears and rebuilds entire log view
   */
  render(forceRebuild = false) {
    this.#renderPending = false;
    if (!this.#container) return;

    const filter = this.#filter;
    const filteredEntries = this.#entries.filter(
      (entry) => filter === 'all' || entry.level === filter
    );

    // Update entry count
    if (this.#countElement) {
      this.#countElement.textContent = filteredEntries.length.toString();
    }

    // Handle empty state
    if (this.#emptyState) {
      this.#emptyState.style.display = filteredEntries.length === 0 ? 'flex' : 'none';
    }

    // If force rebuild or container is empty (but we have entries), clear and rebuild
    // We check if container has children other than emptyState
    const hasLogEntries = this.#container.querySelector('.log-entry');

    if (forceRebuild || (!hasLogEntries && filteredEntries.length > 0)) {
      // Clear container (preserve empty state element)
      const children = Array.from(this.#container.children);
      for (const child of children) {
        if (child.id !== 'logsEmptyState') {
          child.remove();
        }
      }
      this.#lastRenderedId = 0;
    }

    // Find entries that haven't been rendered yet
    const newEntries = filteredEntries.filter(e => e.id > this.#lastRenderedId);

    if (newEntries.length > 0) {
      const fragment = document.createDocumentFragment();
      for (let i = 0; i < newEntries.length; i++) {
        const entry = newEntries[i];
        fragment.append(this.#createLogEntry(entry, true));
        this.#lastRenderedId = Math.max(this.#lastRenderedId, entry.id);
      }
      this.#container.append(fragment);
    }

    // Trim DOM if too many entries (keep last MAX_LOG_ENTRIES visible)
    const logEntries = this.#container.querySelectorAll('.log-entry');
    if (logEntries.length > MAX_LOG_ENTRIES) {
      const excess = logEntries.length - MAX_LOG_ENTRIES;
      for (let i = 0; i < excess; i++) {
        logEntries[i].remove();
      }
    }

    if (this.#autoScroll && newEntries.length > 0) {
      this.#container.scrollTop = this.#container.scrollHeight;
    }
  }

  #createLogEntry(entry, isNew) {
    const row = this.#rowTemplate.cloneNode(true);
    row.className = `log-entry log-${entry.level}${isNew ? ' log-entry-new' : ''}`;
    row.dataset.level = entry.level;
    row.dataset.id = entry.id;

    // Fast access to children (order is known from #buildRowTemplate)
    // 0: indicator, 1: icon-wrapper, 2: timestamp, 3: badge, 4: message, 5: actions
    const iconWrapper = row.children[1];
    const time = row.children[2];
    const badge = row.children[3];
    const msg = row.children[4];

    iconWrapper.innerHTML = LEVEL_ICONS[entry.level] || LEVEL_ICONS.info;
    time.textContent = this.#formatTime(entry.timestamp);
    badge.className = `log-level-badge log-level-${entry.level}`;
    badge.textContent = entry.level.toUpperCase();
    msg.textContent = entry.message;

    return row;
  }
}

// --- services/advanced-settings.js ---
const SETTINGS_STORAGE_KEYS = {
  chunk: 'cyberbackup-chunk-size',
  retry: 'cyberbackup-retry-limit',
};

const SETTINGS_DEFAULTS = {
  chunkSize: 8,
  retryLimit: 3,
};

const SETTINGS_LIMITS = {
  chunkSize: { min: 1, max: 256 },
  retryLimit: { min: 0, max: 20 },
};

/**
 * Manages advanced backup settings like chunk size and retry limit.
 * Persists settings to localStorage and validates input ranges.
 */
class AdvancedSettings {
  /**
   * @param {Object} config - Settings configuration
   * @param {HTMLInputElement} [config.chunkInput] - Input field for chunk size (MB)
   * @param {HTMLInputElement} [config.retryInput] - Input field for retry limit
   * @param {HTMLElement} [config.resetButton] - Button to reset settings to defaults
   * @param {ToastManager} [config.toast] - Toast notification manager
   * @param {ScreenReaderAnnouncer} [config.announcer] - Screen reader announcer instance
   */
  constructor({ chunkInput, retryInput, resetButton, toast, announcer }) {
    this.chunkInput = chunkInput;
    this.retryInput = retryInput;
    this.resetButton = resetButton;
    this.toast = toast;
    this.announcer = announcer;

    this.#hydrate();
    this.#bindEvents();
  }

  /**
   * Gets the current settings as an options object for backup operations.
   * Returns an object with chunk_size_mb and/or retry_limit keys if valid.
   * @returns {Object} Options object with validated settings
   */
  getOptions() {
    const chunk = validateNumericInput(this.chunkInput, SETTINGS_LIMITS.chunkSize);
    const retry = validateNumericInput(this.retryInput, SETTINGS_LIMITS.retryLimit);
    const options = {};

    if (chunk !== null) {
      options.chunk_size_mb = chunk;
    }

    if (retry !== null) {
      options.retry_limit = retry;
    }

    return options;
  }

  /**
   * Resets all settings to their default values.
   * Updates localStorage and shows a toast notification.
   */
  reset() {
    this.#applyValue(this.chunkInput, SETTINGS_DEFAULTS.chunkSize, SETTINGS_STORAGE_KEYS.chunk);
    this.#applyValue(this.retryInput, SETTINGS_DEFAULTS.retryLimit, SETTINGS_STORAGE_KEYS.retry);
    this.toast?.show('Advanced settings restored to defaults', 'info', 2200);
    this.announcer?.announce('Advanced settings reset to defaults');
  }

  #hydrate() {
    this.#applyValue(this.chunkInput, this.#loadFromStorage(SETTINGS_STORAGE_KEYS.chunk, SETTINGS_DEFAULTS.chunkSize));
    this.#applyValue(this.retryInput, this.#loadFromStorage(SETTINGS_STORAGE_KEYS.retry, SETTINGS_DEFAULTS.retryLimit));
  }

  #applyValue(input, value, storageKey) {
    if (!input) {
      return;
    }
    input.value = value.toString();
    input.setAttribute('aria-invalid', 'false');
    if (storageKey) {
      this.#persist(storageKey, value);
    }
  }

  #bindEvents() {
    if (this.resetButton) {
      this.resetButton.addEventListener('click', () => this.reset());
    }

    if (this.chunkInput) {
      this.chunkInput.addEventListener('blur', () => this.#validateAndPersist(this.chunkInput, SETTINGS_STORAGE_KEYS.chunk, SETTINGS_LIMITS.chunkSize));
    }

    if (this.retryInput) {
      this.retryInput.addEventListener('blur', () => this.#validateAndPersist(this.retryInput, SETTINGS_STORAGE_KEYS.retry, SETTINGS_LIMITS.retryLimit));
    }
  }

  #validateAndPersist(input, storageKey, limits) {
    if (!input) {
      return;
    }

    const parsed = validateNumericInput(input, limits);
    if (parsed === null) {
      input.setAttribute('aria-invalid', 'true');
      this.toast?.show(`Enter a value between ${limits.min} and ${limits.max}`, 'warn', 3200);
      this.announcer?.announce(`Invalid value. Enter a number between ${limits.min} and ${limits.max}`);
      return;
    }

    input.value = parsed.toString();
    input.setAttribute('aria-invalid', 'false');
    this.#persist(storageKey, parsed);
  }

  #persist(key, value) {
    try {
      localStorage.setItem(key, value.toString());
    } catch (error) {
      console.warn('Failed to persist advanced setting', { key, error });
    }
  }

  #loadFromStorage(key, fallback) {
    try {
      const value = localStorage.getItem(key);
      if (value === null) {
        return fallback;
      }
      const numeric = Number.parseInt(value, 10);
      return Number.isFinite(numeric) ? clamp(numeric, SETTINGS_LIMITS[key === SETTINGS_STORAGE_KEYS.chunk ? 'chunkSize' : 'retryLimit']) : fallback;
    } catch {
      return fallback;
    }
  }
}
