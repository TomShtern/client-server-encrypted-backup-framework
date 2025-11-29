/**
 * Professional Desktop Web GUI Enhancements
 * JavaScript enhancements for improved user experience
 */
console.log('Enhancements module loaded');

class ProfessionalGUIEnhancements {
    constructor() {
        this.init();
    }

    init() {
        this.setupSidebarEnhancements();
        // Visual effects only
        ProfessionalGUIEnhancements.initDataParticles();
        ProfessionalGUIEnhancements.initRippleEffects();
        ProfessionalGUIEnhancements.initFloatingLabels();
        ProfessionalGUIEnhancements.addEnhancementStyles();

        // Setup advanced settings UI
        this.setupAdvancedSettingsAccordion();
        this.setupAdvancedSettingsTabs();

        // Setup non-conflicting enhancements
        ProfessionalGUIEnhancements.setupConnectionDropdown();
        ProfessionalGUIEnhancements.setupLogSearch();
        ProfessionalGUIEnhancements.setupSpeedChart();

        // New Enhancements
        this.setupDragAndDrop();
        this.setupShortcuts();
        this.setupLogInteractions();
        this.setupBrowserNotifications();
    }

    // Setup Browser Notifications
    setupBrowserNotifications() {
        if (!('Notification' in window)) return;

        // Request permission on user interaction (e.g., first click on page)
        const requestPermission = () => {
            if (Notification.permission === 'default') {
                Notification.requestPermission();
            }
            document.removeEventListener('click', requestPermission);
        };
        document.addEventListener('click', requestPermission);
    }

    // Static method to show notification
    static showNotification(title, options) {
        if (!('Notification' in window) || Notification.permission !== 'granted') return;

        try {
            new Notification(title, {
                icon: 'favicon.svg',
                ...options
            });
        } catch (e) {
            console.warn('Notification failed', e);
        }
    }

    // Static method: Initialize data particles
    static initDataParticles() {
        const container = document.getElementById('dataParticles');
        if (!container) return;

        // Clear existing
        container.innerHTML = '';

        // Create particles
        const particleCount = window.innerWidth < 768 ? 20 : 50;

        for (let i = 0; i < particleCount; i++) {
            const particle = document.createElement('div');
            particle.className = 'particle';

            // Random positioning and sizing
            const size = Math.random() * 3 + 1;
            particle.style.width = `${size}px`;
            particle.style.height = `${size}px`;
            particle.style.left = `${Math.random() * 100}%`;
            particle.style.top = `${Math.random() * 100}%`;

            // Random animation properties
            const duration = Math.random() * 20 + 10;
            const delay = Math.random() * 5;
            particle.style.animationDuration = `${duration}s`;
            particle.style.animationDelay = `-${delay}s`;
            particle.style.opacity = Math.random() * 0.5 + 0.1;

            container.appendChild(particle);
        }
    }

    // Static method: Initialize ripple effects
    static initRippleEffects() {
        document.addEventListener('click', (e) => {
            const target = e.target.closest('.ripple');
            if (!target) return;

            const rect = target.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;

            const circle = document.createElement('span');
            const diameter = Math.max(rect.width, rect.height);
            const radius = diameter / 2;

            circle.style.width = circle.style.height = `${diameter}px`;
            circle.style.left = `${x - radius}px`;
            circle.style.top = `${y - radius}px`;
            circle.classList.add('ripple-effect');

            const ripple = target.getElementsByClassName('ripple-effect')[0];
            if (ripple) {
                ripple.remove();
            }

            target.appendChild(circle);

            // Clean up
            setTimeout(() => {
                circle.remove();
            }, 600);
        });
    }

    // Static method: Initialize floating labels
    static initFloatingLabels() {
        const inputs = document.querySelectorAll('.floating-label .interactive');

        inputs.forEach(input => {
            // Initial check
            if (input.value) {
                input.classList.add('has-value');
            }

            input.addEventListener('input', () => {
                if (input.value) {
                    input.classList.add('has-value');
                } else {
                    input.classList.remove('has-value');
                }
            });

            input.addEventListener('focus', () => {
                input.parentElement.classList.add('focused');
            });

            input.addEventListener('blur', () => {
                input.parentElement.classList.remove('focused');
            });
        });
    }

    // Instance method: Setup sidebar-specific interactions
    setupSidebarEnhancements() {
        try {
            const sidebar = document.querySelector('aside.stack');
            if (!sidebar) return;

            // Allow collapsing/expanding the sidebar by clicking the header area
            const title = sidebar.querySelector('.phase');
            if (title) {
                title.style.cursor = 'pointer';
                title.addEventListener('click', () => {
                    sidebar.classList.toggle('collapsed');
                });
            }

            // Add hover depth class using CSS already present
            sidebar.addEventListener('mouseenter', () => sidebar.classList.add('hovered'));
            sidebar.addEventListener('mouseleave', () => sidebar.classList.remove('hovered'));
        } catch (e) {
            console.warn('setupSidebarEnhancements failed', e);
        }
    }

