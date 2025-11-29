/**
 * CyberBackup Client Application
 * Bundled from modular source files
 */

// --- Source: scripts/utils/formatters.js ---
const BYTE_UNITS = ['B', 'KB', 'MB', 'GB', 'TB'];

function formatBytes(bytes) {
  if (!Number.isFinite(bytes) || bytes < 0) {
    return '—';
  }
  if (bytes === 0) {
    return '0 B';
  }
  const exponent = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), BYTE_UNITS.length - 1);
  const value = bytes / Math.pow(1024, exponent);

  let precision;
  if (value >= 100) {
    precision = 0;
  } else if (value >= 10) {
    precision = 1;
  } else {
    precision = 2;
  }

  return `${value.toFixed(precision)} ${BYTE_UNITS[exponent]}`;
}

function formatSpeed(bytesPerSecond) {
  if (!Number.isFinite(bytesPerSecond) || bytesPerSecond < 0) {
    return '—';
  }
  if (bytesPerSecond === 0) {
    return '0 B/s';
  }
  const exponent = Math.min(Math.floor(Math.log(bytesPerSecond) / Math.log(1024)), BYTE_UNITS.length - 1);
  const value = bytesPerSecond / Math.pow(1024, exponent);

  let precision;
  if (value >= 100) {
    precision = 0;
  } else if (value >= 10) {
    precision = 1;
  } else {
    precision = 2;
  }

  return `${value.toFixed(precision)} ${BYTE_UNITS[exponent]}/s`;
}

/**
 * Format duration in seconds to human-readable string
 * @param {number} seconds - Duration in seconds
 * @returns {string} Formatted duration string
 */
function formatDuration(seconds) {
  if (!Number.isFinite(seconds) || seconds < 0) {
    return '—';
  }
  if (seconds < 1) {
    return `${seconds.toFixed(1)} s`;
  }
  const hrs = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);

  if (hrs > 0) {
    return `${hrs}h ${mins.toString().padStart(2, '0')}m`;
  }
  if (mins > 0) {
    return `${mins}m ${secs.toString().padStart(2, '0')}s`;
  }
  return `${secs}s`;
}

function formatLatency(ms) {
  if (!Number.isFinite(ms) || ms <= 0) {
    return '—';
  }
  return `${Math.max(1, Math.round(ms))} ms`;
}

function formatPercentage(value) {
  if (!Number.isFinite(value)) {
    return '0%';
  }
  return `${Math.min(100, Math.max(0, value)).toFixed(0)}%`;
}

/**
 * Parse server address string into host and port components
 * @param {string} input - Server address in format "host:port" or "host"
 * @returns {Object|null} Parsed address {host, port} or null if invalid
 */
function parseServerAddress(input) {
  if (!input || typeof input !== 'string') {
    return null;
  }
  let trimmed = input.trim();
  if (trimmed.length === 0) {
    return null;
  }

  // Strip protocol if provided
  if (trimmed.startsWith('http://')) trimmed = trimmed.slice(7);
  else if (trimmed.startsWith('https://')) trimmed = trimmed.slice(8);
  // Remove any trailing path
  const slashIdx = trimmed.indexOf('/');
  if (slashIdx > -1) trimmed = trimmed.slice(0, slashIdx);

  const hasColon = trimmed.includes(':');
  if (!hasColon) {
    return { host: trimmed, port: 1256 };
  }

  const [hostPart, portPart] = trimmed.split(':');
  const parsedPort = Number.parseInt(portPart, 10);
  if (!Number.isFinite(parsedPort) || parsedPort <= 0 || parsedPort > 65535) {
    return null;
  }
  return { host: hostPart, port: parsedPort };
}


// --- Source: scripts/services/connection-metrics.js ---
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


// --- Source: scripts/utils/dom.js ---
/**
 * Gets a DOM element by ID with optional fallback
 * @param {string} id - The element ID to find
 * @param {boolean} required - Whether to throw if not found
 * @returns {HTMLElement|null} The found element or null
 * @throws {Error} If the element is not found and required is true
 */
function getElement(id, required = true) {
  const el = document.getElementById(id);
  if (!el && required) {
    throw new Error(`Missing required element: #${id}`);
  }
  return el;
}

/**
 * Gets a DOM element by ID, returns null if not found (no throw)
 * @param {string} id - The element ID to find
 * @returns {HTMLElement|null} The found element or null
 */
function getOptionalElement(id) {
  return document.getElementById(id);
}

/**
 * Query for a DOM element using CSS selector and throw if not found
 * @param {string} selector - CSS selector to find the element
 * @param {ParentNode} parent - Parent node to search within (default: document)
 * @returns {HTMLElement} The found element
 * @throws {Error} If the element is not found
 */
function querySelector(selector, parent = document) {
  const el = parent.querySelector(selector);
  if (!el) {
    throw new Error(`Missing required element for selector: ${selector}`);
  }
  return el;
}

/**
 * Centralized DOM element cache containing all required UI elements
 * @namespace
 */
const dom = {
  container: querySelector('.container'),
  statusOutput: getElement('statusOutput'),
  connStatus: getElement('connStatus'),
  connHealth: getElement('connHealth'),
  connQuality: getElement('connQuality'),
  themeToggle: getElement('themeToggle'),
  serverInput: getElement('serverInput'),
  usernameInput: getElement('usernameInput'),
  serverValidIcon: getElement('serverValidIcon'),
  usernameValidIcon: getElement('usernameValidIcon'),
  serverHint: getElement('serverHint'),
  usernameHint: getElement('usernameHint'),
  fileDropZone: getElement('fileDropZone'),
  fileInput: getElement('fileInput'),
  // Optional elements that may not exist in new design
  fileSelectBtn: getOptionalElement('chooseFileBtn'),
  recentFilesBtn: getOptionalElement('recentFilesBtn'),
  clearFileBtn: getOptionalElement('clearFileBtn'),
  fileName: getOptionalElement('fileName'),
  fileInfo: getOptionalElement('fileInfo'),
  primaryActionBtn: getElement('primaryActionBtn'),
  pauseBtn: getElement('pauseBtn'),
  resumeBtn: getElement('resumeBtn'),
  stopBtn: getElement('stopBtn'),
  advChunkSize: getOptionalElement('advChunkSize'),
  advRetryLimit: getOptionalElement('advRetryLimit'),
  advResetBtn: getOptionalElement('advResetBtn'),
  // Advanced settings panel elements
  advancedPanel: getOptionalElement('advancedPanel'),
  advancedContent: getOptionalElement('advancedContent'),
  phaseText: getElement('phaseText'),
  progressRing: getElement('progressRing'),
  progressArc: getElement('progressArc'),
  progressPct: getElement('progressPct'),
  etaText: getElement('etaText'),
  stats: {
    bytes: getElement('statBytes'),
    speed: getElement('statSpeed'),
    size: getElement('statSize'),
    elapsed: getElement('statElapsed'),
  },
  // Log filter buttons
  logFilters: [
    getElement('filterAll'),
    getElement('filterInfo'),
    getElement('filterWarn'),
    getElement('filterError'),
  ],
  // Log filter segment indicator (for sliding animation)
  segmentIndicator: getOptionalElement('segmentIndicator'),
  logAutoscrollToggle: getOptionalElement('logAutoscrollToggle'),
  logExportBtn: getOptionalElement('logExportBtn'),
  logClearBtn: getOptionalElement('logClearBtn'),
  logDemoBtn: getOptionalElement('logDemoBtn'),
  logSearchInput: getOptionalElement('logSearchInput'),
  searchClearBtn: getOptionalElement('searchClearBtn'),
  logEntryCount: getOptionalElement('logEntryCount'),
  logContainer: getElement('logContainer'),
  logsEmptyState: getOptionalElement('logsEmptyState'),
  toastStack: getElement('toastStack'),
  modal: getElement('modalConfirm'),
  modalCancelBtn: getElement('modalCancelBtn'),
  modalOkBtn: getElement('modalOkBtn'),
  srLive: getElement('srLive'),
};

/**
 * Utility functions for DOM manipulation and error-safe operations
 */
