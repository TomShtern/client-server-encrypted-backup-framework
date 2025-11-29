/**
 * CyberBackup Client - Core Utilities
 * Bundled: dom, formatters, performance-optimizer, state-store, toasts, accessibility
 */

// --- utils/dom.js ---
/**
 * Gets a DOM element by ID with optional fallback
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
 */
function getOptionalElement(id) {
  return document.getElementById(id);
}

/**
 * Query for a DOM element using CSS selector and throw if not found
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
  safeExecute(operation, context = 'DOM operation') {
    try {
      return operation();
    } catch (error) {
      console.warn(`DOM error in ${context}:`, error);
      return null;
    }
  },

  isVisible(element) {
    return element &&
           element.offsetWidth > 0 &&
           element.offsetHeight > 0 &&
           getComputedStyle(element).display !== 'none';
  },

  addCleanupListener(element, event, handler, options = {}) {
    element.addEventListener(event, handler, options);
    return () => element.removeEventListener(event, handler, options);
  },

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

// --- utils/formatters.js ---
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

// --- utils/performance-optimizer.js ---
class PerformanceOptimizer {
  constructor() {
    this.pendingUpdates = new Map();
    this.rafId = null;
    this.isScheduled = false;
  }

  scheduleUpdate(key, updateFn) {
    this.pendingUpdates.set(key, updateFn);

    if (!this.isScheduled) {
      this.isScheduled = true;
      this.rafId = requestAnimationFrame(() => this.flush());
    }
  }

  flush() {
    if (this.pendingUpdates.size === 0) {
      this.isScheduled = false;
      return;
    }

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

  cancel() {
    if (this.rafId) {
      cancelAnimationFrame(this.rafId);
      this.rafId = null;
    }
    this.pendingUpdates.clear();
    this.isScheduled = false;
  }
}

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

class DOMBatcher {
  constructor() {
    this.reads = [];
    this.writes = [];
    this.scheduled = false;
  }

  read(readFn) {
    return new Promise((resolve) => {
      this.reads.push(() => {
        const result = readFn();
        resolve(result);
      });
      this.schedule();
    });
  }

  write(writeFn) {
    return new Promise((resolve) => {
      this.writes.push(() => {
        writeFn();
        resolve();
      });
      this.schedule();
    });
  }

  schedule() {
    if (!this.scheduled) {
      this.scheduled = true;
      requestAnimationFrame(() => this.flush());
    }
  }

  flush() {
    const reads = this.reads.splice(0);
    reads.forEach(read => read());

    const writes = this.writes.splice(0);
    writes.forEach(write => write());

    this.scheduled = false;
  }
}

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

  animate(timestamp) {
    if (!this.startTime) {
      this.startTime = timestamp;
    }

    const elapsed = timestamp - this.startTime;
    const progress = Math.min(elapsed / this.duration, 1);

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

  setImmediate(value) {
    if (this.rafId) {
      cancelAnimationFrame(this.rafId);
      this.rafId = null;
    }
    this.currentValue = value;
    this.targetValue = value;
    this.element.textContent = this.formatFn(value);
  }

  destroy() {
    if (this.rafId) {
      cancelAnimationFrame(this.rafId);
    }
  }
}

function createIntersectionObserver(callback, options = {}) {
  const defaultOptions = {
    root: null,
    rootMargin: '0px',
    threshold: 0.1,
    ...options
  };

  return new IntersectionObserver(callback, defaultOptions);
}

function measurePerformance(label, fn) {
  const start = performance.now();
  const result = fn();
  const end = performance.now();
  console.log(`[Performance] ${label}: ${(end - start).toFixed(2)}ms`);
  return result;
}

const performanceOptimizer = new PerformanceOptimizer();
const domBatcher = new DOMBatcher();

// --- state/state-store.js ---
function shallowClone(value) {
  if (value === null || typeof value !== 'object') {
    return value;
  }

  if (Array.isArray(value)) {
    return [...value];
  }

  return { ...value };
}

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
    return this.#state;
  }

  update(patch) {
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

    if (!shallowEqual(this.#state, next)) {
      this.#state = next;
      this.#notifyListeners(next);
    }

    this.#pendingUpdate = null;
    this.#updateScheduled = false;
  }

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

    queueMicrotask(() => listener(this.#state));

    return () => this.#listeners.delete(listener);
  }
}

// --- ui/toasts.js ---
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

// --- ui/accessibility.js ---
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