    // Removed conflicting methods: setupProgressEnhancements, setupButtonHierarchy, setupBrowserBehavior, setupAccessibility, setupProfessionalInteractions


    // Setup Advanced Settings Accordion
    setupAdvancedSettingsAccordion() {
        const toggleBtn = document.querySelector('.advanced-toggle');
        const content = document.getElementById('advancedContent');

        if (toggleBtn && content) {
            toggleBtn.addEventListener('click', () => {
                const isExpanded = toggleBtn.getAttribute('aria-expanded') === 'true';
                toggleBtn.setAttribute('aria-expanded', !isExpanded);
                content.hidden = isExpanded;
            });
        }
    }

    // Setup Advanced Settings Tabs
    setupAdvancedSettingsTabs() {
        const tabButtons = document.querySelectorAll('.settings-tabs .tab-btn');
        const tabPanels = document.querySelectorAll('.tab-panels .tab-panel');

        if (tabButtons.length && tabPanels.length) {
            tabButtons.forEach(btn => {
                btn.addEventListener('click', () => {
                    const tabId = btn.getAttribute('data-tab');
                    const targetPanel = document.getElementById(`tab-${tabId}`);

                    // Update buttons
                    tabButtons.forEach(b => {
                        b.classList.remove('active');
                        b.setAttribute('aria-selected', 'false');
                    });
                    btn.classList.add('active');
                    btn.setAttribute('aria-selected', 'true');

                    // Update panels
                    tabPanels.forEach(panel => {
                        panel.classList.remove('active');
                        panel.hidden = true;
                    });
                    if (targetPanel) {
                        targetPanel.classList.add('active');
                        targetPanel.hidden = false;
                    }
                });
            });
        }
    }

    // File type icon mapping
    static FILE_TYPE_ICONS = {
  // Documents
  pdf: { icon: '📄', badge: 'pdf', class: 'pdf' },
  doc: { icon: '📝', badge: 'doc', class: 'doc' },
  docx: { icon: '📝', badge: 'doc', class: 'doc' },
  txt: { icon: '📄', badge: 'txt', class: 'default' },
  rtf: { icon: '📝', badge: 'rtf', class: 'doc' },

  // Spreadsheets
  xls: { icon: '📊', badge: 'xls', class: 'doc' },
  xlsx: { icon: '📊', badge: 'xlsx', class: 'doc' },
  csv: { icon: '📊', badge: 'csv', class: 'doc' },

  // Images
  jpg: { icon: '🖼️', badge: 'jpg', class: 'img' },
  jpeg: { icon: '🖼️', badge: 'jpeg', class: 'img' },
  png: { icon: '🖼️', badge: 'png', class: 'img' },
  gif: { icon: '🖼️', badge: 'gif', class: 'img' },
  svg: { icon: '🖼️', badge: 'svg', class: 'img' },
  webp: { icon: '🖼️', badge: 'webp', class: 'img' },

  // Videos
  mp4: { icon: '🎥', badge: 'mp4', class: 'video' },
  avi: { icon: '🎥', badge: 'avi', class: 'video' },
  mkv: { icon: '🎥', badge: 'mkv', class: 'video' },
  mov: { icon: '🎥', badge: 'mov', class: 'video' },

  // Audio
  mp3: { icon: '🎵', badge: 'mp3', class: 'audio' },
  wav: { icon: '🎵', badge: 'wav', class: 'audio' },
  flac: { icon: '🎵', badge: 'flac', class: 'audio' },

  // Archives
  zip: { icon: '📦', badge: 'zip', class: 'archive' },
  rar: { icon: '📦', badge: 'rar', class: 'archive' },
  '7z': { icon: '📦', badge: '7z', class: 'archive' },
  tar: { icon: '📦', badge: 'tar', class: 'archive' },
  gz: { icon: '📦', badge: 'gz', class: 'archive' },

  // Code
  js: { icon: '💻', badge: 'js', class: 'code' },
  py: { icon: '💻', badge: 'py', class: 'code' },
  html: { icon: '💻', badge: 'html', class: 'code' },
  css: { icon: '💻', badge: 'css', class: 'code' },
  json: { icon: '💻', badge: 'json', class: 'code' },
  xml: { icon: '💻', badge: 'xml', class: 'code' },

  // Default
  default: { icon: '📄', badge: 'file', class: 'default' }
};

    // Get file type info
    static getFileTypeInfo(filename) {
        const ext = filename.split('.').pop().toLowerCase();
        return ProfessionalGUIEnhancements.FILE_TYPE_ICONS[ext] || ProfessionalGUIEnhancements.FILE_TYPE_ICONS.default;
    }

    // Format file modified date
    static formatModifiedDate(date) {
        const now = new Date();
        const diff = now - date;
        const days = Math.floor(diff / (1000 * 60 * 60 * 24));

        if (days === 0) {
            return 'Today';
        } else if (days === 1) {
            return 'Yesterday';
        } else if (days < 7) {
            return `${days} days ago`;
        } else {
            return date.toLocaleDateString();
        }
    }