const domUtils = {
  /**
   * Safely execute a DOM operation with error handling
   * @param {Function} operation - DOM operation to execute
   * @param {string} context - Context for error messages
   * @returns {*} Result of the operation or null if failed
   */
  safeExecute(operation, context = 'DOM operation') {
    try {
      return operation();
    } catch (error) {
      console.warn(`DOM error in ${context}:`, error);
      return null;
    }
  },

  /**
   * Check if element exists and is visible
   * @param {HTMLElement} element - Element to check
   * @returns {boolean} True if element exists and is visible
   */
  isVisible(element) {
    return element &&
           element.offsetWidth > 0 &&
           element.offsetHeight > 0 &&
           getComputedStyle(element).display !== 'none';
  },

  /**
   * Add event listener with automatic cleanup
   * @param {HTMLElement} element - Target element
   * @param {string} event - Event type
   * @param {Function} handler - Event handler
   * @param {Object} options - Event listener options
   * @returns {Function} Cleanup function to remove the listener
   */
  addCleanupListener(element, event, handler, options = {}) {
    element.addEventListener(event, handler, options);
    return () => element.removeEventListener(event, handler, options);
  },

  /**
   * Debounce function calls
   * @param {Function} func - Function to debounce
   * @param {number} wait - Wait time in milliseconds
   * @returns {Function} Debounced function
   */
  debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  },

  /**
   * Throttle function calls
   * @param {Function} func - Function to throttle
   * @param {number} limit - Throttle limit in milliseconds
   * @returns {Function} Throttled function
   */
  throttle(func, limit) {
    let inThrottle;
    return function executedFunction(...args) {
      if (!inThrottle) {
        func.apply(this, args);
        inThrottle = true;
        setTimeout(() => inThrottle = false, limit);
      }
    };
  }
};


// --- Source: scripts/utils/performance-optimizer.js ---
/**
 * Performance Optimizer - RAF-based DOM update batching
 * Prevents layout thrashing by batching DOM updates into single animation frames
 */

class PerformanceOptimizer {
  constructor() {
    this.pendingUpdates = new Map();
    this.rafId = null;
    this.isScheduled = false;
  }

  /**
   * Schedule a DOM update to run in the next animation frame
   * @param {string} key - Unique key for this update
   * @param {Function} updateFn - Function that performs DOM updates
   */
  scheduleUpdate(key, updateFn) {
    this.pendingUpdates.set(key, updateFn);

    if (!this.isScheduled) {
      this.isScheduled = true;
      this.rafId = requestAnimationFrame(() => this.flush());
    }
  }

  /**
   * Execute all pending updates in a single frame
   */
  flush() {
    if (this.pendingUpdates.size === 0) {
      this.isScheduled = false;
      return;
    }

    // Execute all pending updates
    for (const [key, updateFn] of this.pendingUpdates) {
      try {
        updateFn();
      } catch (error) {
        console.error(`Update failed for ${key}:`, error);
      }
    }

    this.pendingUpdates.clear();
    this.isScheduled = false;
  }

  /**
   * Cancel all pending updates
   */
  cancel() {
    if (this.rafId) {
      cancelAnimationFrame(this.rafId);
      this.rafId = null;
    }
    this.pendingUpdates.clear();
    this.isScheduled = false;
  }
}

/**
 * Debounce function with RAF optimization
 * @param {Function} fn - Function to debounce
 * @param {number} wait - Wait time in milliseconds
 * @returns {Function} Debounced function
 */
function rafDebounce(fn, wait = 16) {
  let timeoutId = null;
  let rafId = null;

  return function debounced(...args) {
    const later = () => {
      timeoutId = null;
      rafId = requestAnimationFrame(() => {
        fn.apply(this, args);
        rafId = null;
      });
    };

    if (timeoutId) {
      clearTimeout(timeoutId);
    }
    if (rafId) {
      cancelAnimationFrame(rafId);
    }

    timeoutId = setTimeout(later, wait);
  };
}

/**
 * Throttle function with RAF optimization
 * @param {Function} fn - Function to throttle
 * @param {number} limit - Limit in milliseconds
 * @returns {Function} Throttled function
 */
function rafThrottle(fn, limit = 16) {
  let inThrottle = false;
  let rafId = null;

  return function throttled(...args) {
    if (!inThrottle) {
      rafId = requestAnimationFrame(() => {
        fn.apply(this, args);
        rafId = null;
      });
      inThrottle = true;
      setTimeout(() => {
        inThrottle = false;
      }, limit);
    }
  };
}

/**
 * Batch DOM reads and writes to prevent layout thrashing
 */
class DOMBatcher {
  constructor() {
    this.reads = [];
    this.writes = [];
    this.scheduled = false;
  }

  /**
   * Schedule a DOM read operation
   * @param {Function} readFn - Function that reads from the DOM
   * @returns {Promise} Promise that resolves with the read result
   */
  read(readFn) {
    return new Promise((resolve) => {
      this.reads.push(() => {
        const result = readFn();
        resolve(result);
      });
      this.schedule();
    });
  }

  /**
   * Schedule a DOM write operation
   * @param {Function} writeFn - Function that writes to the DOM
   * @returns {Promise} Promise that resolves when write is complete
   */
  write(writeFn) {
    return new Promise((resolve) => {
      this.writes.push(() => {
        writeFn();
        resolve();
      });
      this.schedule();
    });
  }

  /**
   * Schedule the batched execution
   */
  schedule() {
    if (!this.scheduled) {
      this.scheduled = true;
      requestAnimationFrame(() => this.flush());
    }
  }

  /**
   * Execute all batched operations
   */
  flush() {
    // Execute all reads first
    const reads = this.reads.splice(0);
    reads.forEach(read => read());

    // Then execute all writes
    const writes = this.writes.splice(0);
    writes.forEach(write => write());

    this.scheduled = false;
  }
}

/**
 * Smooth value interpolation for animated counters
 */
class SmoothCounter {
  constructor(element, options = {}) {
    this.element = element;
    this.targetValue = 0;
    this.currentValue = 0;
    this.duration = options.duration || 300;
    this.formatFn = options.formatFn || ((v) => Math.round(v).toString());
    this.rafId = null;
    this.startTime = null;
    this.startValue = 0;
  }

  /**
   * Set a new target value and animate towards it
   * @param {number} value - Target value
   */
  setValue(value) {
    if (value === this.targetValue) return;

    this.startValue = this.currentValue;
    this.targetValue = value;
    this.startTime = null;

    if (this.rafId) {
      cancelAnimationFrame(this.rafId);
    }

    this.animate();
  }

  /**
   * Animation loop
   */
  animate(timestamp) {
    if (!this.startTime) {
      this.startTime = timestamp;
    }

    const elapsed = timestamp - this.startTime;
    const progress = Math.min(elapsed / this.duration, 1);

    // Ease-out cubic
    const eased = 1 - Math.pow(1 - progress, 3);
    this.currentValue = this.startValue + (this.targetValue - this.startValue) * eased;

    this.element.textContent = this.formatFn(this.currentValue);

    if (progress < 1) {
      this.rafId = requestAnimationFrame((t) => this.animate(t));
    } else {
      this.currentValue = this.targetValue;
      this.element.textContent = this.formatFn(this.targetValue);
      this.rafId = null;
    }
  }

  /**
   * Stop animation and set value immediately
   * @param {number} value - Value to set
   */
  setImmediate(value) {
    if (this.rafId) {
      cancelAnimationFrame(this.rafId);
      this.rafId = null;
    }
    this.currentValue = value;
    this.targetValue = value;
    this.element.textContent = this.formatFn(value);
  }

  /**
   * Cleanup
   */
  destroy() {
    if (this.rafId) {
      cancelAnimationFrame(this.rafId);
    }
  }
}

/**
 * Intersection Observer helper for lazy loading/animations
 */
function createIntersectionObserver(callback, options = {}) {
  const defaultOptions = {
    root: null,
    rootMargin: '0px',
    threshold: 0.1,
    ...options
  };

  return new IntersectionObserver(callback, defaultOptions);
}

/**
 * Measure performance of a function
 */
function measurePerformance(label, fn) {
  const start = performance.now();
  const result = fn();
  const end = performance.now();
  console.log(`[Performance] ${label}: ${(end - start).toFixed(2)}ms`);
  return result;
}

/**
 * Create a singleton instance
 */
const performanceOptimizer = new PerformanceOptimizer();
const domBatcher = new DOMBatcher();



// --- Source: scripts/ui/accessibility.js ---
class ScreenReaderAnnouncer {
  constructor(liveRegion) {
    this.liveRegion = liveRegion;
    this._pendingMessages = [];
    this._isAnnouncing = false;
  }

  announce(message) {
    if (!this.liveRegion) return;
    this._pendingMessages.push(String(message));
    if (!this._isAnnouncing) {
      void this.#flushQueue();
    }
  }

  async #flushQueue() {
    this._isAnnouncing = true;
    while (this._pendingMessages.length > 0) {
      const next = this._pendingMessages.shift();
      if (!next) {
        continue;
      }
      this.liveRegion.textContent = '';
      await new Promise((resolve) => {
        requestAnimationFrame(() => {
          this.liveRegion.textContent = next;
          setTimeout(resolve, 120);
        });
      });
    }
    this._isAnnouncing = false;
  }
}


// --- Source: scripts/ui/toasts.js ---
const DEFAULT_DURATION = 4000;

class ToastManager {
  #stack;
  #activeToasts;

