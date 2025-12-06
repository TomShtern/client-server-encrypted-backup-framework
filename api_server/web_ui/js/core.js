/**
 * CyberBackup Client - Core Engine
 * Pure logic, networking, configuration, and utilities.
 * Depends on: core-utils.js
 */

// --- Error Handling ---

class ErrorBoundary {
  static handle(error, context, recovery = null) {
    console.error(`[${context}] Error:`, error);
    const userMessage = this.formatUserMessage(error, context);

    try {
      if (globalThis.app?.logs) {
        globalThis.app.logs.add(userMessage, { level: 'error', phase: 'ERROR' });
      }
    } catch (logError) {
      console.warn('Failed to log error:', logError);
    }

    try {
      if (globalThis.app?.toast) {
        globalThis.app.toast.show(userMessage, 'error', 5000);
      }
    } catch (toastError) {
      console.warn('Failed to show toast:', toastError);
    }

    if (recovery) {
      try {
        recovery();
      } catch (recoveryError) {
        console.error('Recovery failed:', recoveryError);
      }
    }
  }

  static formatUserMessage(error, context) {
    if (error.name === 'NetworkError' || error.message.includes('fetch')) {
      return `Network error: Unable to connect to server.`;
    }
    if (error.name === 'TypeError' && error.message.includes('fetch')) {
      return `Connection error: Server is not responding.`;
    }
    if (error.name === 'AbortError') {
      return `Operation cancelled.`;
    }
    return error.message || `An unexpected error occurred in ${context}.`;
  }
}

// --- Networking ---

const DEFAULT_TIMEOUT = 20000;