    // Update file card with rich preview (Icons and Badges only - text handled by app.js)
    static updateFileCardPreview(file) {
        const fileIcon = document.getElementById('fileIcon');
        const fileMetadata = document.getElementById('fileMetadata');
        const fileTypeBadge = document.getElementById('fileTypeBadge');
        const fileModified = document.getElementById('fileModified');

        // New elements for toggling
        const defaultContent = document.getElementById('defaultDropContent');
        const previewCard = document.getElementById('filePreviewCard');
        const fileNameDisplay = document.getElementById('fileNameDisplay');

        if (!file) {
            // Reset/Hide metadata if no file
            if (defaultContent) defaultContent.style.display = 'flex';
            if (previewCard) previewCard.style.display = 'none';

            if (fileIcon) fileIcon.textContent = '';
            if (fileMetadata) fileMetadata.style.display = 'none';
            if (fileTypeBadge) fileTypeBadge.className = 'file-badge';
            if (fileModified) fileModified.textContent = '';
            return;
        }

        // Show preview, hide default
        if (defaultContent) defaultContent.style.display = 'none';
        if (previewCard) previewCard.style.display = 'grid';

        const typeInfo = ProfessionalGUIEnhancements.getFileTypeInfo(file.name);
        const modifiedDate = ProfessionalGUIEnhancements.formatModifiedDate(new Date(file.lastModified));

        // Update icon
        if (fileIcon) {
            fileIcon.textContent = typeInfo.icon;
        }

        // Update name
        if (fileNameDisplay) {
            fileNameDisplay.textContent = file.name;
        }

        // Update metadata visibility
        if (fileMetadata) {
            fileMetadata.style.display = 'flex';
        }

        if (fileTypeBadge) {
            fileTypeBadge.textContent = typeInfo.badge.toUpperCase();
            fileTypeBadge.className = `file-badge ${typeInfo.class}`;
        }

        if (fileModified) {
            fileModified.textContent = `Modified: ${modifiedDate}`;
        }
    }

