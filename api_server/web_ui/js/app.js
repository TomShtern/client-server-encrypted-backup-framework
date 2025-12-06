/**
 * CyberBackup Client - Main Application
 * Orchestrates Core Logic and UI Components.
 * Depends on: core-utils.js, core.js, ui.js
 */

class App {
  constructor() {
    // Initialize State
    this.state = new StateStore({
      connected: false,
      jobId: null,
      status: 'idle', // idle, uploading, paused, completed, error
      progress: 0,
      speed: 0,
      bytesTransferred: 0,
      totalBytes: 0,
      startTime: null,
      serverAddress: 'localhost:1256',
      username: 'User-' + Math.floor(Math.random() * 10000)
    });

    // Initialize Managers
    // Initialize Managers
    this.api = new ApiClient(API_CONFIG.getApiBaseUrl());
    this.toast = new ToastManager(dom.toastStack);
    this.logs = new LogStore(dom.logContainer); // FIXED: Was dom.logsContainer (undefined in core-utils)
    this.theme = new ThemeManager(); // Uses dom.themeToggle internally

    // Fix: FileManager takes 3 args (input, dropZone, callback)
    this.fileManager = new FileManager(dom.fileInput, dom.fileDropZone, (file) => this.#onFileSelected(file));

    // this.enhancements = new ProfessionalGUIEnhancements(); // REMOVED: Static class, no instance needed

    this.advancedSettings = new AdvancedSettings({
      chunkInput: dom.chunkSizeInput,
      retryInput: dom.retryLimitInput,
      resetButton: dom.resetSettingsBtn,
      toast: this.toast,
      announcer: dom.announcer
    });

    // Initialize Networking
    this.socket = new SocketClient({
      url: API_CONFIG.getApiBaseUrl(),
      onConnect: () => this.#onSocketConnect(),
      onDisconnect: () => this.#onSocketDisconnect(),
      onError: (err) => this.#onSocketError(err),
      onStatus: (status) => this.#onServerStatus(status),
      onProgress: (progress) => this.#onProgress(progress),
      onFileReceipt: (receipt) => this.#onFileReceipt(receipt)
    });

    this.monitor = new ConnectionMonitor({
      api: this.api,
      onResult: (res) => this.#onMonitorResult(res)
    });

    // Bind UI Events
    this.#bindEvents();
  }

  async init() {
    ProfessionalGUIEnhancements.init();

    // Check protocol
    if (API_CONFIG.isFileProtocol()) {
      API_CONFIG.showFileProtocolWarning(this.toast.show.bind(this.toast));
    }

    // Start monitoring
    this.monitor.start();

    // Start socket
    await this.socket.start();

    // Subscribe to state changes
    this.state.subscribe((state) => this.#render(state));

    this.logs.add('Application initialized', { phase: 'INIT' });
  }

  // --- Event Handlers ---

  #bindEvents() {
    // Primary Action Button - State Machine (CONNECT ↔ DISCONNECT)
    dom.primaryActionBtn?.addEventListener('click', () => this.#handlePrimaryAction());

    // Backup Controls
    dom.pauseBtn?.addEventListener('click', () => this.#handlePause());
    dom.resumeBtn?.addEventListener('click', () => this.#handleResume());
    dom.stopBtn?.addEventListener('click', () => this.#handleStop());

    // Settings
    dom.settingsToggle?.addEventListener('click', () => {
      dom.settingsPanel?.classList.toggle('open');
    });
  }

  /**
   * State machine for primary action button.
   * Toggles between connect and disconnect based on current state.
   */
  #handlePrimaryAction() {
    if (this.state.snapshot.connected) {
      this.#handleDisconnect();
    } else {
      this.#handleConnect();
    }
  }

  async #handleConnect() {
    const addressInput = dom.serverInput?.value || dom.serverAddress?.value;
    const parsed = formatters.parseServerAddress(addressInput);

    if (!parsed) {
      this.toast.show('Invalid server address format. Use host:port', 'error');
      this.#updateConnectionStatus('Invalid address format', 'error');
      return;
    }

    try {
      // Update button to connecting state
      this.#setButtonState('connecting');
      this.#updateConnectionStatus('Connecting...', 'pending');

      await this.api.connect({
        host: parsed.host,
        port: parsed.port,
        username: this.state.snapshot.username
      });

      this.state.update({
        connected: true,
        serverAddress: `${parsed.host}:${parsed.port}`
      });

      this.#setButtonState('connected');
      this.#updateConnectionStatus(`Connected to ${parsed.host}:${parsed.port}`, 'success');
      this.toast.show('Connected to backup server', 'success');
      this.logs.add(`Connected to ${parsed.host}:${parsed.port}`, { phase: 'NET' });

    } catch (error) {
      this.#setButtonState('idle');
      this.#updateConnectionStatus('Connection failed', 'error');
      ErrorBoundary.handle(error, 'Connection');
    }
  }

  async #handleDisconnect() {
    try {
      this.#setButtonState('disconnecting');
      this.#updateConnectionStatus('Disconnecting...', 'pending');

      await this.api.disconnect();
      this.state.update({ connected: false, status: 'idle' });

      this.#setButtonState('idle');
      this.#updateConnectionStatus('Disconnected', 'info');
      this.toast.show('Disconnected from server', 'info');
      this.logs.add('Disconnected', { phase: 'NET' });
    } catch (error) {
      this.#setButtonState('connected'); // Restore if disconnect failed
      this.#updateConnectionStatus('Disconnect failed', 'error');
      ErrorBoundary.handle(error, 'Disconnect');
    }
  }

  /**
   * Updates primary action button state with visual feedback.
   * @param {'idle'|'connecting'|'connected'|'disconnecting'} state
   */
  #setButtonState(state) {
    const btn = dom.primaryActionBtn;
    const text = dom.primaryBtnText;
    const spinner = dom.primaryBtnSpinner;
    if (!btn) return;

    switch (state) {
      case 'connecting':
        btn.disabled = true;
        btn.classList.add('loading');
        if (text) text.textContent = 'CONNECTING';
        if (spinner) spinner.classList.add('active');
        break;
      case 'connected':
        btn.disabled = false;
        btn.classList.remove('loading');
        btn.classList.add('connected');
        if (text) text.textContent = 'DISCONNECT';
        if (spinner) spinner.classList.remove('active');
        break;
      case 'disconnecting':
        btn.disabled = true;
        btn.classList.add('loading');
        if (text) text.textContent = 'DISCONNECTING';
        if (spinner) spinner.classList.add('active');
        break;
      case 'idle':
      default:
        btn.disabled = false;
        btn.classList.remove('loading', 'connected');
        if (text) text.textContent = 'CONNECT';
        if (spinner) spinner.classList.remove('active');
    }
  }

  /**
   * Updates connection status message area.
   * @param {string} message
   * @param {'pending'|'success'|'error'|'info'} type
   */
  #updateConnectionStatus(message, type = 'info') {
    const container = dom.connectionStatusMessage;
    const textEl = dom.connectionStatusText;
    const iconEl = dom.connectionStatusIcon;
    if (!container || !textEl) return;

    // Update text
    textEl.textContent = message;

    // Update classes for styling
    container.className = 'connection-status-message ' + type;

    // Update icon
    if (iconEl) {
      const icons = { pending: '⏳', success: '✓', error: '✕', info: 'ℹ' };
      iconEl.textContent = icons[type] || '';
    }
  }

