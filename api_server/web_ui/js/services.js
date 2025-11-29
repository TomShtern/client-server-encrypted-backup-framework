/**
 * CyberBackup Client - Services
 * Bundled: api-client, socket-client, connection-metrics, connection-monitor, file-manager, theme-manager, log-store, advanced-settings
 */

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

class ApiClient {
  constructor(baseUrl = '') {
    this.baseUrl = baseUrl;
  }

  #buildUrl(path) {
    if (!path.startsWith('/')) {
      return `${this.baseUrl}/${path}`;
    }
    return `${this.baseUrl}${path}`;
  }

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

  async disconnect() {
    const { response, payload } = await withTimeout(
      fetch(this.#buildUrl('/api/disconnect'), { method: 'POST' }),
    ).then(normalizeResponse);
    if (!response.ok || !payload?.success) {
      throw new Error(payload?.error || 'Failed to disconnect');
    }
    return payload;
  }

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

  async pause() {
    return this.#command('/api/pause');
  }

  async resume() {
    return this.#command('/api/resume');
  }

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

class SocketClient {
  constructor({ url = DEFAULT_SOCKET_URL, options = {}, onConnect, onDisconnect, onError, onStatus, onProgress, onFileReceipt }) {
    this.url = url ?? DEFAULT_SOCKET_URL;
    this.options = { ...DEFAULT_OPTIONS, ...options };
    this.onConnect = typeof onConnect === 'function' ? onConnect : () => {};
    this.onDisconnect = typeof onDisconnect === 'function' ? onDisconnect : () => {};
    this.onError = typeof onError === 'function' ? onError : () => {};
    this.onStatus = typeof onStatus === 'function' ? onStatus : () => {};
    this.onProgress = typeof onProgress === 'function' ? onProgress : () => {};
    this.onFileReceipt = typeof onFileReceipt === 'function' ? onFileReceipt : () => {};

    this.socket = null;
    this.currentJobId = null;
    this.ioFactory = null;
  }

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

  stop() {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
  }

  watchJob(jobId) {
    this.currentJobId = jobId;
    this.requestStatus(jobId);
  }

  clearJob() {
    this.currentJobId = null;
  }

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
      const module = await import('https://cdn.jsdelivr.net/npm/socket.io-client@4.7.5/dist/socket.io.esm.min.js');
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

class ConnectionMonitor {
  constructor({ api, interval = DEFAULT_INTERVAL, onResult }) {
    this.api = api;
    this.interval = interval;
    this.onResult = typeof onResult === 'function' ? onResult : () => {};
    this.timer = null;
    this.inFlight = null;
  }

  start() {
    this.stop();
    this.#tick();
    this.timer = globalThis.setInterval(() => this.#tick(), this.interval);
  }

  stop() {
    if (this.timer) {
      globalThis.clearInterval(this.timer);
      this.timer = null;
    }
    this.inFlight = null;
  }

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

        this.onResult({
          ok: true,
          latency,
          metrics,
          connected,
          quality,
          timestamp: Date.now(),
        });
      })
      .catch((error) => {
        console.error('[ConnectionMonitor] Health check failed:', error);
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

class FileManager {
  constructor({ dropZone, fileInput, selectButton, clearButton, recentButton, nameLabel, infoLabel, announcer, onRecent }) {
    this.dropZone = dropZone;
    this.fileInput = fileInput;
    this.selectButton = selectButton;
    this.clearButton = clearButton;
    this.recentButton = recentButton;
    this.nameLabel = nameLabel;
    this.infoLabel = infoLabel;
    this.announcer = announcer;
    this.onRecent = onRecent;

    this.currentFile = null;
    this.currentFileMeta = null;
    this.recent = this.#loadRecent();

    this.#attachEvents();
    this.#updateUI();
  }

  get file() {
    return this.currentFile;
  }

  clear() {
    this.currentFile = null;
    this.currentFileMeta = null;
    if (this.fileInput) {
      this.fileInput.value = '';
    }
    this.#updateUI();
  }

  #attachEvents() {
    // Select button click (optional - may not exist in new design)
    if (this.selectButton) {
      this.selectButton.addEventListener('click', () => this.fileInput?.click());
    }

    // File input change
    if (this.fileInput) {
      this.fileInput.addEventListener('change', (event) => {
        const input = event.target;
        const file = input.files?.[0];
        if (file) {
          this.#handleFile(file);
        }
      });
    }

    // Clear button (optional)
    if (this.clearButton) {
      this.clearButton.addEventListener('click', () => {
        this.clear();
        this.announcer?.announce('File cleared');
      });
    }

    // Recent files button (optional)
    if (this.recentButton) {
      this.recentButton.addEventListener('click', () => this.#showRecent());
    }

    // Drop zone drag and drop + click to select
    if (this.dropZone) {
      const onDragOver = (event) => {
        event.preventDefault();
        this.dropZone?.classList.add('drag-over');
      };
      const onDragLeave = () => this.dropZone?.classList.remove('drag-over');
      const onDrop = (event) => {
        event.preventDefault();
        this.dropZone?.classList.remove('drag-over');
        if (event.dataTransfer?.files?.[0]) {
          this.#handleFile(event.dataTransfer.files[0]);
        }
      };

      // Click on drop zone to open file picker
      const onClick = (event) => {
        // Don't trigger if clicking on a button inside
        if (event.target.tagName === 'BUTTON') return;
        this.fileInput?.click();
      };

      this.dropZone.addEventListener('dragover', onDragOver);
      this.dropZone.addEventListener('dragleave', onDragLeave);
      this.dropZone.addEventListener('drop', onDrop);
      this.dropZone.addEventListener('click', onClick);
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

    const { name, size, type } = this.currentFileMeta;

    // Add file-selected class with animation
    this.dropZone?.classList.add('file-selected');
    this.dropZone?.classList.remove('file-invalid');

    // Update drop zone text for new design
    if (dropZoneText) {
      dropZoneText.textContent = `${name} (${formatBytes(size)})`;
      dropZoneText.classList.add('file-selected');
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

    // Add animation to file icon
    const fileIcon = this.dropZone?.querySelector('.file-icon');
    if (fileIcon) {
      fileIcon.classList.add('file-selected');
    }

    if (this.clearButton) {
      this.clearButton.disabled = false;
    }
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
}

// --- services/theme-manager.js ---
const THEME_STORAGE_KEY = 'cyberbackup-theme';

class ThemeManager {
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

  toggle() {
    this.current = this.current === 'theme-dark' ? 'theme-light' : 'theme-dark';
    this.apply(this.current);
    this.#save(this.current);
    this.#updateLabel();
  }

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

  setFilter(filter) {
    if (this.#filter === filter) return;
    this.#filter = filter;
    // Filter changed - need full rebuild
    this.#lastRenderedId = 0;
    this.render(true);
  }

  setAutoScroll(enabled) {
    this.#autoScroll = Boolean(enabled);
  }

  add(message, { level = 'info', phase, timestamp = new Date() } = {}) {
    const entry = {
      id: this.#nextId++,
      timestamp: timestamp instanceof Date ? timestamp : new Date(timestamp),
      message,
      phase: phase || null,
      level: normalizeLevel(level),
    };
    this.#entries.push(entry);

    // Keep only last 500 entries in memory
    if (this.#entries.length > 500) {
      this.#entries.shift(); // Remove oldest
    }

    this.#requestRender();
  }

  clear() {
    this.#entries = [];
    this.#lastRenderedId = 0;
    this.render(true);
  }

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

    // Trim DOM if too many entries (keep last 400 visible)
    const logEntries = this.#container.querySelectorAll('.log-entry');
    const maxVisible = 400;
    if (logEntries.length > maxVisible) {
      const excess = logEntries.length - maxVisible;
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

function clamp(value, { min, max }) {
  return Math.min(Math.max(value, min), max);
}

function parseNumericInput(input, { min, max }) {
  const raw = input.value.trim();
  if (raw.length === 0) {
    return null;
  }
  const numeric = Number.parseInt(raw, 10);
  if (!Number.isFinite(numeric)) {
    return null;
  }
  return clamp(numeric, { min, max });
}

class AdvancedSettings {
  constructor({ chunkInput, retryInput, resetButton, toast, announcer }) {
    this.chunkInput = chunkInput;
    this.retryInput = retryInput;
    this.resetButton = resetButton;
    this.toast = toast;
    this.announcer = announcer;

    this.#hydrate();
    this.#bindEvents();
  }

  getOptions() {
    const chunk = parseNumericInput(this.chunkInput, SETTINGS_LIMITS.chunkSize);
    const retry = parseNumericInput(this.retryInput, SETTINGS_LIMITS.retryLimit);
    const options = {};

    if (chunk !== null) {
      options.chunk_size_mb = chunk;
    }

    if (retry !== null) {
      options.retry_limit = retry;
    }

    return options;
  }

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

    const parsed = parseNumericInput(input, limits);
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