    // Helper function for file size formatting
    static formatBytes(bytes, decimals = 2) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
    }

    // Removed conflicting methods: ProgressRingStates, updateProgressRingState, validateServerInput, validateUsername, updateValidationIcon, setupValidation, updatePrimaryButtonState


    // Connection dropdown toggle
    static setupConnectionDropdown() {
        const statusBadge = document.getElementById('connStatus');
        const dropdown = document.getElementById('connectionDetails');

        if (!statusBadge || !dropdown) return;

        statusBadge.addEventListener('click', (e) => {
            e.stopPropagation();
            dropdown.classList.toggle('show');
        });

        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!dropdown.contains(e.target) && !statusBadge.contains(e.target)) {
                dropdown.classList.remove('show');
            }
        });
    }

    // Log search functionality
    static setupLogSearch() {
        const searchInput = document.getElementById('logSearchInput');
        const logContainer = document.getElementById('logContainer');

        if (!searchInput || !logContainer) return;

        let searchTimeout;

        searchInput.addEventListener('input', () => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                const query = searchInput.value.toLowerCase().trim();
                ProfessionalGUIEnhancements.filterLogs(query);
            }, 300); // Debounce 300ms
        });
    }

    static filterLogs(query) {
        const logContainer = document.getElementById('logContainer');
        if (!logContainer) return;

        const logEntries = logContainer.querySelectorAll('[data-log-entry]');

        if (!query) {
            logEntries.forEach(entry => {
                entry.style.display = '';
            });
            return;
        }

        logEntries.forEach(entry => {
            const text = entry.textContent.toLowerCase();
            if (text.includes(query)) {
                entry.style.display = '';
            } else {
                entry.style.display = 'none';
            }
        });
    }

    // Speed chart implementation (inner class)
    static SpeedChart = class {
        constructor(canvasId) {
            this.canvas = document.getElementById(canvasId);
            if (!this.canvas) return;

            this.ctx = this.canvas.getContext('2d');
            this.dataPoints = [];
            this.maxDataPoints = 30; // 30 seconds of data
            this.maxSpeed = 0;

            // Setup canvas size
            this.resizeCanvas();
            window.addEventListener('resize', () => this.resizeCanvas());
        }

        resizeCanvas() {
            if (!this.canvas) return;
            const rect = this.canvas.getBoundingClientRect();
            this.canvas.width = rect.width * window.devicePixelRatio;
            this.canvas.height = rect.height * window.devicePixelRatio;
            this.ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
            this.draw();
        }

        addDataPoint(speed) {
            this.dataPoints.push(speed);

            // Keep only last N points
            if (this.dataPoints.length > this.maxDataPoints) {
                this.dataPoints.shift();
            }

            // Update max for scaling
            this.maxSpeed = Math.max(...this.dataPoints, this.maxSpeed * 0.95);

            this.draw();
        }

        draw() {
            if (!this.ctx || this.dataPoints.length === 0) return;

            const width = this.canvas.width / window.devicePixelRatio;
            const height = this.canvas.height / window.devicePixelRatio;
            const padding = 10;
            const chartWidth = width - padding * 2;
            const chartHeight = height - padding * 2;

            // Clear canvas
            this.ctx.clearRect(0, 0, width, height);

            // Draw grid lines
            this.ctx.strokeStyle = '#30363d';
            this.ctx.lineWidth = 1;
            for (let i = 0; i <= 4; i++) {
                const y = padding + (chartHeight / 4) * i;
                this.ctx.beginPath();
                this.ctx.moveTo(padding, y);
                this.ctx.lineTo(width - padding, y);
                this.ctx.stroke();
            }

            // Draw line chart
            this.ctx.strokeStyle = '#58a6ff';
            this.ctx.lineWidth = 2;
            this.ctx.beginPath();

            this.dataPoints.forEach((speed, index) => {
                const x = padding + (chartWidth / (this.maxDataPoints - 1)) * index;
                const y = padding + chartHeight - (speed / this.maxSpeed) * chartHeight;

                if (index === 0) {
                    this.ctx.moveTo(x, y);
                } else {
                    this.ctx.lineTo(x, y);
                }
            });

            this.ctx.stroke();

            // Draw fill gradient
            this.ctx.lineTo(width - padding, height - padding);
            this.ctx.lineTo(padding, height - padding);
            this.ctx.closePath();

            const gradient = this.ctx.createLinearGradient(0, padding, 0, height - padding);
            gradient.addColorStop(0, 'rgba(88, 166, 255, 0.2)');
            gradient.addColorStop(1, 'rgba(88, 166, 255, 0.0)');
            this.ctx.fillStyle = gradient;
            this.ctx.fill();
        }

        clear() {
            this.dataPoints = [];
            this.maxSpeed = 0;
            if (this.ctx) {
                const width = this.canvas.width / window.devicePixelRatio;
                const height = this.canvas.height / window.devicePixelRatio;
                this.ctx.clearRect(0, 0, width, height);
            }
        }
    }

    // Initialize speed chart
    static setupSpeedChart() {
        ProfessionalGUIEnhancements.chartInstance = new ProfessionalGUIEnhancements.SpeedChart('speedChart');

        const toggleBtn = document.getElementById('toggleSpeedChart');
        const container = document.getElementById('speedChartContainer');

        if (toggleBtn && container) {
            toggleBtn.addEventListener('click', () => {
                const isVisible = container.classList.contains('show');
                if (isVisible) {
                    container.classList.remove('show');
                    toggleBtn.textContent = 'Show Chart';
                } else {
                    container.classList.add('show');
                    toggleBtn.textContent = 'Hide Chart';
                    if (ProfessionalGUIEnhancements.chartInstance) ProfessionalGUIEnhancements.chartInstance.draw();
                }
            });
        }
    }

    // Removed conflicting methods: setupThemeToggle

    // Setup Drag & Drop Overlay
    setupDragAndDrop() {
        const overlay = document.getElementById('dragOverlay');
        const dropZone = document.getElementById('fileDropZone');
        const fileInput = document.getElementById('fileInput');

        if (!overlay || !dropZone || !fileInput) return;

        let dragCounter = 0;

        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            document.body.addEventListener(eventName, preventDefaults, false);
        });

        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }

        document.body.addEventListener('dragenter', (e) => {
            dragCounter++;
            overlay.classList.add('active');
        });

        document.body.addEventListener('dragleave', (e) => {
            dragCounter--;
            if (dragCounter === 0) {
                overlay.classList.remove('active');
            }
        });

        document.body.addEventListener('drop', (e) => {
            dragCounter = 0;
            overlay.classList.remove('active');

            const { files } = e.dataTransfer;

            if (files.length > 0) {
                fileInput.files = files;
                // Trigger change event manually
                const event = new Event('change', { bubbles: true });
                fileInput.dispatchEvent(event);
            }
        });
    }

    // Setup Keyboard Shortcuts
    setupShortcuts() {
        const modal = document.getElementById('shortcutModal');
        const btn = document.getElementById('shortcutBtn');
        const closeBtn = document.getElementById('closeShortcutBtn');

        if (!modal || !btn || !closeBtn) return;

        btn.addEventListener('click', () => modal.showModal());
        closeBtn.addEventListener('click', () => modal.close());

        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.close();
        });

        document.addEventListener('keydown', (e) => {
            if (e.key === '?' && e.shiftKey && document.activeElement.tagName !== 'INPUT') {
                e.preventDefault();
                modal.showModal();
            }
        });
    }

    // Setup Log Interactions (Copy/Pin)
    setupLogInteractions() {
        const logContainer = document.getElementById('logContainer');
        if (!logContainer) return;

        logContainer.addEventListener('click', (e) => {
            const btn = e.target.closest('.log-action-mini');
            if (!btn) return;

            const entry = btn.closest('.log-entry');
            if (!entry) return;

            const { action } = btn.dataset;
            const message = entry.querySelector('.log-message').textContent;

            if (action === 'copy') {
                navigator.clipboard.writeText(message).then(() => {
                    // Visual feedback
                    const originalIcon = btn.innerHTML;
                    btn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg>';
                    btn.style.color = 'var(--success)';
                    setTimeout(() => {
                        btn.innerHTML = originalIcon;
                        btn.style.color = '';
                    }, 1500);
                });
            } else if (action === 'pin') {
                entry.classList.toggle('pinned');
                if (entry.classList.contains('pinned')) {
                    entry.style.background = 'rgba(88, 166, 255, 0.1)';
                    entry.style.borderLeftColor = 'var(--accent)';
                    btn.style.color = 'var(--accent)';
                } else {
                    entry.style.background = '';
                    entry.style.borderLeftColor = '';
                    btn.style.color = '';
                }
            }
        });
    }

    // Static method: Initialize data particles
    static initDataParticles() {
        const container = document.getElementById('dataParticles');
        if (!container) return;

        // Clear existing
        container.innerHTML = '';

        // Create particles
        const particleCount = window.innerWidth < 768 ? 20 : 50;

        for (let i = 0; i < particleCount; i++) {
            const particle = document.createElement('div');
            particle.className = 'particle';

            // Random positioning and sizing
            const size = Math.random() * 3 + 1;
            particle.style.width = `${size}px`;
            particle.style.height = `${size}px`;
            particle.style.left = `${Math.random() * 100}%`;
            particle.style.top = `${Math.random() * 100}%`;

            // Random animation properties
            const duration = Math.random() * 20 + 10;
            const delay = Math.random() * 5;
            particle.style.animationDuration = `${duration}s`;
            particle.style.animationDelay = `-${delay}s`;
            particle.style.opacity = Math.random() * 0.5 + 0.1;

            container.appendChild(particle);
        }
    }

    // Static method: Initialize ripple effects
    static initRippleEffects() {
        document.addEventListener('click', (e) => {
            const target = e.target.closest('.ripple');
            if (!target) return;

            const rect = target.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;

            const circle = document.createElement('span');
            const diameter = Math.max(rect.width, rect.height);
            const radius = diameter / 2;

            circle.style.width = circle.style.height = `${diameter}px`;
            circle.style.left = `${x - radius}px`;
            circle.style.top = `${y - radius}px`;
            circle.classList.add('ripple-effect');

            const ripple = target.getElementsByClassName('ripple-effect')[0];
            if (ripple) {
                ripple.remove();
            }

            target.appendChild(circle);

            // Clean up
            setTimeout(() => {
                circle.remove();
            }, 600);
        });
    }

    // Static method: Initialize floating labels
    static initFloatingLabels() {
        const inputs = document.querySelectorAll('.floating-label .interactive');

        inputs.forEach(input => {
            // Initial check
            if (input.value) {
                input.classList.add('has-value');
            }

            input.addEventListener('input', () => {
                if (input.value) {
                    input.classList.add('has-value');
                } else {
                    input.classList.remove('has-value');
                }
            });

            input.addEventListener('focus', () => {
                input.parentElement.classList.add('focused');
            });

            input.addEventListener('blur', () => {
                input.parentElement.classList.remove('focused');
            });
        });
    }

    // Instance method: Setup sidebar-specific interactions
    setupSidebarEnhancements() {
        try {
            const sidebar = document.querySelector('aside.stack');
            if (!sidebar) return;

            // Allow collapsing/expanding the sidebar by clicking the header area
            const title = sidebar.querySelector('.phase');
            if (title) {
                title.style.cursor = 'pointer';
                title.addEventListener('click', () => {
                    sidebar.classList.toggle('collapsed');
                });
            }

            // Add hover depth class using CSS already present
            sidebar.addEventListener('mouseenter', () => sidebar.classList.add('hovered'));
            sidebar.addEventListener('mouseleave', () => sidebar.classList.remove('hovered'));
        } catch (e) {
            console.warn('setupSidebarEnhancements failed', e);
        }
    }

    // Removed conflicting methods: setupProgressEnhancements, setupButtonHierarchy, setupBrowserBehavior, setupAccessibility, setupProfessionalInteractions


    // Setup Advanced Settings Accordion
    setupAdvancedSettingsAccordion() {
        const toggleBtn = document.querySelector('.advanced-toggle');
        const content = document.getElementById('advancedContent');

        if (toggleBtn && content) {
            toggleBtn.addEventListener('click', () => {
                const isExpanded = toggleBtn.getAttribute('aria-expanded') === 'true';
                toggleBtn.setAttribute('aria-expanded', !isExpanded);
                content.hidden = isExpanded;
            });
        }
    }

    // Setup Advanced Settings Tabs
    setupAdvancedSettingsTabs() {
        const tabButtons = document.querySelectorAll('.settings-tabs .tab-btn');
        const tabPanels = document.querySelectorAll('.tab-panels .tab-panel');

        if (tabButtons.length && tabPanels.length) {
            tabButtons.forEach(btn => {
                btn.addEventListener('click', () => {
                    const tabId = btn.getAttribute('data-tab');
                    const targetPanel = document.getElementById(`tab-${tabId}`);

                    // Update buttons
                    tabButtons.forEach(b => {
                        b.classList.remove('active');
                        b.setAttribute('aria-selected', 'false');
                    });
                    btn.classList.add('active');
                    btn.setAttribute('aria-selected', 'true');

                    // Update panels
                    tabPanels.forEach(panel => {
                        panel.classList.remove('active');
                        panel.hidden = true;
                    });
                    if (targetPanel) {
                        targetPanel.classList.add('active');
                        targetPanel.hidden = false;
                    }
                });
            });
        }
    }

    // File type icon mapping
    static FILE_TYPE_ICONS = {
  // Documents
  pdf: { icon: '📄', badge: 'pdf', class: 'pdf' },
  doc: { icon: '📝', badge: 'doc', class: 'doc' },
  docx: { icon: '📝', badge: 'doc', class: 'doc' },
  txt: { icon: '📄', badge: 'txt', class: 'default' },
  rtf: { icon: '📝', badge: 'rtf', class: 'doc' },

  // Spreadsheets
  xls: { icon: '📊', badge: 'xls', class: 'doc' },
  xlsx: { icon: '📊', badge: 'xlsx', class: 'doc' },
  csv: { icon: '📊', badge: 'csv', class: 'doc' },

  // Images
  jpg: { icon: '🖼️', badge: 'jpg', class: 'img' },
  jpeg: { icon: '🖼️', badge: 'jpeg', class: 'img' },
  png: { icon: '🖼️', badge: 'png', class: 'img' },
  gif: { icon: '🖼️', badge: 'gif', class: 'img' },
  svg: { icon: '🖼️', badge: 'svg', class: 'img' },
  webp: { icon: '🖼️', badge: 'webp', class: 'img' },

  // Videos
  mp4: { icon: '🎥', badge: 'mp4', class: 'video' },
  avi: { icon: '🎥', badge: 'avi', class: 'video' },
  mkv: { icon: '🎥', badge: 'mkv', class: 'video' },
  mov: { icon: '🎥', badge: 'mov', class: 'video' },

  // Audio
  mp3: { icon: '🎵', badge: 'mp3', class: 'audio' },
  wav: { icon: '🎵', badge: 'wav', class: 'audio' },
  flac: { icon: '🎵', badge: 'flac', class: 'audio' },

  // Archives
  zip: { icon: '📦', badge: 'zip', class: 'archive' },
  rar: { icon: '📦', badge: 'rar', class: 'archive' },
  '7z': { icon: '📦', badge: '7z', class: 'archive' },
  tar: { icon: '📦', badge: 'tar', class: 'archive' },
  gz: { icon: '📦', badge: 'gz', class: 'archive' },

  // Code
  js: { icon: '💻', badge: 'js', class: 'code' },
  py: { icon: '💻', badge: 'py', class: 'code' },
  html: { icon: '💻', badge: 'html', class: 'code' },
  css: { icon: '💻', badge: 'css', class: 'code' },
  json: { icon: '💻', badge: 'json', class: 'code' },
  xml: { icon: '💻', badge: 'xml', class: 'code' },

  // Default
  default: { icon: '📄', badge: 'file', class: 'default' }
};

    // Get file type info
    static getFileTypeInfo(filename) {
        const ext = filename.split('.').pop().toLowerCase();
        return ProfessionalGUIEnhancements.FILE_TYPE_ICONS[ext] || ProfessionalGUIEnhancements.FILE_TYPE_ICONS.default;
    }

    // Format file modified date
    static formatModifiedDate(date) {
        const now = new Date();
        const diff = now - date;
        const days = Math.floor(diff / (1000 * 60 * 60 * 24));

        if (days === 0) {
            return 'Today';
        } else if (days === 1) {
            return 'Yesterday';
        } else if (days < 7) {
            return `${days} days ago`;
        } else {
            return date.toLocaleDateString();
        }
    }

    // Update file card with rich preview (Icons and Badges only - text handled by app.js)
    static updateFileCardPreview(file) {
        const fileIcon = document.getElementById('fileIcon');
        const fileMetadata = document.getElementById('fileMetadata');
        const fileTypeBadge = document.getElementById('fileTypeBadge');
        const fileModified = document.getElementById('fileModified');

        // New elements for toggling
        const defaultContent = document.getElementById('defaultDropContent');
        const previewCard = document.getElementById('filePreviewCard');
        const fileNameDisplay = document.getElementById('fileNameDisplay');

        if (!file) {
            // Reset/Hide metadata if no file
            if (defaultContent) defaultContent.style.display = 'flex';
            if (previewCard) previewCard.style.display = 'none';

            if (fileIcon) fileIcon.textContent = '';
            if (fileMetadata) fileMetadata.style.display = 'none';
            if (fileTypeBadge) fileTypeBadge.className = 'file-badge';
            if (fileModified) fileModified.textContent = '';
            return;
        }

        // Show preview, hide default
        if (defaultContent) defaultContent.style.display = 'none';
        if (previewCard) previewCard.style.display = 'grid';

        const typeInfo = ProfessionalGUIEnhancements.getFileTypeInfo(file.name);
        const modifiedDate = ProfessionalGUIEnhancements.formatModifiedDate(new Date(file.lastModified));

        // Update icon
        if (fileIcon) {
            fileIcon.textContent = typeInfo.icon;
        }

        // Update name
        if (fileNameDisplay) {
            fileNameDisplay.textContent = file.name;
        }

        // Update metadata visibility
        if (fileMetadata) {
            fileMetadata.style.display = 'flex';
        }

        if (fileTypeBadge) {
            fileTypeBadge.textContent = typeInfo.badge.toUpperCase();
            fileTypeBadge.className = `file-badge ${typeInfo.class}`;
        }

        if (fileModified) {
            fileModified.textContent = `Modified: ${modifiedDate}`;
        }
    }

    // Helper function for file size formatting
    static formatBytes(bytes, decimals = 2) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
    }

    // Removed conflicting methods: ProgressRingStates, updateProgressRingState, validateServerInput, validateUsername, updateValidationIcon, setupValidation, updatePrimaryButtonState


    // Connection dropdown toggle
    static setupConnectionDropdown() {
        const statusBadge = document.getElementById('connStatus');
        const dropdown = document.getElementById('connectionDetails');

        if (!statusBadge || !dropdown) return;

        statusBadge.addEventListener('click', (e) => {
            e.stopPropagation();
            dropdown.classList.toggle('show');
        });

        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!dropdown.contains(e.target) && !statusBadge.contains(e.target)) {
                dropdown.classList.remove('show');
            }
        });
    }

    // Log search functionality
    static setupLogSearch() {
        const searchInput = document.getElementById('logSearchInput');
        const logContainer = document.getElementById('logContainer');

        if (!searchInput || !logContainer) return;

        let searchTimeout;

        searchInput.addEventListener('input', () => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                const query = searchInput.value.toLowerCase().trim();
                ProfessionalGUIEnhancements.filterLogs(query);
            }, 300); // Debounce 300ms
        });
    }

    static filterLogs(query) {
        const logContainer = document.getElementById('logContainer');
        if (!logContainer) return;

        const logEntries = logContainer.querySelectorAll('[data-log-entry]');

        if (!query) {
            logEntries.forEach(entry => {
                entry.style.display = '';
            });
            return;
        }

        logEntries.forEach(entry => {
            const text = entry.textContent.toLowerCase();
            if (text.includes(query)) {
                entry.style.display = '';
            } else {
                entry.style.display = 'none';
            }
        });
    }

    // Speed chart implementation (inner class)
    static SpeedChart = class {
        constructor(canvasId) {
            this.canvas = document.getElementById(canvasId);
            if (!this.canvas) return;

            this.ctx = this.canvas.getContext('2d');
            this.dataPoints = [];
            this.maxDataPoints = 30; // 30 seconds of data
            this.maxSpeed = 0;

            // Setup canvas size
            this.resizeCanvas();
            window.addEventListener('resize', () => this.resizeCanvas());
        }

        resizeCanvas() {
            if (!this.canvas) return;
            const rect = this.canvas.getBoundingClientRect();
            this.canvas.width = rect.width * window.devicePixelRatio;
            this.canvas.height = rect.height * window.devicePixelRatio;
            this.ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
            this.draw();
        }

        addDataPoint(speed) {
            this.dataPoints.push(speed);

            // Keep only last N points
            if (this.dataPoints.length > this.maxDataPoints) {
                this.dataPoints.shift();
            }

            // Update max for scaling
            this.maxSpeed = Math.max(...this.dataPoints, this.maxSpeed * 0.95);

            this.draw();
        }

        draw() {
            if (!this.ctx || this.dataPoints.length === 0) return;

            const width = this.canvas.width / window.devicePixelRatio;
            const height = this.canvas.height / window.devicePixelRatio;
            const padding = 10;
            const chartWidth = width - padding * 2;
            const chartHeight = height - padding * 2;

            // Clear canvas
            this.ctx.clearRect(0, 0, width, height);

            // Draw grid lines
            this.ctx.strokeStyle = '#30363d';
            this.ctx.lineWidth = 1;
            for (let i = 0; i <= 4; i++) {
                const y = padding + (chartHeight / 4) * i;
                this.ctx.beginPath();
                this.ctx.moveTo(padding, y);
                this.ctx.lineTo(width - padding, y);
                this.ctx.stroke();
            }

            // Draw line chart
            this.ctx.strokeStyle = '#58a6ff';
            this.ctx.lineWidth = 2;
            this.ctx.beginPath();

            this.dataPoints.forEach((speed, index) => {
                const x = padding + (chartWidth / (this.maxDataPoints - 1)) * index;
                const y = padding + chartHeight - (speed / this.maxSpeed) * chartHeight;

                if (index === 0) {
                    this.ctx.moveTo(x, y);
                } else {
                    this.ctx.lineTo(x, y);
                }
            });

            this.ctx.stroke();

            // Draw fill gradient
            this.ctx.lineTo(width - padding, height - padding);
            this.ctx.lineTo(padding, height - padding);
            this.ctx.closePath();

            const gradient = this.ctx.createLinearGradient(0, padding, 0, height - padding);
            gradient.addColorStop(0, 'rgba(88, 166, 255, 0.2)');
            gradient.addColorStop(1, 'rgba(88, 166, 255, 0.0)');
            this.ctx.fillStyle = gradient;
            this.ctx.fill();
        }

        clear() {
            this.dataPoints = [];
            this.maxSpeed = 0;
            if (this.ctx) {
                const width = this.canvas.width / window.devicePixelRatio;
                const height = this.canvas.height / window.devicePixelRatio;
                this.ctx.clearRect(0, 0, width, height);
            }
        }
    }

    // Initialize speed chart
    static setupSpeedChart() {
        ProfessionalGUIEnhancements.chartInstance = new ProfessionalGUIEnhancements.SpeedChart('speedChart');

        const toggleBtn = document.getElementById('toggleSpeedChart');
        const container = document.getElementById('speedChartContainer');

        if (toggleBtn && container) {
            toggleBtn.addEventListener('click', () => {
                const isVisible = container.classList.contains('show');
                if (isVisible) {
                    container.classList.remove('show');
                    toggleBtn.textContent = 'Show Chart';
                } else {
                    container.classList.add('show');
                    toggleBtn.textContent = 'Hide Chart';
                    if (ProfessionalGUIEnhancements.chartInstance) ProfessionalGUIEnhancements.chartInstance.draw();
                }
            });
        }
    }

    // Removed conflicting methods: setupThemeToggle

    // Initialize all enhancements
    static initializeEnhancements() {
        ProfessionalGUIEnhancements.addEnhancementStyles();
        ProfessionalGUIEnhancements.setupConnectionDropdown();
        ProfessionalGUIEnhancements.setupLogSearch();
        ProfessionalGUIEnhancements.setupSpeedChart();

        // Enhanced interactions
        ProfessionalGUIEnhancements.initDataParticles();
        ProfessionalGUIEnhancements.initRippleEffects();
        ProfessionalGUIEnhancements.initFloatingLabels();

        // Watch for file selection changes to update icons/badges
        const fileInput = document.getElementById('fileInput');
        if (fileInput) {
            fileInput.addEventListener('change', () => {
                if (fileInput.files && fileInput.files[0]) {
                    ProfessionalGUIEnhancements.updateFileCardPreview(fileInput.files[0]);
                } else {
                    ProfessionalGUIEnhancements.updateFileCardPreview(null);
                }
            });
        }

        // Watch for clear button
        const clearBtn = document.getElementById('clearFileBtn');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => {
                ProfessionalGUIEnhancements.updateFileCardPreview(null);
            });
        }

        // Responsive particle count on resize
        let resizeTimeout;
        window.addEventListener('resize', () => {
            clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(() => {
                ProfessionalGUIEnhancements.initDataParticles();
            }, 250);
        });

        // Initialize new professional enhancements
        new ProfessionalGUIEnhancements();
    }

    // Add CSS animations for enhancement effects
    static addEnhancementStyles() {
        const style = document.createElement('style');
        style.textContent = `
            @keyframes ripple {
                to {
                    transform: scale(2);
                    opacity: 0;
                }
            }

            .success-pulse {
                animation: successPulse 1s ease-out;
            }

            @keyframes successPulse {
                0% { transform: scale(1); }
                50% { transform: scale(1.02); }
                100% { transform: scale(1); }
            }

            .label-focused {
                transform: translateY(-1px);
            }

            .input-valid {
                border-color: var(--success) !important;
            }

            .input-invalid {
                border-color: var(--danger) !important;
            }

            .primary-hover {
                transform: translateY(-2px) !important;
            }

            .secondary-hover {
                transform: translateY(-1px) !important;
            }

            .card-hover {
                transform: translateY(-2px) !important;
            }

            .badge-hover {
                transform: scale(1.05) !important;
            }

            .element-focused {
                outline: 2px solid var(--focus) !important;
                outline-offset: 2px !important;
            }

            .tab-inactive {
                opacity: 0.8;
            }

            .refreshing {
                animation: refreshing 1s ease-in-out;
            }

            @keyframes refreshing {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }

            .resizing {
                transition: all 0.3s ease !important;
            }
        `;
        document.head.appendChild(style);
    }
}

// Export for potential external use
window.ProfessionalGUIEnhancements = ProfessionalGUIEnhancements;

// Export functions for use by main app
if (typeof window !== 'undefined') {
    window.Enhancements = {
        updateFileCardPreview: ProfessionalGUIEnhancements.updateFileCardPreview,
        getFileTypeInfo: ProfessionalGUIEnhancements.getFileTypeInfo,
        updateSpeedChart: (speed) => {
            if (ProfessionalGUIEnhancements.chartInstance) {
                ProfessionalGUIEnhancements.chartInstance.addDataPoint(speed);
            }
        },
        showNotification: ProfessionalGUIEnhancements.showNotification,
        initializeEnhancements: ProfessionalGUIEnhancements.initializeEnhancements
    };
}

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', ProfessionalGUIEnhancements.initializeEnhancements);
} else {
    ProfessionalGUIEnhancements.initializeEnhancements();
}

export {
    ProfessionalGUIEnhancements,
    ProfessionalGUIEnhancements as default
};
// End of enhancements.js