  constructor(stackElement) {
    this.#stack = stackElement;
    this.#activeToasts = new Set();
  }

  show(message, variant = 'info', duration = DEFAULT_DURATION) {
    if (!this.#stack) {
      return () => {};
    }
    const toast = document.createElement('div');
    toast.className = `toast ${variant}`;
    toast.setAttribute('role', 'status');
    toast.setAttribute('aria-live', 'polite');
    toast.textContent = message;
    this.#stack.append(toast);
    this.#activeToasts.add(toast);

    const close = () => {
      if (!this.#activeToasts.has(toast)) {
        return;
      }
      this.#activeToasts.delete(toast);
      toast.classList.add('closing');
      toast.addEventListener('transitionend', () => toast.remove(), { once: true });
      // Fallback removal
      setTimeout(() => toast.remove(), 300);
    };

    if (duration > 0) {
      setTimeout(close, duration);
    }

    return close;
  }

  clear() {
    for (const toast of this.#activeToasts) {
      toast.remove();
    }
    this.#activeToasts.clear();
  }
}


// --- Source: scripts/state/state-store.js ---
// Optimized shallow clone for primitive values and simple objects
function shallowClone(value) {
  if (value === null || typeof value !== 'object') {
    return value;
  }

  if (Array.isArray(value)) {
    return [...value];
  }

  return { ...value };
}

// Deep equality check to avoid unnecessary updates
function shallowEqual(objA, objB) {
  if (objA === objB) return true;
  if (typeof objA !== 'object' || typeof objB !== 'object' || objA === null || objB === null) {
    return false;
  }

  const keysA = Object.keys(objA);
  const keysB = Object.keys(objB);

  if (keysA.length !== keysB.length) return false;

  for (const key of keysA) {
    if (objA[key] !== objB[key]) return false;
  }

  return true;
}

class StateStore {
  #state;
  #listeners;
  #pendingUpdate;
  #updateScheduled;

  constructor(initialState) {
    this.#state = shallowClone(initialState);
    this.#listeners = new Set();
    this.#pendingUpdate = null;
    this.#updateScheduled = false;
  }

  get snapshot() {
    // Return direct reference for reads (caller shouldn't mutate)
    // This avoids expensive deep cloning on every read
    return this.#state;
  }

