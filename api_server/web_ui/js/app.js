/**
 * CyberBackup - Main Application Logic
 * Consolidated from multiple modules
 */

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
const STATUS_INTERVAL_MS = 5000;  // Reduced from 2500ms for performance
const GENERAL_STATUS_INTERVAL_MS = 15000;  // Reduced from 12000ms for performance
const RENDER_DEBOUNCE_MS = 50;  // Minimum time between render calls

/**
 * Add an animation class and remove it when the animation ends.
 * Uses animationend event instead of setTimeout for better performance.
 * @param {Element} element - The DOM element
 * @param {string} className - The class to add/remove
 */
function animateOnce(element, className) {
  if (!element) return;
  // Optimization: If already animating, let it finish. Don't stack listeners.
  if (element.classList.contains(className)) return;

  element.classList.add(className);
  element.addEventListener('animationend', function handler() {
    element.classList.remove(className);
  }, { once: true });
}

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
    // Get the correct API base URL for cross-origin requests
    const apiBaseUrl = API_CONFIG.getApiBaseUrl();
    const isFileProtocol = API_CONFIG.isFileProtocol();

    if (apiBaseUrl) {
      console.log('[App] API Base URL:', apiBaseUrl);
    } else if (isFileProtocol) {
      console.log('[App] Running from file:// protocol - API features will be limited');
    } else {
      console.log('[App] API Base URL: (same origin)');
    }

    // Initialize with error boundaries
    try {
      this.api = new ApiClient(apiBaseUrl);
      this.toast = new ToastManager(dom.toastStack);
      this.announcer = new ScreenReaderAnnouncer(dom.srLive);
      this.state = new StateStore(INITIAL_STATE);
      this.logs = new LogStore(dom.logContainer);
      this.theme = new ThemeManager(dom.themeToggle);

      // Show warning if opened via file:// protocol (after toast is initialized)
      if (isFileProtocol) {
        // Delay to ensure UI is ready
        setTimeout(() => API_CONFIG.showFileProtocolWarning((msg, type, duration) => this.toast.show(msg, type, duration)), 500);
      }
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
      // New File Card Elements
      fileIcon: dom.fileIcon,
      fileNameDisplay: dom.fileNameDisplay,
      fileMetadata: dom.fileMetadata,
      fileTypeBadge: dom.fileTypeBadge,
      fileModified: dom.fileModified,
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

    // Use the same API base URL for WebSocket connections
    const socketUrl = apiBaseUrl || globalThis.location?.origin || '';
    this.socket = new SocketClient({
      url: socketUrl,
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
    this._lastRenderTime = 0;  // For render debouncing
    this._isTabVisible = true;  // Track tab visibility

    // Cache stat card DOM queries (avoid querySelectorAll in render loop)
    this._cachedStatCards = document.querySelectorAll('.stat');
    this._cachedSpeedCard = document.querySelector('.stat:nth-child(2)');

    // Speed update throttling
    this._lastSpeedUpdate = 0;
    this._speedUpdateThrottle = 100; // Max 10 updates/sec

    // Set initial idle state (no transfer running)
    document.documentElement.classList.add('app-idle');

    try {
      this.#bindEvents();
      this.#setupVisibilityHandler();
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

  // Page Visibility API: pause polling when tab is hidden
  #setupVisibilityHandler() {
    document.addEventListener('visibilitychange', () => {
      const isHidden = document.hidden;
      this._isTabVisible = !isHidden;

      if (isHidden) {
        // Pause all polling when tab is hidden
        document.documentElement.classList.add('tab-hidden');
        this.connectionMonitor.stop();
        this.#stopJobStatusLoop();
        if (this.generalStatusTimer) {
          clearInterval(this.generalStatusTimer);
          this.generalStatusTimer = null;
        }
        console.log('[Performance] Tab hidden - polling paused');
      } else {
        // Resume polling when tab becomes visible
        document.documentElement.classList.remove('tab-hidden');
        this.connectionMonitor.start();
        this.#startGeneralStatusLoop();

        // Resume job polling if there's an active job
        const { jobId, jobRunning } = this.state.snapshot;
        if (jobId && jobRunning) {
          this.#startJobStatusLoop(jobId);
        }
        console.log('[Performance] Tab visible - polling resumed');
      }
    });
  }

  // Update idle state based on job status
  #updateIdleState(isRunning) {
    if (isRunning) {
      document.documentElement.classList.remove('app-idle');
    } else {
      document.documentElement.classList.add('app-idle');
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

    // Segmented filter control with sliding indicator - Event Delegation
    const filterContainer = document.querySelector('.logs-filter-segment');
    if (filterContainer) {
      filterContainer.addEventListener('click', (e) => {
        const button = e.target.closest('.segment-btn');
        if (!button) return;

        const buttons = filterContainer.querySelectorAll('.segment-btn');
        buttons.forEach(btn => {
          const isActive = btn === button;
          btn.classList.toggle('active', isActive);
          btn.setAttribute('aria-pressed', isActive ? 'true' : 'false');
        });

        // Animate segment indicator
        if (dom.segmentIndicator) {
          const index = Array.from(buttons).indexOf(button);
          if (index !== -1) {
            const segmentWidth = 100 / buttons.length;
            dom.segmentIndicator.style.width = `calc(${segmentWidth}% - 3px)`;
            dom.segmentIndicator.style.left = `calc(${index * segmentWidth}% + 4px)`;
          }
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
      icon.textContent = '✗';
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

    // Use RAF batching for smooth progress updates
    performanceOptimizer.scheduleUpdate('socket-progress', () => {
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

      if (window.Enhancements?.showNotification) {
        window.Enhancements.showNotification('Backup Verified', {
          body: `File ${name} verified on server.`
        });
      }
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

      if (window.Enhancements?.showNotification) {
        window.Enhancements.showNotification('Backup Completed', {
          body: `Backup of ${this.state.snapshot.fileName || 'file'} finished successfully.`
        });
      }
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
    // Debounce renders to avoid excessive DOM updates
    const now = performance.now();
    if (now - this._lastRenderTime < RENDER_DEBOUNCE_MS) {
      // Skip this render, but schedule one for later
      if (!this._pendingRender) {
        this._pendingRender = setTimeout(() => {
          this._pendingRender = null;
          this.#render(this.state.snapshot);
        }, RENDER_DEBOUNCE_MS);
      }
      return;
    }
    this._lastRenderTime = now;

    // Cache previous render state to avoid unnecessary DOM updates
    if (!this._prevRenderState) {
      this._prevRenderState = {};
    }

    // Update idle state based on job running status
    this.#updateIdleState(state.jobRunning);

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
      animateOnce(dom.phaseText, 'phase-transitioning');
      dom.phaseText.textContent = phaseLabel;
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
      animateOnce(dom.progressPct, 'updating');
      dom.progressPct.textContent = progressText;
    }

    const etaText = etaSeconds ? formatDuration(etaSeconds) : '–';
    if (dom.etaText.textContent !== etaText) {
      dom.etaText.textContent = etaText;
    }
  }

  #renderStats(state) {
    // Apply transfer-active class during active transfers
    const isTransferring = state.jobStatus === 'running' && !state.paused;

    // Use cached DOM queries instead of querySelectorAll on every render
    this._cachedStatCards.forEach(card => {
      if (isTransferring) {
        card.classList.add('transfer-active');
      } else {
        card.classList.remove('transfer-active');
      }
    });

    // Highlight speed card as primary stat during transfer
    if (this._cachedSpeedCard) {
      if (isTransferring) {
        this._cachedSpeedCard.classList.add('primary-stat');
      } else {
        this._cachedSpeedCard.classList.remove('primary-stat');
      }
    }

    // Update bytes with animation
    const bytesText = formatBytes(state.bytesTransferred);
    if (dom.stats.bytes.textContent !== bytesText) {
      animateOnce(dom.stats.bytes, 'updating');
      dom.stats.bytes.textContent = bytesText;
    }

    // Throttle speed updates to max 10/sec (reduce animation overhead)
    const now = performance.now();
    const speedText = formatSpeed(state.speed);
    if (now - this._lastSpeedUpdate >= this._speedUpdateThrottle) {
      if (dom.stats.speed.textContent !== speedText) {
        animateOnce(dom.stats.speed, 'updating');
        dom.stats.speed.textContent = speedText;
        this._lastSpeedUpdate = now;
      }
    }

    // Update size with animation
    const total = state.totalBytes || state.fileSize;
    const sizeText = formatBytes(total);
    if (dom.stats.size.textContent !== sizeText) {
      animateOnce(dom.stats.size, 'updating');
      dom.stats.size.textContent = sizeText;
    }

    // Update elapsed time with animation
    const elapsedText = state.elapsedSeconds ? formatDuration(state.elapsedSeconds) : '–';
    if (dom.stats.elapsed.textContent !== elapsedText) {
      animateOnce(dom.stats.elapsed, 'updating');
      dom.stats.elapsed.textContent = elapsedText;
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
  } catch { }
  dom.serverInput.addEventListener('input', () => {
    try { localStorage.setItem('cyberbackup-server', dom.serverInput.value.trim()); } catch { }
  });
  dom.usernameInput.addEventListener('input', () => {
    try { localStorage.setItem('cyberbackup-username', dom.usernameInput.value.trim()); } catch { }
  });
});