  #onFileSelected(file) {
    if (file) {
      this.logs.add(`File selected: ${file.name} (${formatters.formatBytes(file.size)})`, { phase: 'FILE' });
      // Update file label if it exists
      if (dom.fileLabel) {
        dom.fileLabel.textContent = file.name;
      }
      // Reset progress if new file selected
      if (this.state.snapshot.status === 'completed' || this.state.snapshot.status === 'error') {
        this.state.update({ status: 'idle', progress: 0, bytesTransferred: 0 });
      }
    }
  }

  async #handleStartBackup() {
    const file = this.fileManager.input?.files?.[0];
    if (!file) {
      this.toast.show('Please select a file first', 'warn');
      return;
    }

    if (!this.state.snapshot.connected) {
      this.toast.show('Please connect to a server first', 'warn');
      return;
    }

    try {
      this.state.update({ status: 'uploading', progress: 0, startTime: Date.now() });

      const [host, port] = this.state.snapshot.serverAddress.split(':');
      const options = this.advancedSettings.getOptions();

      const result = await this.api.startBackup({
        file,
        username: this.state.snapshot.username,
        host,
        port,
        options
      });

      this.state.update({ jobId: result.job_id });
      this.socket.watchJob(result.job_id);

      this.logs.add(`Backup started: ${result.job_id}`, { phase: 'BACKUP' });
      this.toast.show('Backup started successfully', 'success');

    } catch (error) {
      this.state.update({ status: 'error' });
      ErrorBoundary.handle(error, 'Start Backup');
    }
  }

  async #handlePause() {
    try {
      await this.api.pause();
      this.state.update({ status: 'paused' });
      this.logs.add('Backup paused', { phase: 'BACKUP' });
    } catch (error) {
      ErrorBoundary.handle(error, 'Pause');
    }
  }

  async #handleResume() {
    try {
      await this.api.resume();
      this.state.update({ status: 'uploading' });
      this.logs.add('Backup resumed', { phase: 'BACKUP' });
    } catch (error) {
      ErrorBoundary.handle(error, 'Resume');
    }
  }

  async #handleStop() {
    try {
      await this.api.stop();
      this.state.update({ status: 'idle', progress: 0, jobId: null });
      this.socket.clearJob();
      this.logs.add('Backup stopped', { phase: 'BACKUP' });
      this.toast.show('Backup stopped', 'info');
    } catch (error) {
      ErrorBoundary.handle(error, 'Stop');
    }
  }

  // --- Socket & Monitor Callbacks ---

  #onSocketConnect() {
    this.logs.add('WebSocket connected', { phase: 'NET' });
  }

  #onSocketDisconnect() {
    this.logs.add('WebSocket disconnected', { phase: 'NET', level: 'warn' });
  }

  #onSocketError(err) {
    console.error('Socket error:', err);
  }

  #onServerStatus(status) {
    // Handle general server status updates if needed
  }

  #onProgress(data) {
    // data: { job_id, percent, bytes_transferred, total_bytes, speed, status }
    if (data.status === 'completed') {
      this.state.update({
        status: 'completed',
        progress: 100,
        bytesTransferred: data.total_bytes
      });
      this.logs.add('Backup completed successfully', { phase: 'BACKUP', level: 'success' });
      this.toast.show('Backup completed!', 'success');
      this.socket.clearJob();
    } else if (data.status === 'failed') {
      this.state.update({ status: 'error' });
      this.logs.add(`Backup failed: ${data.error || 'Unknown error'}`, { phase: 'BACKUP', level: 'error' });
      this.toast.show('Backup failed', 'error');
    } else {
      this.state.update({
        status: 'uploading',
        progress: data.percent,
        bytesTransferred: data.bytes_transferred,
        totalBytes: data.total_bytes,
        speed: data.speed
      });
    }
  }

  #onFileReceipt(receipt) {
    this.logs.add(`File receipt: ${receipt.filename} stored as ${receipt.file_id}`, { phase: 'BACKUP' });
  }

  #onMonitorResult(res) {
    // Update connection quality indicator in UI
    if (dom.statusIndicator) {
      dom.statusIndicator.className = `status-indicator ${res.quality}`;
    }
    if (dom.statusText) {
      dom.statusText.textContent = res.connected ? 'Connected' : 'Disconnected';
    }
  }

  // --- Rendering ---

  #render(state) {
    // Visibility
    if (dom.connectionPanel) dom.connectionPanel.style.display = state.connected ? 'none' : 'block';
    if (dom.backupPanel) dom.backupPanel.style.display = state.connected ? 'block' : 'none';

    // Progress
    if (state.status === 'uploading' || state.status === 'paused') {
      if (dom.progressSection) dom.progressSection.style.display = 'block';
      if (dom.progressBar) {
        dom.progressBar.style.width = `${state.progress}%`;
        dom.progressBar.className = state.status === 'paused' ? 'progress-bar paused' : 'progress-bar';
      }
      if (dom.progressText) dom.progressText.textContent = formatters.formatPercentage(state.progress);
      if (dom.bytesTransferred) {
        // Use stats elements if available for detailed breakdown
        if (dom.stats && dom.stats.bytes) {
          dom.bytesTransferred.textContent = `${formatters.formatBytes(state.bytesTransferred)} / ${formatters.formatBytes(state.totalBytes)}`;
          dom.stats.bytes.textContent = formatters.formatBytes(state.bytesTransferred);
          dom.stats.size.textContent = formatters.formatBytes(state.totalBytes);
          dom.stats.speed.textContent = formatters.formatSpeed(state.speed);
        } else {
          dom.bytesTransferred.textContent = `${formatters.formatBytes(state.bytesTransferred)} / ${formatters.formatBytes(state.totalBytes)}`;
        }
      }
      if (dom.transferSpeed) dom.transferSpeed.textContent = formatters.formatSpeed(state.speed);

      // Controls
      if (dom.pauseBtn) dom.pauseBtn.style.display = state.status === 'uploading' ? 'inline-block' : 'none';
      if (dom.resumeBtn) dom.resumeBtn.style.display = state.status === 'paused' ? 'inline-block' : 'none';
      if (dom.stopBtn) dom.stopBtn.style.display = 'inline-block';
      if (dom.startBackupBtn) dom.startBackupBtn.disabled = true;

    } else if (state.status === 'completed') {
      if (dom.progressBar) {
        dom.progressBar.style.width = '100%';
        dom.progressBar.className = 'progress-bar success';
      }
      if (dom.progressText) dom.progressText.textContent = '100%';
      if (dom.startBackupBtn) dom.startBackupBtn.disabled = false;
      if (dom.stopBtn) dom.stopBtn.style.display = 'none';
      if (dom.pauseBtn) dom.pauseBtn.style.display = 'none';
      if (dom.resumeBtn) dom.resumeBtn.style.display = 'none';

    } else {
      // Idle or Error
      if (dom.progressSection && state.status === 'idle') dom.progressSection.style.display = 'none';
      if (dom.startBackupBtn) dom.startBackupBtn.disabled = false;
      if (dom.stopBtn) dom.stopBtn.style.display = 'none';
      if (dom.pauseBtn) dom.pauseBtn.style.display = 'none';
      if (dom.resumeBtn) dom.resumeBtn.style.display = 'none';
    }
  }
}

// --- Bootstrap ---

document.addEventListener('DOMContentLoaded', () => {
  // Ensure DOM is fully ready before initializing app
  setTimeout(() => {
    globalThis.app = new App();
    globalThis.app.init().catch(err => {
      console.error('Fatal initialization error:', err);
      document.body.innerHTML = '<div style="color:red; padding:20px;"><h1>Fatal Error</h1><p>Application failed to initialize. See console for details.</p></div>';
    });
  }, 0);
});