function withTimeout(promise, timeoutMs = DEFAULT_TIMEOUT) {
  return Promise.race([
    promise,
    new Promise((_, reject) => setTimeout(() => reject(new Error('Request timed out')), timeoutMs))
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
    return path.startsWith('/') ? `${this.baseUrl}${path}` : `${this.baseUrl}/${path}`;
  }

  async health() {
    const { response, payload } = await withTimeout(
      fetch(this.#buildUrl('/api/health'), { headers: { 'Cache-Control': 'no-cache' } }),
      8000
    ).then(normalizeResponse);
    if (!response.ok) throw new Error(payload?.error || 'Health check failed');
    return payload;
  }

  async connect(config) {
    const { response, payload } = await withTimeout(
      fetch(this.#buildUrl('/api/connect'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      })
    ).then(normalizeResponse);
    if (!response.ok || !payload?.success) throw new Error(payload?.error || payload?.message || 'Failed to connect');
    return payload;
  }

  async disconnect() {
    const { response, payload } = await withTimeout(
      fetch(this.#buildUrl('/api/disconnect'), { method: 'POST' })
    ).then(normalizeResponse);
    if (!response.ok || !payload?.success) throw new Error(payload?.error || 'Failed to disconnect');
    return payload;
  }

  async startBackup({ file, username, host, port, options = {} }) {
    if (!(file instanceof File)) throw new TypeError('A valid file must be provided');
    const form = new FormData();
    form.append('file', file, file.name);
    if (username) form.append('username', username);
    if (host) form.append('host', host);
    if (port) form.append('port', String(port));
    for (const [key, value] of Object.entries(options)) {
      if (value !== undefined && value !== null && value !== '') form.append(key, String(value));
    }

    const { response, payload } = await withTimeout(
      fetch(this.#buildUrl('/api/start_backup'), { method: 'POST', body: form }),
      60000
    ).then(normalizeResponse);
    if (!response.ok || !payload?.success) throw new Error(payload?.error || payload?.message || 'Backup start failed');
    return payload;
  }

  async status(jobId) {
    const url = new URL(this.#buildUrl('/api/status'), globalThis.location?.origin || 'http://localhost');
    if (jobId) url.searchParams.set('job_id', jobId);
    const { response, payload } = await withTimeout(
      fetch(url.toString(), { headers: { 'Cache-Control': 'no-cache' } }),
      10000
    ).then(normalizeResponse);
    if (!response.ok) throw new Error(payload?.error || 'Status request failed');
    return payload;
  }

  async pause() { return this.#command('/api/pause'); }
  async resume() { return this.#command('/api/resume'); }
  async stop() { return this.#command('/api/stop'); }

  #command(path) {
    return withTimeout(fetch(this.#buildUrl(path), { method: 'POST' })).then(async (response) => {
      const { payload } = await normalizeResponse(response);
      if (!response.ok || !payload?.success) throw new Error(payload?.error || `Command failed: ${path}`);
      return payload;
    });
  }
}

class SocketClient {
  constructor({ url, options = {}, onConnect, onDisconnect, onError, onStatus, onProgress, onFileReceipt }) {
    this.url = url || (globalThis.location ? globalThis.location.origin : '');
    this.options = {
      transports: ['websocket'],
      reconnection: true,
      reconnectionDelay: 1500,
      timeout: 8000,
      ...options
    };
    this.callbacks = { onConnect, onDisconnect, onError, onStatus, onProgress, onFileReceipt };
    this.socket = null;
    this.currentJobId = null;
  }

  async start() {
    try {
      const io = await this.#ensureIo();
      this.socket = io(this.url, this.options);
      this.#bindEvents();
    } catch (error) {
      this.callbacks.onError?.(error);
    }
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
    if (this.socket && jobId) {
      this.socket.emit('request_status', { job_id: jobId });
    }
  }

  #bindEvents() {
    if (!this.socket) return;
    this.socket.on('connect', () => {
      this.callbacks.onConnect?.();
      if (this.currentJobId) this.requestStatus(this.currentJobId);
    });
    this.socket.on('disconnect', (reason) => this.callbacks.onDisconnect?.(reason));
    this.socket.on('connect_error', (err) => this.callbacks.onError?.(err));
    this.socket.on('status', (p) => this.callbacks.onStatus?.(p));
    this.socket.on('status_response', (p) => this.callbacks.onStatus?.(p));
    this.socket.on('progress_update', (p) => {
      if (!this.currentJobId || !p?.job_id || p.job_id === this.currentJobId) {
        this.callbacks.onProgress?.(p);
      }
    });
    this.socket.on('file_receipt', (p) => this.callbacks.onFileReceipt?.(p));
    this.socket.connect();
  }

  async #ensureIo() {
    if (globalThis.io) return globalThis.io;
    try {
      const module = await import('https://cdn.jsdelivr.net/npm/socket.io-client@4.7.5/dist/socket.io.esm.min.js');
      return module.io;
    } catch (e) {
      throw new Error('Unable to load Socket.IO client');
    }
  }
}

function evaluateConnectionQuality({ latencyMs, successRate }) {
  if (successRate < 0.8) return 'poor';
  if (latencyMs > 500) return 'poor';
  if (latencyMs > 150) return 'fair';
  return 'good';
}

class ConnectionMonitor {
  constructor({ api, interval = 15000, onResult }) {
    this.api = api;
    this.interval = interval;
    this.onResult = onResult || (() => {});
    this.timerId = null;
    this.inFlight = null;
  }

  start() {
    this.stop();
    this.timerId = setInterval(() => this.#tick(), this.interval);
    this.#tick();
  }

  stop() {
    if (this.timerId) {
      clearInterval(this.timerId);
      this.timerId = null;
    }
    this.inFlight = null;
  }

  forcePing() {
    this.#tick(true);
  }

  async #tick(force = false) {
    if (this.inFlight && !force) return;

    const started = performance.now();
    const request = this.api.health()
      .then((payload) => {
        const latency = performance.now() - started;
        const backupServer = payload?.backup_server || payload?.backup_server_status;
        const apiServer = payload?.api_server || payload?.api_server_status;
        const apiStatus = payload?.status;

        const isBackupRunning = backupServer === 'running' || backupServer === 'active' || backupServer === 'healthy';
        const isApiRunning = apiServer === 'running' || apiServer === 'active' || apiServer === 'healthy';
        const isHealthy = apiStatus === 'healthy' || apiStatus === 'ok' || apiStatus === 'running';
        const connected = isApiRunning || isBackupRunning || isHealthy || Boolean(payload?.success);

        let quality = 'offline';
        if (connected) {
          quality = evaluateConnectionQuality({ latencyMs: latency, successRate: 1 });
        }

        // Update UI helper if available
        if (globalThis.updateDualServerStatus) {
          globalThis.updateDualServerStatus({
            apiOnline: true,
            backupOnline: isBackupRunning,
            latency
          });
        }

        this.onResult({
          ok: true,
          latency,
          metrics: payload?.system_metrics || payload?.systemMetrics,
          connected,
          quality,
          apiServerOnline: true,
          backupServerOnline: isBackupRunning,
          timestamp: Date.now()
        });
      })
      .catch((error) => {
        if (globalThis.updateDualServerStatus) {
          globalThis.updateDualServerStatus({ apiOnline: false, backupOnline: false });
        }
        this.onResult({ ok: false, error, timestamp: Date.now() });
      })
      .finally(() => {
        if (this.inFlight === request) this.inFlight = null;
      });

    this.inFlight = request;
  }
}

class AdvancedSettings {
  constructor({ chunkInput, retryInput, resetButton, toast, announcer }) {
    this.chunkInput = chunkInput;
    this.retryInput = retryInput;
    this.resetButton = resetButton;
    this.toast = toast;
    this.announcer = announcer;
    this.limits = { chunkSize: { min: 1, max: 256 }, retryLimit: { min: 0, max: 20 } };
    this.defaults = { chunkSize: 8, retryLimit: 3 };
    this.keys = { chunk: 'cyberbackup-chunk-size', retry: 'cyberbackup-retry-limit' };

    this.#hydrate();
    this.#bindEvents();
  }

  getOptions() {
    const chunk = validateNumericInput(this.chunkInput, this.limits.chunkSize);
    const retry = validateNumericInput(this.retryInput, this.limits.retryLimit);
    const options = {};
    if (chunk !== null) options.chunk_size_mb = chunk;
    if (retry !== null) options.retry_limit = retry;
    return options;
  }

  reset() {
    this.#apply(this.chunkInput, this.defaults.chunkSize, this.keys.chunk);
    this.#apply(this.retryInput, this.defaults.retryLimit, this.keys.retry);
    this.toast?.show('Advanced settings restored to defaults', 'info');
    this.announcer?.announce('Advanced settings reset to defaults');
  }

  #hydrate() {
    this.#apply(this.chunkInput, this.#load(this.keys.chunk, this.defaults.chunkSize));
    this.#apply(this.retryInput, this.#load(this.keys.retry, this.defaults.retryLimit));
  }

  #apply(input, value, key) {
    if (!input) return;
    input.value = value.toString();
    input.setAttribute('aria-invalid', 'false');
    if (key) localStorage.setItem(key, value.toString());
  }

  #bindEvents() {
    this.resetButton?.addEventListener('click', () => this.reset());
    this.chunkInput?.addEventListener('blur', () => this.#validate(this.chunkInput, this.keys.chunk, this.limits.chunkSize));
    this.retryInput?.addEventListener('blur', () => this.#validate(this.retryInput, this.keys.retry, this.limits.retryLimit));
  }

  #validate(input, key, limits) {
    if (!input) return;
    const val = validateNumericInput(input, limits);
    if (val === null) {
      input.setAttribute('aria-invalid', 'true');
      this.toast?.show(`Enter a value between ${limits.min} and ${limits.max}`, 'warn');
      return;
    }
    input.value = val.toString();
    input.setAttribute('aria-invalid', 'false');
    localStorage.setItem(key, val.toString());
  }

  #load(key, fallback) {
    try {
      const val = localStorage.getItem(key);
      if (val === null) return fallback;
      const num = parseInt(val, 10);
      return Number.isFinite(num) ? num : fallback;
    } catch { return fallback; }
  }
}
