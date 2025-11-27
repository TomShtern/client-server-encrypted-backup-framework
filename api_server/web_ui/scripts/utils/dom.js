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
export function querySelector(selector, parent = document) {
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
export const dom = {
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
export const domUtils = {
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