  update(patch) {
    // Batch updates using requestAnimationFrame
    if (!this.#pendingUpdate) {
      this.#pendingUpdate = {};
    }

    Object.assign(this.#pendingUpdate, patch);

    if (!this.#updateScheduled) {
      this.#updateScheduled = true;
      requestAnimationFrame(() => this.#flushUpdate());
    }
  }

  #flushUpdate() {
    if (!this.#pendingUpdate) {
      this.#updateScheduled = false;
      return;
    }

    const next = { ...this.#state, ...this.#pendingUpdate };

    // Only notify if state actually changed
    if (!shallowEqual(this.#state, next)) {
      this.#state = next;
      this.#notifyListeners(next);
    }

    this.#pendingUpdate = null;
    this.#updateScheduled = false;
  }

  // Force immediate update without batching (use sparingly)
  updateImmediate(patch) {
    const next = { ...this.#state, ...patch };
    if (!shallowEqual(this.#state, next)) {
      this.#state = next;
      this.#notifyListeners(next);
    }
  }

  mutate(mutator) {
    const next = { ...this.#state };
    mutator(next);

    if (!shallowEqual(this.#state, next)) {
      this.#state = next;
      this.#notifyListeners(next);
    }
  }

  #notifyListeners(state) {
    // Use microtask queue for listener notifications
    queueMicrotask(() => {
      for (const listener of this.#listeners) {
        try {
          listener(state);
        } catch (error) {
          console.error('State listener error:', error);
        }
      }
    });
  }

  subscribe(listener) {
    if (typeof listener !== 'function') {
      throw new TypeError('Listener must be a function');
    }
    this.#listeners.add(listener);

    // Initial notification
    queueMicrotask(() => listener(this.#state));

    return () => this.#listeners.delete(listener);
  }
}


// --- Source: scripts/services/api-client.js ---
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


// --- Source: scripts/services/log-store.js ---
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

  constructor(container) {
    this.#entries = [];
    this.#filter = 'all';
    this.#autoScroll = true;
    this.#container = container;
    this.#emptyState = document.getElementById('logsEmptyState');
    this.#countElement = document.getElementById('logEntryCount');
  }

  setFilter(filter) {
    this.#filter = filter;
    this.render();
  }

  setAutoScroll(enabled) {
    this.#autoScroll = Boolean(enabled);
  }

  add(message, { level = 'info', phase, timestamp = new Date() } = {}) {
    const entry = {
      timestamp: timestamp instanceof Date ? timestamp : new Date(timestamp),
      message,
      phase: phase || null,
      level: normalizeLevel(level),
    };
    this.#entries.push(entry);
    if (this.#entries.length > 500) {
      this.#entries.splice(0, this.#entries.length - 500);
    }
    this.render();
  }

  clear() {
    this.#entries = [];
    this.render();
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

  render() {
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

    const fragment = document.createDocumentFragment();
    const entriesToShow = filteredEntries.slice(-400);

    for (let i = 0; i < entriesToShow.length; i++) {
      const entry = entriesToShow[i];
      const isNew = i === entriesToShow.length - 1 && entriesToShow.length === this.#entries.length;

      const row = document.createElement('div');
      row.className = `log-entry log-${entry.level}${isNew ? ' log-entry-new' : ''}`;
      row.dataset.level = entry.level;

      // Level indicator bar
      const indicator = document.createElement('div');
      indicator.className = 'log-indicator';

      // Icon
      const iconWrapper = document.createElement('div');
      iconWrapper.className = 'log-icon-wrapper';
      iconWrapper.innerHTML = LEVEL_ICONS[entry.level] || LEVEL_ICONS.info;

      // Timestamp
      const time = document.createElement('span');
      time.className = 'log-timestamp';
      time.textContent = this.#formatTime(entry.timestamp);

      // Level badge
      const levelBadge = document.createElement('span');
      levelBadge.className = `log-level-badge log-level-${entry.level}`;
      levelBadge.textContent = entry.level.toUpperCase();

      // Message
      const msg = document.createElement('span');
      msg.className = 'log-message';
      msg.textContent = entry.message;

      row.append(indicator, iconWrapper, time, levelBadge, msg);
      fragment.append(row);
    }

    // Clear container and add entries (preserve empty state element)
    const children = Array.from(this.#container.children);
    for (const child of children) {
      if (child.id !== 'logsEmptyState') {
        child.remove();
      }
    }
    this.#container.append(fragment);

    if (this.#autoScroll) {
      this.#container.scrollTop = this.#container.scrollHeight;
    }
  }
}



// --- Source: scripts/services/theme-manager.js ---
const STORAGE_KEY = 'cyberbackup-theme';

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
      localStorage.setItem(STORAGE_KEY, theme);
    } catch (error) {
      console.warn('Failed to persist theme preference', error);
    }
  }

  #load() {
    try {
      return localStorage.getItem(STORAGE_KEY);
    } catch {
      return null;
    }
  }
}


// --- Source: scripts/services/advanced-settings.js ---
const STORAGE_KEYS = {
  chunk: 'cyberbackup-chunk-size',
  retry: 'cyberbackup-retry-limit',
};

const DEFAULTS = {
  chunkSize: 8,
  retryLimit: 3,
};

const LIMITS = {
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
    const chunk = parseNumericInput(this.chunkInput, LIMITS.chunkSize);
    const retry = parseNumericInput(this.retryInput, LIMITS.retryLimit);
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
    this.#applyValue(this.chunkInput, DEFAULTS.chunkSize, STORAGE_KEYS.chunk);
    this.#applyValue(this.retryInput, DEFAULTS.retryLimit, STORAGE_KEYS.retry);
    this.toast?.show('Advanced settings restored to defaults', 'info', 2200);
    this.announcer?.announce('Advanced settings reset to defaults');
  }

  #hydrate() {
    this.#applyValue(this.chunkInput, this.#loadFromStorage(STORAGE_KEYS.chunk, DEFAULTS.chunkSize));
    this.#applyValue(this.retryInput, this.#loadFromStorage(STORAGE_KEYS.retry, DEFAULTS.retryLimit));
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
      this.chunkInput.addEventListener('blur', () => this.#validateAndPersist(this.chunkInput, STORAGE_KEYS.chunk, LIMITS.chunkSize));
    }

    if (this.retryInput) {
      this.retryInput.addEventListener('blur', () => this.#validateAndPersist(this.retryInput, STORAGE_KEYS.retry, LIMITS.retryLimit));
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
      return Number.isFinite(numeric) ? clamp(numeric, LIMITS[key === STORAGE_KEYS.chunk ? 'chunkSize' : 'retryLimit']) : fallback;
    } catch {
      return fallback;
    }
  }
}


// --- Source: scripts/services/socket-client.js ---
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


// --- Source: scripts/services/connection-monitor.js ---

const DEFAULT_INTERVAL = 7000;

/* CACHE BUSTER v2.0 - Force browser reload */

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


// --- Source: scripts/services/file-manager.js ---

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


// --- Source: scripts/app.js ---
// Utility functions are defined above in the bundled file

// Error boundary utilities
class ErrorBoundary {
  static handle(error, context, recovery = null) {
    console.error(`[${context}] Error:`, error);

    // Create user-friendly error message
    const userMessage = this.formatUserMessage(error, context);

    // Log to application logs if available
    try {
      if (globalThis.cyberBackupApp?.logs) {
        globalThis.cyberBackupApp.logs.add(userMessage, { level: 'error', phase: 'ERROR' });
      }
    } catch (logError) {
      console.warn('Failed to log error to application logs:', logError);
    }

    // Show toast notification if available
    try {
      if (globalThis.cyberBackupApp?.toast) {
        globalThis.cyberBackupApp.toast.show(userMessage, 'error', 5000);
      }
    } catch (toastError) {
      console.warn('Failed to show error toast:', toastError);
    }

    // Attempt recovery if provided
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
      return `Network error: Unable to connect to server. Please check your connection and try again.`;
    }

    if (error.name === 'TypeError' && error.message.includes('fetch')) {
      return `Connection error: Server is not responding. Please verify the server is running.`;
    }

    if (error.message.includes('Missing required element')) {
      return `UI error: A required interface element is missing. Please refresh the page.`;
    }

    if (error.name === 'AbortError') {
      return `Operation cancelled.`;
    }

    // Generic error message
    return error.message || `An unexpected error occurred in ${context}. Please try again.`;
  }

  static async withErrorHandling(promise, context, recovery = null) {
    try {
      return await promise;
    } catch (error) {
      this.handle(error, context, recovery);
      throw error; // Re-throw so calling code can handle it if needed
    }
  }

  static wrapFunction(fn, context, recovery = null) {
    return (...args) => {
      try {
        const result = fn.apply(this, args);

        // Handle both sync and async functions
        if (result && typeof result.catch === 'function') {
          return result.catch(error => {
            this.handle(error, context, recovery);
            throw error;
          });
        }

        return result;
      } catch (error) {
        this.handle(error, context, recovery);
        throw error;
      }
    };
  }
}

const CIRCUMFERENCE = 282.743; // Precomputed circumference for r=45 circle
const STATUS_INTERVAL_MS = 2500;
const GENERAL_STATUS_INTERVAL_MS = 12000;

const INITIAL_STATE = {
  connecting: false,
  connected: false,
  connectionLatency: null,
  connectionQuality: 'offline',
  jobId: null,
  jobStatus: 'idle',
  jobPhase: 'Idle',
  jobMessage: 'Idle',
  jobRunning: false,
  paused: false,
  progress: 0,
  bytesTransferred: 0,
  totalBytes: 0,
  speed: 0,
  etaSeconds: null,
  elapsedSeconds: 0,
  startTimestamp: null,
  fileName: null,
  fileSize: 0,
  lastUpdated: null,
  systemMetrics: null,
  connectionAttempted: false,
};

class App {
  constructor() {
    // Initialize with error boundaries
    try {
      this.api = new ApiClient('');
      this.toast = new ToastManager(dom.toastStack);
      this.announcer = new ScreenReaderAnnouncer(dom.srLive);
      this.state = new StateStore(INITIAL_STATE);
      this.logs = new LogStore(dom.logContainer);
      this.theme = new ThemeManager(dom.themeToggle);
    } catch (error) {
      ErrorBoundary.handle(error, 'App Initialization', () => {
        // Fallback initialization
        this.state = new StateStore(INITIAL_STATE);
        this.toast = { show: (msg, type, duration) => console.log(`${type}: ${msg}`) };
        this.logs = { add: (msg, opts) => console.log(`LOG: ${msg}`) };
      });
      return;
    }
    this.fileManager = new FileManager({
      dropZone: dom.fileDropZone,
      fileInput: dom.fileInput,
      selectButton: dom.fileSelectBtn,
      clearButton: dom.clearFileBtn,
      recentButton: dom.recentFilesBtn,
      nameLabel: dom.fileName,
      infoLabel: dom.fileInfo,
      announcer: this.announcer,
      onRecent: (meta) => {
        const message = `Most recent • ${meta.name} (${meta.formattedSize})`;
        this.toast.show(message, 'info', 2600);
      },
    });
    this.advanced = new AdvancedSettings({
      chunkInput: dom.advChunkSize,
      retryInput: dom.advRetryLimit,
      resetButton: dom.advResetBtn,
      toast: this.toast,
      announcer: this.announcer,
    });

    this.connectionMonitor = new ConnectionMonitor({
      api: this.api,
      onResult: (payload) => this.#handleConnectionUpdate(payload),
    });

    this.socket = new SocketClient({
      onConnect: () => this.#onSocketConnect(),
      onDisconnect: (reason) => this.#onSocketDisconnect(reason),
      onError: (error) => this.#onSocketError(error),
      onStatus: (payload) => this.#onSocketStatus(payload),
      onProgress: (payload) => this.#handleSocketProgress(payload),
      onFileReceipt: (payload) => this.#handleFileReceipt(payload),
    });

    this.generalStatusTimer = null;
    this.jobStatusTimer = null;
    this.lastSpeedSample = null;
    this.lastConnectionState = null;
    this.previousFocus = null;
    this.modalKeyHandler = null;
    this.modalFocusables = [];
    this.actionLock = false;

      try {
      this.#bindEvents();
      this.state.subscribe((snapshot) => this.#render(snapshot));
    } catch (error) {
      ErrorBoundary.handle(error, 'Event Binding', () => {
        // Minimal fallback binding
        const primaryBtn = document.getElementById('primaryActionBtn');
        if (primaryBtn) {
          primaryBtn.addEventListener('click', () => {
            this.toast.show('Application initialization incomplete. Please refresh.', 'error', 5000);
          });
        }
      });
    }
  }

  async init() {
    return ErrorBoundary.withErrorHandling(async () => {
      this.connectionMonitor.start();
      await this.socket.start();
      await this.#bootstrap();
    }, 'Application Initialization', () => {
      // Fallback to basic functionality
      this.logs.add('Application started in safe mode with limited functionality', { level: 'warn' });
    });
  }

  async #bootstrap() {
    try {
      await this.#refreshStatus();
      this.#startGeneralStatusLoop();
    } catch (error) {
      console.warn('Initial status check failed', error);
    }
  }

  #bindEvents() {
    dom.primaryActionBtn.addEventListener('click', () => this.#handlePrimaryAction());
    dom.pauseBtn.addEventListener('click', () => this.#handlePause());
    dom.resumeBtn.addEventListener('click', () => this.#handleResume());
    dom.stopBtn.addEventListener('click', () => this.#openStopModal());

    dom.modalCancelBtn.addEventListener('click', () => this.#closeModalWithAnimation());
    dom.modalOkBtn.addEventListener('click', () => this.#confirmStop());
    dom.modal.addEventListener('close', () => this.#handleModalClosed());
    dom.modal.addEventListener('cancel', (event) => {
      event.preventDefault();
      this.#closeModalWithAnimation();
    });

    dom.serverInput.addEventListener('input', () => {
      dom.serverHint.setAttribute('hidden', 'true');
      this.#validateInput(dom.serverInput, dom.serverValidIcon);
    });

    dom.usernameInput.addEventListener('input', () => {
      dom.usernameHint.setAttribute('hidden', 'true');
      this.#validateInput(dom.usernameInput, dom.usernameValidIcon);
    });

    if (dom.logAutoscrollToggle) {
      dom.logAutoscrollToggle.addEventListener('change', (event) => {
        const enabled = event.currentTarget.checked;
        this.logs.setAutoScroll(enabled);
        this.toast.show(`Autoscroll ${enabled ? 'enabled' : 'disabled'}`, 'info', 1800);
      });
    }

    if (dom.logExportBtn) {
      dom.logExportBtn.addEventListener('click', () => this.#exportLogs());
    }

    // Log clear button
    if (dom.logClearBtn) {
      dom.logClearBtn.addEventListener('click', () => {
        this.logs.clear();
        this.toast.show('Logs cleared', 'info', 1800);
      });
    }

    // Log demo button - adds sample log entries for testing
    if (dom.logDemoBtn) {
      dom.logDemoBtn.addEventListener('click', () => {
        this.#generateDemoLogs();
      });
    }

    // Log search functionality
    if (dom.logSearchInput) {
      dom.logSearchInput.addEventListener('input', (event) => {
        const query = event.target.value.trim().toLowerCase();
        this.#filterLogsBySearch(query);

        // Show/hide clear button
        if (dom.searchClearBtn) {
          dom.searchClearBtn.hidden = !query;
        }
      });
    }

    if (dom.searchClearBtn) {
      dom.searchClearBtn.addEventListener('click', () => {
        if (dom.logSearchInput) {
          dom.logSearchInput.value = '';
          dom.searchClearBtn.hidden = true;
          this.#filterLogsBySearch('');
        }
      });
    }

    // Segmented filter control with sliding indicator
    for (let i = 0; i < dom.logFilters.length; i++) {
      const button = dom.logFilters[i];
      button.addEventListener('click', () => {
        // Update active state for all buttons
        for (const other of dom.logFilters) {
          const isActive = other === button;
          other.classList.toggle('active', isActive);
          other.setAttribute('aria-pressed', isActive ? 'true' : 'false');
        }

        // Animate segment indicator
        if (dom.segmentIndicator) {
          const segmentWidth = 100 / dom.logFilters.length;
          dom.segmentIndicator.style.width = `calc(${segmentWidth}% - 3px)`;
          dom.segmentIndicator.style.left = `calc(${i * segmentWidth}% + 4px)`;
        }

        // Apply filter
        this.logs.setFilter(button.dataset.level || 'all');
      });
    }

    document.addEventListener('keydown', (event) => this.#handleKeydown(event));
  }

  async #handlePrimaryAction() {
    const { connecting, connected, jobStatus } = this.state.snapshot;
    if (connecting || this.actionLock) {
      return;
    }

    let connectionAttempted = false;
    let connectionSucceeded = false;

    try {
      this.actionLock = true;
      if (!connected) {
        connectionAttempted = true;
        await this.#connect();
        connectionSucceeded = true;
        return;
      }

      if (jobStatus === 'running') {
        this.toast.show('Backup already in progress', 'info');
        return;
      }

      const { file } = this.fileManager;
      if (!file) {
        this.toast.show('Please select a file to back up', 'error');
        this.announcer.announce('Select a file before starting backup');
        return;
      }

      await this.#startBackup(file);
    } catch (error) {
      console.error('Primary action failed', error);
      this.toast.show(error.message || 'Operation failed', 'error', 5000);
    } finally {
      this.actionLock = false;
      const patch = { connecting: false };
      // If connection was attempted but failed, ensure connected is false
      if (connectionAttempted && !connectionSucceeded) {
        patch.connected = false;
      }
      this.state.update(patch);
    }
  }

  #validateInput(input, icon) {
    if (!input || !icon) return;

    const value = input.value.trim();
    if (!value) {
      input.classList.remove('error', 'success');
      icon.classList.remove('error', 'success', 'show');
      return;
    }

    let isValid = false;
    if (input === dom.serverInput) {
      isValid = Boolean(parseServerAddress(value));
    } else if (input === dom.usernameInput) {
      isValid = value.length > 0;
    }

    if (isValid) {
      input.classList.remove('error');
      input.classList.add('success');
      icon.classList.remove('error');
      icon.classList.add('success', 'show');
      icon.textContent = '✓';
    } else {
      input.classList.remove('success');
      input.classList.add('error');
      icon.classList.remove('success');
      icon.classList.add('error', 'show');
      icon.textContent = '✕';
    }
  }

  async #connect() {
    const serverRaw = dom.serverInput.value.trim();
    const username = dom.usernameInput.value.trim();

    const server = parseServerAddress(serverRaw);
    if (!server) {
      dom.serverHint.removeAttribute('hidden');
      dom.serverInput.classList.add('error');
      this.#validateInput(dom.serverInput, dom.serverValidIcon);
      dom.serverInput.focus();
      throw new Error('Enter a valid server address in host:port format');
    }
    if (!username) {
      dom.usernameHint.removeAttribute('hidden');
      dom.usernameInput.classList.add('error');
      this.#validateInput(dom.usernameInput, dom.usernameValidIcon);
      dom.usernameInput.focus();
      throw new Error('Username is required');
    }

    this.state.update({ connecting: true, connectionAttempted: true });
    this.toast.show(`Connecting to ${server.host}:${server.port}…`, 'info', 2600);

    const startTime = performance.now();
    const result = await this.api.connect({ host: server.host, port: server.port, username });
    const latency = performance.now() - startTime;

    this.logs.add(`Connected to ${server.host}:${server.port}`, { level: 'info', phase: 'CONNECT' });
    this.toast.show(result.message || 'Connected successfully', 'success', 2800);
    this.announcer.announce('Connection established');

    this.state.update({
      connecting: false,
      connected: true,
      connectionLatency: latency,
      connectionQuality: evaluateConnectionQuality({ latencyMs: latency }),
    });

    this.connectionMonitor.forcePing();
  }

  async #startBackup(file) {
    const server = parseServerAddress(dom.serverInput.value.trim());
    const username = dom.usernameInput.value.trim();
    if (!server || !username) {
      throw new Error('Provide server and username before starting backup');
    }

    const options = this.advanced.getOptions();
    this.toast.show(`Starting backup for ${file.name}`, 'info');

    const response = await this.api.startBackup({
      file,
      username,
      host: server.host,
      port: server.port,
      options,
    });

    this.logs.add(`Backup started for ${file.name}`, { level: 'info', phase: 'START' });
    this.announcer.announce(`Backup started for ${file.name}`);

    const now = Date.now();
    this.state.update({
      jobId: response.job_id,
      jobStatus: 'running',
      jobPhase: 'INITIALIZING',
      jobMessage: response.message || 'Backup initializing…',
      jobRunning: true,
      progress: 0,
      bytesTransferred: 0,
      totalBytes: file.size,
      speed: 0,
      etaSeconds: null,
      startTimestamp: now,
      lastUpdated: now,
      fileName: file.name,
      fileSize: file.size,
      paused: false,
    });

    this.lastSpeedSample = { bytes: 0, time: now };
    this.socket.watchJob(response.job_id);
    this.#startJobStatusLoop(response.job_id);
  }

  async #handlePause() {
    const { jobId, paused } = this.state.snapshot;
    if (!jobId || paused) {
      return;
    }
    try {
      await this.api.pause();
      this.toast.show('Pause command sent', 'info');
      this.state.update({ paused: true });
    } catch (error) {
      this.toast.show(error.message || 'Pause failed', 'error');
    }
  }

  async #handleResume() {
    const { jobId, paused } = this.state.snapshot;
    if (!jobId || !paused) {
      return;
    }
    try {
      await this.api.resume();
      this.toast.show('Resume command sent', 'info');
      this.state.update({ paused: false });
    } catch (error) {
      this.toast.show(error.message || 'Resume failed', 'error');
    }
  }

  #openStopModal() {
    if (typeof dom.modal.showModal !== 'function') {
      return;
    }

    this.previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    dom.modal.showModal();
    this.#setupModalFocusTrap();
  }

  #closeModalWithAnimation() {
    if (!dom.modal || !dom.modal.open) return;

    // Add closing class for animation
    dom.modal.classList.add('closing');

    // Wait for animation before closing
    setTimeout(() => {
      dom.modal.close();
      dom.modal.classList.remove('closing');
    }, 250);
  }

  async #confirmStop() {
    this.#closeModalWithAnimation();
    const { jobId } = this.state.snapshot;
    if (!jobId) {
      return;
    }
    try {
      await this.api.stop();
      this.toast.show('Stop command sent', 'warn');
      this.logs.add('Stop command issued by user', { level: 'warn', phase: 'STOP' });
      this.state.update({
        jobStatus: 'idle',
        jobRunning: false,
        jobId: null,
        progress: 0,
        speed: 0,
        etaSeconds: null,
        paused: false,
        lastUpdated: Date.now(),
      });
      this.socket.clearJob();
      this.lastSpeedSample = null;
      this.#stopJobStatusLoop();
      this.connectionMonitor.forcePing();
      this.announcer.announce('Backup stop requested');
    } catch (error) {
      this.toast.show(error.message || 'Stop failed', 'error');
    }
  }

  #handleModalClosed() {
    this.#teardownModalFocusTrap();
    if (this.previousFocus && typeof this.previousFocus.focus === 'function') {
      this.previousFocus.focus();
    }
    this.previousFocus = null;
  }

  #setupModalFocusTrap() {
    const focusableSelectors = [
      'button:not([disabled])',
      'a[href]',
      'input:not([disabled])',
      'select:not([disabled])',
      'textarea:not([disabled])',
      '[tabindex]:not([tabindex="-1"])',
    ].join(', ');

    this.modalFocusables = Array.from(dom.modal.querySelectorAll(focusableSelectors)).filter((el) =>
      el instanceof HTMLElement && !el.hasAttribute('aria-hidden'),
    );

    if (this.modalKeyHandler) {
      dom.modal.removeEventListener('keydown', this.modalKeyHandler);
    }

    this.modalKeyHandler = (event) => this.#handleModalKeydown(event);
    dom.modal.addEventListener('keydown', this.modalKeyHandler);

    globalThis.requestAnimationFrame(() => {
      const target = this.modalFocusables[0] || dom.modal;
      if (target && typeof target.focus === 'function') {
        target.focus();
      }
    });
  }

  #teardownModalFocusTrap() {
    if (this.modalKeyHandler) {
      dom.modal.removeEventListener('keydown', this.modalKeyHandler);
      this.modalKeyHandler = null;
    }
    this.modalFocusables = [];
  }

  #handleModalKeydown(event) {
    if (event.key !== 'Tab' || this.modalFocusables.length === 0) {
      return;
    }

    const first = this.modalFocusables[0];
    const last = this.modalFocusables[this.modalFocusables.length - 1];

    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  #handleConnectionUpdate(payload) {
    if (!payload) {
      return;
    }

    if (payload.ok) {
      const patch = {};
      if (typeof payload.connected === 'boolean') {
        patch.connected = payload.connected;
      }
      if (Number.isFinite(payload.latency)) {
        patch.connectionLatency = payload.latency;
      }
      if (payload.quality) {
        patch.connectionQuality = payload.quality;
      }
      if (payload.metrics) {
        patch.systemMetrics = payload.metrics;
      }

      if (typeof patch.connected === 'boolean' && patch.connected !== this.lastConnectionState) {
        const level = patch.connected ? 'info' : 'warn';
        const message = patch.connected ? 'Link to backup server verified' : 'Backup server unreachable';
        this.logs.add(message, { level, phase: 'CONNECT' });
        if (!patch.connected) {
          this.toast.show('Lost connection to backup server', 'warn', 4200);
        }
        this.lastConnectionState = patch.connected;
      }

      if (Object.keys(patch).length) {
        this.state.update(patch);
      }
    } else {
      if (this.lastConnectionState !== false) {
        this.logs.add('Connection monitor: server unreachable', { level: 'warn', phase: 'CONNECT' });
        this.toast.show('Connection monitor lost contact with server', 'warn', 3800);
      }
      this.lastConnectionState = false;
      this.state.update({ connected: false, connectionQuality: 'offline', connectionLatency: null });
    }
  }

  #onSocketConnect() {
    this.logs.add('Realtime channel connected', { level: 'info', phase: 'SOCKET' });
    const { jobId } = this.state.snapshot;
    if (jobId) {
      this.socket.requestStatus(jobId);
    }
  }

  #onSocketDisconnect(reason) {
    this.logs.add(`Realtime channel disconnected${reason ? ` (${reason})` : ''}`, { level: 'warn', phase: 'SOCKET' });
    // Update connection state when socket disconnects
    this.state.update({ connected: false });
  }

  #onSocketError(error) {
    const message = error?.message || 'Realtime channel error';
    this.logs.add(message, { level: 'error', phase: 'SOCKET' });
  }

  #onSocketStatus(payload) {
    if (!payload) {
      return;
    }
    const status = payload.status ?? payload;
    if (status && typeof status === 'object') {
      this.#applyStatus(status);
    }
  }

  #handleSocketProgress(payload) {
    if (!payload) {
      return;
    }
    const activeJobId = this.state.snapshot.jobId;
    if (activeJobId && payload.job_id && payload.job_id !== activeJobId) {
      return;
    }

    const { phase, data } = payload;
    let message = '';
    let level = 'info';
    let progressValue = null;
    let bytesTransferred;
    let totalBytes;

    if (typeof data === 'string') {
      message = data;
    } else if (data && typeof data === 'object') {
      message = data.message || '';
      if (data.success === false) {
        level = 'error';
      }
      progressValue = data.progress?.percentage ?? data.progress ?? null;
      bytesTransferred = data.bytes_transferred ?? data.bytesTransferred;
      totalBytes = data.total_bytes ?? data.totalBytes;
    }

    if (!message) {
      message = phase || 'Progress update';
    }

    this.logs.add(message, { level, phase: phase || 'PROGRESS' });

    const now = Date.now();
    this.state.mutate((draft) => {
      draft.jobRunning = true;
      draft.jobStatus = 'running';
      draft.jobPhase = phase || draft.jobPhase;
      draft.jobMessage = message;
      draft.lastUpdated = now;

      if (Number.isFinite(progressValue)) {
        draft.progress = progressValue;
      }

      if (Number.isFinite(bytesTransferred)) {
        draft.bytesTransferred = bytesTransferred;
        if (this.lastSpeedSample) {
          const deltaBytes = bytesTransferred - this.lastSpeedSample.bytes;
          const deltaTime = (now - this.lastSpeedSample.time) / 1000;
          if (deltaBytes >= 0 && deltaTime > 0) {
            draft.speed = deltaBytes / deltaTime;
          }
        }
        this.lastSpeedSample = { bytes: bytesTransferred, time: now };
      }

      if (Number.isFinite(totalBytes)) {
        draft.totalBytes = totalBytes;
      }

      if (draft.startTimestamp) {
        draft.elapsedSeconds = (now - draft.startTimestamp) / 1000;
      }

      if (draft.totalBytes && draft.bytesTransferred && draft.speed > 0) {
        draft.etaSeconds = Math.max((draft.totalBytes - draft.bytesTransferred) / draft.speed, 0);
      }
    });
  }

  #handleFileReceipt(payload) {
    if (!payload) {
      return;
    }
    const { event_type: type, data } = payload;
    const descriptor = typeof type === 'string' ? type.replace(/_/g, ' ') : 'File event';
    const name = data?.filename || data?.file || '';
    const message = name ? `${descriptor}: ${name}` : descriptor;
    const level = /fail|error/i.test(descriptor) ? 'error' : 'info';
    this.logs.add(message, { level, phase: 'RECEIPT' });
    if (data?.verified || /complete|verified/i.test(descriptor)) {
      this.toast.show('Backup verified on server', 'success', 3600);
    }
  }

  #handleKeydown(event) {
    if (event.defaultPrevented || event.metaKey || event.altKey) {
      return;
    }
    const key = event.key.toLowerCase();
    if (event.ctrlKey) {
      switch (key) {
        case 'k':
          event.preventDefault();
          dom.serverInput.focus();
          break;
        case 'u':
          event.preventDefault();
          dom.usernameInput.focus();
          break;
        case 'f':
          event.preventDefault();
          dom.fileSelectBtn.click();
          break;
        case 't':
          event.preventDefault();
          this.theme.toggle();
          break;
        default:
          break;
      }
    }
  }

  async #refreshStatus(jobId, latencyStart) {
    try {
      const start = latencyStart ?? performance.now();
      const status = await this.api.status(jobId);
      const latency = performance.now() - start;
      this.#applyStatus(status, latency);
    } catch (error) {
      console.warn('Status polling failed', error);
      this.state.update({ connected: false, connectionQuality: 'offline' });
    }
  }

  #applyStatus(status, latency) {
    if (!status) {
      return;
    }

    const connected = Boolean(status.connected);
    const jobRunning = Boolean(status.backing_up);
    const phase = status.phase || status.status || 'Idle';
    const message = status.message || phase;
    const progress = status.progress?.percentage ?? status.progress?.progress ?? null;
    const bytesTransferred = status.progress?.bytes_transferred ?? status.progress?.bytesTransferred ?? null;
    const totalBytes = status.progress?.total_bytes ?? status.progress?.totalBytes ?? null;
    const jobId = status.job_id ?? status.jobId ?? this.state.snapshot.jobId ?? null;
    const paused = Boolean(status.paused ?? status.progress?.paused ?? status.job_paused);

    const now = Date.now();
    const {
      speed: previousSpeed = 0,
      totalBytes: previousTotalBytes,
      bytesTransferred: previousTransferred,
      progress: previousProgress,
      connectionLatency: previousLatency,
      connectionQuality: previousQuality,
      elapsedSeconds: previousElapsedSeconds,
      startTimestamp,
      jobStatus: previousJobStatus,
    } = this.state.snapshot;

    let speed = previousSpeed || 0;
    if (typeof bytesTransferred === 'number') {
      if (this.lastSpeedSample) {
        const deltaBytes = bytesTransferred - this.lastSpeedSample.bytes;
        const deltaTime = (now - this.lastSpeedSample.time) / 1000;
        if (deltaBytes >= 0 && deltaTime > 0) {
          speed = deltaBytes / deltaTime;
        }
      }
      this.lastSpeedSample = { bytes: bytesTransferred, time: now };
    }

    const total = typeof totalBytes === 'number' ? totalBytes : previousTotalBytes;
    const transferred = typeof bytesTransferred === 'number' ? bytesTransferred : previousTransferred;
    const pct = progress ?? previousProgress;

    let etaSeconds = null;
    if (Number.isFinite(total) && Number.isFinite(transferred) && speed > 0 && total > transferred) {
      etaSeconds = (total - transferred) / speed;
    }

    let elapsedSeconds = previousElapsedSeconds;
    if (startTimestamp) {
      elapsedSeconds = (now - startTimestamp) / 1000;
    }

    const connectionQuality = latency
      ? evaluateConnectionQuality({ latencyMs: latency })
      : previousQuality;

    const nextState = {
      jobId,
      connected,
      connectionLatency: latency ?? previousLatency,
      connectionQuality,
      jobRunning,
      jobPhase: phase,
      jobMessage: message,
      jobStatus: this.#deriveJobStatus(status, previousJobStatus),
      progress: Number.isFinite(pct) ? pct : previousProgress,
      bytesTransferred: Number.isFinite(transferred) ? transferred : previousTransferred,
      totalBytes: Number.isFinite(total) ? total : previousTotalBytes,
      speed,
      etaSeconds,
      elapsedSeconds,
      lastUpdated: now,
      paused,
    };

    if (!jobRunning) {
      nextState.jobRunning = false;
      nextState.paused = false;
      if (this.state.snapshot.jobId && (!jobId || jobId === this.state.snapshot.jobId)) {
        this.socket.clearJob();
      }
    }

    if (!jobRunning && nextState.jobStatus === 'completed') {
      this.#stopJobStatusLoop();
      this.toast.show('Backup completed', 'success', 4000);
      this.announcer.announce('Backup completed successfully');
    }

    if (Array.isArray(status.events)) {
      status.events.forEach((event) => {
        if (!event) return;
        const { phase: eventPhase, data } = event;
        let messageText = '';
        let level = 'info';
        if (typeof data === 'string') {
          messageText = data;
        } else if (data && typeof data === 'object') {
          messageText = data.message || JSON.stringify(data);
          if (data.success === false) {
            level = 'error';
          }
        }
        if (!messageText) {
          messageText = eventPhase || 'Event';
        }
        if (eventPhase && /error|fail/i.test(eventPhase)) {
          level = 'error';
        }
        this.logs.add(messageText, { level, phase: eventPhase });
      });
    }

    this.state.update(nextState);
  }

  #deriveJobStatus(status, previousStatus) {
    if (!status) return previousStatus;
    const phase = status.phase || '';
    if (/failed|error/i.test(phase) || status.error) {
      return 'error';
    }
    if (/completed/i.test(phase)) {
      return 'completed';
    }
    if (Boolean(status.backing_up)) {
      return 'running';
    }
    if (/idle|waiting|ready/i.test(phase)) {
      return 'idle';
    }
    if (previousStatus === 'running') {
      return 'idle';
    }
    return previousStatus || 'idle';
  }

  #startJobStatusLoop(jobId) {
    this.#stopJobStatusLoop();
    const poll = () => this.#refreshStatus(jobId);
    this.jobStatusTimer = globalThis.setInterval(poll, STATUS_INTERVAL_MS);
    poll();
  }

  #stopJobStatusLoop() {
    if (this.jobStatusTimer) {
      clearInterval(this.jobStatusTimer);
      this.jobStatusTimer = null;
    }
  }

  #startGeneralStatusLoop() {
    if (this.generalStatusTimer) {
      clearInterval(this.generalStatusTimer);
    }
    const poll = () => {
      const { jobStatus, jobId } = this.state.snapshot;
      if (jobStatus === 'running' && jobId) {
        return;
      }
      this.#refreshStatus();
    };
    this.generalStatusTimer = globalThis.setInterval(poll, GENERAL_STATUS_INTERVAL_MS);
    poll();
  }

  #render(state) {
    // Cache previous render state to avoid unnecessary DOM updates
    if (!this._prevRenderState) {
      this._prevRenderState = {};
    }

    // Use RAF-based batching for smooth rendering
    performanceOptimizer.scheduleUpdate('app-render', () => {
      // Only update changed sections
      if (this.#hasConnectionChanged(state)) {
        this.#renderConnection(state);
      }
      if (this.#hasProgressChanged(state)) {
        this.#renderProgress(state);
      }
      if (this.#hasStatsChanged(state)) {
        this.#renderStats(state);
      }
      if (this.#hasButtonsChanged(state)) {
        this.#renderButtons(state);
      }

      this._prevRenderState = { ...state };
    });
  }

  #hasConnectionChanged(state) {
    const prev = this._prevRenderState;
    return !prev ||
      prev.connecting !== state.connecting ||
      prev.connected !== state.connected ||
      prev.connectionLatency !== state.connectionLatency ||
      prev.connectionQuality !== state.connectionQuality;
  }

  #hasProgressChanged(state) {
    const prev = this._prevRenderState;
    return !prev ||
      prev.jobMessage !== state.jobMessage ||
      prev.jobPhase !== state.jobPhase ||
      prev.progress !== state.progress ||
      prev.etaSeconds !== state.etaSeconds;
  }

  #hasStatsChanged(state) {
    const prev = this._prevRenderState;
    return !prev ||
      prev.bytesTransferred !== state.bytesTransferred ||
      prev.speed !== state.speed ||
      prev.totalBytes !== state.totalBytes ||
      prev.fileSize !== state.fileSize ||
      prev.elapsedSeconds !== state.elapsedSeconds;
  }

  #hasButtonsChanged(state) {
    const prev = this._prevRenderState;
    return !prev ||
      prev.connecting !== state.connecting ||
      prev.connected !== state.connected ||
      prev.jobStatus !== state.jobStatus ||
      prev.jobRunning !== state.jobRunning ||
      prev.paused !== state.paused;
  }

  #renderConnection(state) {
    let badgeClass;
    let statusText;
    if (state.connecting) {
      badgeClass = 'badge connecting';
      statusText = 'Connecting…';
    } else if (state.connected) {
      badgeClass = 'badge connected';
      statusText = 'Connected';
    } else if (!state.connectionAttempted) {
      badgeClass = 'badge muted';
      statusText = 'Ready';
    } else {
      badgeClass = 'badge disconnected';
      statusText = 'Disconnected';
    }

    if (dom.connStatus.className !== badgeClass) {
      dom.connStatus.className = badgeClass;
    }
    if (dom.connStatus.textContent !== statusText) {
      dom.connStatus.textContent = statusText;
    }

    const healthText = `Latency ${formatLatency(state.connectionLatency)}`;
    if (dom.connHealth.textContent !== healthText) {
      dom.connHealth.textContent = healthText;
    }

    const quality = state.connectionQuality || 'offline';
    const qualityClass = `chip quality-${quality}`;
    const qualityLabel = getQualityLabel(quality);

    if (dom.connQuality.className !== qualityClass) {
      dom.connQuality.className = qualityClass;
    }
    if (dom.connQuality.textContent !== qualityLabel) {
      dom.connQuality.textContent = qualityLabel;
    }
  }

  #renderProgress(state) {
    const { jobMessage, jobPhase, progress, connecting, jobStatus, etaSeconds } = state;
    const phaseLabel = jobMessage || jobPhase;

    // Apply phase transition animation when text changes
    if (dom.phaseText.textContent !== phaseLabel) {
      dom.phaseText.classList.add('phase-transitioning');
      dom.phaseText.textContent = phaseLabel;
      setTimeout(() => dom.phaseText.classList.remove('phase-transitioning'), 500);
    }

    // Determine progress ring state based on job state
    const { progressRing } = dom;
    const normalizedProgress = Math.max(0, Math.min(100, progress || 0));
    let stateClass = '';

    if (connecting) {
      stateClass = 'connecting';
    } else if (jobStatus === 'running') {
      if (normalizedProgress >= 100) {
        stateClass = 'completed';
        setTimeout(() => {
          progressRing.classList.remove('completed');
          progressRing.classList.add('active');
        }, 3000); // Reset after 3 seconds
      } else if (normalizedProgress > 80) {
        stateClass = 'completing';
      } else {
        stateClass = 'active';
      }
    } else if (jobStatus === 'completed') {
      stateClass = 'completed';
    } else {
      stateClass = '';
    }

    // Update progress ring state class (SVG elements need classList API)
    progressRing.classList.remove('connecting', 'active', 'completing', 'completed');
    if (stateClass) {
      progressRing.classList.add(stateClass);
    }
    const offset = CIRCUMFERENCE - (normalizedProgress / 100) * CIRCUMFERENCE;
    const offsetStr = offset.toFixed(2);

    // Only update if changed significantly (avoid micro-updates)
    const currentOffset = dom.progressArc.style.strokeDashoffset;
    if (!currentOffset || Math.abs(parseFloat(currentOffset) - offset) > 0.5) {
      dom.progressArc.style.strokeDashoffset = offsetStr;
    }

    // Add updating animation class for percentage pop
    const progressText = formatPercentage(normalizedProgress);
    if (dom.progressPct.textContent !== progressText) {
      dom.progressPct.classList.add('updating');
      dom.progressPct.textContent = progressText;
      setTimeout(() => dom.progressPct.classList.remove('updating'), 400);
    }

    const etaText = etaSeconds ? formatDuration(etaSeconds) : 'ETA —';
    if (dom.etaText.textContent !== etaText) {
      dom.etaText.textContent = etaText;
    }
  }

  #renderStats(state) {
    // Apply transfer-active class during active transfers
    const isTransferring = state.jobStatus === 'running' && !state.paused;
    const statCards = document.querySelectorAll('.stat');
    const speedCard = document.querySelector('.stat:nth-child(2)'); // Speed is typically 2nd

    statCards.forEach(card => {
      if (isTransferring) {
        card.classList.add('transfer-active');
      } else {
        card.classList.remove('transfer-active');
      }
    });

    // Highlight speed card as primary stat during transfer
    if (speedCard) {
      if (isTransferring) {
        speedCard.classList.add('primary-stat');
      } else {
        speedCard.classList.remove('primary-stat');
      }
    }

    // Update bytes with animation
    const bytesText = formatBytes(state.bytesTransferred);
    if (dom.stats.bytes.textContent !== bytesText) {
      dom.stats.bytes.classList.add('updating');
      dom.stats.bytes.textContent = bytesText;
      setTimeout(() => dom.stats.bytes.classList.remove('updating'), 400);
    }

    // Update speed with animation (more frequent updates)
    const speedText = formatSpeed(state.speed);
    if (dom.stats.speed.textContent !== speedText) {
      dom.stats.speed.classList.add('updating');
      dom.stats.speed.textContent = speedText;
      setTimeout(() => dom.stats.speed.classList.remove('updating'), 400);
    }

    // Update size with animation
    const total = state.totalBytes || state.fileSize;
    const sizeText = formatBytes(total);
    if (dom.stats.size.textContent !== sizeText) {
      dom.stats.size.classList.add('updating');
      dom.stats.size.textContent = sizeText;
      setTimeout(() => dom.stats.size.classList.remove('updating'), 400);
    }

    // Update elapsed time with animation
    const elapsedText = state.elapsedSeconds ? formatDuration(state.elapsedSeconds) : '—';
    if (dom.stats.elapsed.textContent !== elapsedText) {
      dom.stats.elapsed.classList.add('updating');
      dom.stats.elapsed.textContent = elapsedText;
      setTimeout(() => dom.stats.elapsed.classList.remove('updating'), 400);
    }

    // Update speed chart if available
    if (window.Enhancements && typeof window.Enhancements.updateSpeedChart === 'function') {
      window.Enhancements.updateSpeedChart(state.speed);
    }
  }

  #renderButtons(state) {
    let btnText, btnDisabled, isLoading = false;

    if (state.connecting) {
      btnText = 'Connecting…';
      btnDisabled = true;
      isLoading = true;
    } else if (!state.connected) {
      btnText = 'Connect';
      btnDisabled = false;
      isLoading = false;
    } else if (state.jobStatus === 'running') {
      btnText = 'Backup in progress';
      btnDisabled = true;
      isLoading = true;
    } else {
      btnText = 'Start Backup';
      btnDisabled = false;
      isLoading = false;
    }

    // Smooth button text transition with loading state
    const btnChanged = dom.primaryActionBtn.textContent !== btnText;
    const loadingChanged = dom.primaryActionBtn.classList.contains('loading') !== isLoading;

    if (btnChanged || loadingChanged) {
      // Fade out
      dom.primaryActionBtn.style.opacity = '0';
      setTimeout(() => {
        dom.primaryActionBtn.textContent = btnText;
        dom.primaryActionBtn.disabled = btnDisabled;

        // Toggle loading class
        if (isLoading) {
          dom.primaryActionBtn.classList.add('loading');
        } else {
          dom.primaryActionBtn.classList.remove('loading');
        }

        // Fade in
        dom.primaryActionBtn.style.opacity = '1';
      }, 150);
    }

    const pauseDisabled = !state.jobRunning || state.paused;
    if (dom.pauseBtn.disabled !== pauseDisabled) {
      dom.pauseBtn.disabled = pauseDisabled;
    }

    const resumeDisabled = !state.jobRunning || !state.paused;
    if (dom.resumeBtn.disabled !== resumeDisabled) {
      dom.resumeBtn.disabled = resumeDisabled;
    }

    const stopDisabled = !state.jobRunning;
    if (dom.stopBtn.disabled !== stopDisabled) {
      dom.stopBtn.disabled = stopDisabled;
    }
  }

  #exportLogs() {
    const content = this.logs.export();
    if (!content) {
      this.toast.show('No logs to export yet', 'info');
      return;
    }
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    link.download = `cyberbackup-log-${timestamp}.txt`;
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 5000);
    this.toast.show('Logs exported', 'success');
  }

  #filterLogsBySearch(query) {
    const entries = dom.logContainer.querySelectorAll('.log-entry');
    let visibleCount = 0;

    for (const entry of entries) {
      const message = entry.querySelector('.log-message');
      const text = message ? message.textContent.toLowerCase() : '';

      if (!query || text.includes(query)) {
        entry.style.display = '';
        visibleCount++;
      } else {
        entry.style.display = 'none';
      }
    }

    // Update visible count
    if (dom.logEntryCount) {
      dom.logEntryCount.textContent = visibleCount.toString();
    }

    // Show/hide empty state
    if (dom.logsEmptyState) {
      dom.logsEmptyState.style.display = visibleCount === 0 ? 'flex' : 'none';
    }
  }

  #generateDemoLogs() {
    const demoMessages = [
      { message: 'Application initialized successfully', level: 'info' },
      { message: 'Connected to backup server at 127.0.0.1:1256', level: 'info' },
      { message: 'RSA key exchange completed', level: 'info' },
      { message: 'AES-256-CBC session key established', level: 'info' },
      { message: 'Starting file transfer: backup_data.zip', level: 'info' },
      { message: 'Chunk 1/10 transferred (10%)', level: 'info' },
      { message: 'Chunk 2/10 transferred (20%)', level: 'info' },
      { message: 'Network latency spike detected: 245ms', level: 'warn' },
      { message: 'Chunk 3/10 transferred (30%)', level: 'info' },
      { message: 'Chunk 4/10 transferred (40%)', level: 'info' },
      { message: 'Connection timeout - retrying...', level: 'warn' },
      { message: 'Reconnected successfully', level: 'info' },
      { message: 'Chunk 5/10 transferred (50%)', level: 'info' },
      { message: 'CRC32 verification failed for chunk 6', level: 'error' },
      { message: 'Retransmitting chunk 6...', level: 'warn' },
      { message: 'Chunk 6/10 transferred (60%)', level: 'info' },
      { message: 'Chunk 7/10 transferred (70%)', level: 'info' },
      { message: 'Chunk 8/10 transferred (80%)', level: 'info' },
      { message: 'Chunk 9/10 transferred (90%)', level: 'info' },
      { message: 'Chunk 10/10 transferred (100%)', level: 'info' },
      { message: 'File integrity verified', level: 'info' },
      { message: 'Backup completed successfully', level: 'info' },
    ];

    // Add messages with staggered timing for animation effect
    let delay = 0;
    for (const { message, level } of demoMessages) {
      setTimeout(() => {
        this.logs.add(message, { level, phase: 'DEMO' });
      }, delay);
      delay += 150; // 150ms between each log
    }

    this.toast.show('Adding demo log entries...', 'info', 2000);
  }
}

globalThis.addEventListener('DOMContentLoaded', () => {
  const app = new App();
  void app.init();
  globalThis.cyberBackupApp = app;
  // Prefill server/username from localStorage if present
  try {
    const savedServer = localStorage.getItem('cyberbackup-server');
    if (savedServer && typeof savedServer === 'string' && savedServer.trim()) {
      dom.serverInput.value = savedServer.trim();
    }
    const savedUser = localStorage.getItem('cyberbackup-username');
    if (savedUser && typeof savedUser === 'string' && savedUser.trim()) {
      dom.usernameInput.value = savedUser.trim();
    }
  } catch {}
  dom.serverInput.addEventListener('input', () => {
    try { localStorage.setItem('cyberbackup-server', dom.serverInput.value.trim()); } catch {}
  });
  dom.usernameInput.addEventListener('input', () => {
    try { localStorage.setItem('cyberbackup-username', dom.usernameInput.value.trim()); } catch {}
  });
});

