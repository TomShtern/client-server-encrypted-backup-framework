/**
 * Professional Desktop Web GUI Enhancements
 * JavaScript enhancements for improved user experience
 */
console.log('Enhancements module loaded');

class ProfessionalGUIEnhancements {
    constructor() {
        this.init();
    }

    // Cleanup method to prevent memory leaks
    static cleanup() {
        ProfessionalGUIEnhancements.rippleController.destroy();
        if (ProfessionalGUIEnhancements.chartInstance) {
            ProfessionalGUIEnhancements.chartInstance.destroy();
        }
    }

    init() {
        this.setupSidebarEnhancements();
        // Visual effects only
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

  
    // Static method: Initialize ripple effects
    static initRippleEffects() {
        ProfessionalGUIEnhancements.rippleController.init();
    }

    // Ripple controller for proper event listener cleanup
    static rippleController = {
        handler: null,
        init() {
            // Remove any existing listener first
            this.destroy();

            // Store reference to handler
            this.handler = (e) => this.createRipple(e);
            document.addEventListener('click', this.handler);
        },
        destroy() {
            if (this.handler) {
                document.removeEventListener('click', this.handler);
                this.handler = null;
            }
        },
        createRipple(e) {
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
        }
    };

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
        pdf: { icon: 'ðŸ“„', badge: 'pdf', class: 'pdf' },
        doc: { icon: 'ðŸ“', badge: 'doc', class: 'doc' },
        docx: { icon: 'ðŸ“', badge: 'doc', class: 'doc' },
        txt: { icon: 'ðŸ“„', badge: 'txt', class: 'default' },
        rtf: { icon: 'ðŸ“', badge: 'rtf', class: 'doc' },

        // Spreadsheets
        xls: { icon: 'ðŸ“Š', badge: 'xls', class: 'doc' },
        xlsx: { icon: 'ðŸ“Š', badge: 'xlsx', class: 'doc' },
        csv: { icon: 'ðŸ“Š', badge: 'csv', class: 'doc' },

        // Images
        jpg: { icon: 'ðŸ–¼ï¸', badge: 'jpg', class: 'img' },
        jpeg: { icon: 'ðŸ–¼ï¸', badge: 'jpeg', class: 'img' },
        png: { icon: 'ðŸ–¼ï¸', badge: 'png', class: 'img' },
        gif: { icon: 'ðŸ–¼ï¸', badge: 'gif', class: 'img' },
        svg: { icon: 'ðŸ–¼ï¸', badge: 'svg', class: 'img' },
        webp: { icon: 'ðŸ–¼ï¸', badge: 'webp', class: 'img' },

        // Videos
        mp4: { icon: 'ðŸŽ¥', badge: 'mp4', class: 'video' },
        avi: { icon: 'ðŸŽ¥', badge: 'avi', class: 'video' },
        mkv: { icon: 'ðŸŽ¥', badge: 'mkv', class: 'video' },
        mov: { icon: 'ðŸŽ¥', badge: 'mov', class: 'video' },

        // Audio
        mp3: { icon: 'ðŸŽµ', badge: 'mp3', class: 'audio' },
        wav: { icon: 'ðŸŽµ', badge: 'wav', class: 'audio' },
        flac: { icon: 'ðŸŽµ', badge: 'flac', class: 'audio' },

        // Archives
        zip: { icon: 'ðŸ“¦', badge: 'zip', class: 'archive' },
        rar: { icon: 'ðŸ“¦', badge: 'rar', class: 'archive' },
        '7z': { icon: 'ðŸ“¦', badge: '7z', class: 'archive' },
        tar: { icon: 'ðŸ“¦', badge: 'tar', class: 'archive' },
        gz: { icon: 'ðŸ“¦', badge: 'gz', class: 'archive' },

        // Code
        js: { icon: 'ðŸ’»', badge: 'js', class: 'code' },
        py: { icon: 'ðŸ’»', badge: 'py', class: 'code' },
        html: { icon: 'ðŸ’»', badge: 'html', class: 'code' },
        css: { icon: 'ðŸ’»', badge: 'css', class: 'code' },
        json: { icon: 'ðŸ’»', badge: 'json', class: 'code' },
        xml: { icon: 'ðŸ’»', badge: 'xml', class: 'code' },

        // Default
        default: { icon: 'ðŸ“„', badge: 'file', class: 'default' }
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
        // Private field declarations
        #resizeHandler = null;

        constructor(canvasId) {
            this.canvas = document.getElementById(canvasId);
            if (!this.canvas) return;

            this.ctx = this.canvas.getContext('2d');
            this.dataPoints = [];
            this.maxDataPoints = 30; // 30 seconds of data
            this.maxSpeed = 0;

            // Cache colors from CSS variables (theme-responsive)
            this.colors = this.#getColorsFromCSS();

            // Setup canvas size
            this.resizeCanvas();
            this.#attachResizeListener();
            this.#attachThemeChangeListener();
        }

        /**
         * Convert hex color to RGBA format.
         * Handles both 3-digit and 6-digit hex colors.
         * @private
         * @param {string} hex - Hex color code (e.g., '#58a6ff')
         * @param {number} alpha - Alpha value (0-1)
         * @returns {string} RGBA color string
         */
        #hexToRgba(hex, alpha) {
            // Remove # if present
            hex = hex.replace('#', '');

            // Expand 3-digit hex to 6-digit
            if (hex.length === 3) {
                hex = hex.split('').map(c => c + c).join('');
            }

            // Parse hex to RGB
            const r = parseInt(hex.substring(0, 2), 16);
            const g = parseInt(hex.substring(2, 4), 16);
            const b = parseInt(hex.substring(4, 6), 16);

            return `rgba(${r}, ${g}, ${b}, ${alpha})`;
        }

        /**
         * Get colors from CSS custom properties (theme-aware).
         * Reads from root element to get current theme colors.
         * @private
         * @returns {Object} Colors object with grid and line colors
         */
        #getColorsFromCSS() {
            const root = document.documentElement;
            const computedStyle = getComputedStyle(root);

            return {
                grid: computedStyle.getPropertyValue('--border').trim(),
                line: computedStyle.getPropertyValue('--focus').trim(),
            };
        }

        /**
         * Listen for theme changes and update colors accordingly.
         * Triggered when html element class changes (theme toggle).
         * @private
         */
        #attachThemeChangeListener() {
            // Observe class changes on html element for theme switches
            const observer = new MutationObserver(() => {
                this.colors = this.#getColorsFromCSS();
                if (this.dataPoints.length > 0) {
                    this.draw(); // Redraw chart with new colors
                }
            });

            observer.observe(document.documentElement, {
                attributes: true,
                attributeFilter: ['class'],
            });
        }

        #attachResizeListener() {
            // Store handler reference for cleanup
            this.#resizeHandler = () => this.resizeCanvas();
            window.addEventListener('resize', this.#resizeHandler);
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

            // Draw grid lines (color from CSS --border variable for theme support)
            this.ctx.strokeStyle = this.colors.grid;
            this.ctx.lineWidth = 1;
            for (let i = 0; i <= 4; i++) {
                const y = padding + (chartHeight / 4) * i;
                this.ctx.beginPath();
                this.ctx.moveTo(padding, y);
                this.ctx.lineTo(width - padding, y);
                this.ctx.stroke();
            }

            // Draw line chart (color from CSS --focus variable for theme support)
            this.ctx.strokeStyle = this.colors.line;
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

            // Create gradient with theme-aware colors
            const gradient = this.ctx.createLinearGradient(0, padding, 0, height - padding);
            gradient.addColorStop(0, this.#hexToRgba(this.colors.line, 0.2));
            gradient.addColorStop(1, this.#hexToRgba(this.colors.line, 0.0));
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

        destroy() {
            // Remove resize listener to prevent memory leak
            if (this.#resizeHandler) {
                window.removeEventListener('resize', this.#resizeHandler);
                this.#resizeHandler = null;
            }
            this.canvas = null;
            this.ctx = null;
            this.dataPoints = [];
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

    // Initialize all enhancements
    static initializeEnhancements() {
        ProfessionalGUIEnhancements.addEnhancementStyles();
        ProfessionalGUIEnhancements.setupConnectionDropdown();
        ProfessionalGUIEnhancements.setupLogSearch();
        ProfessionalGUIEnhancements.setupSpeedChart();

        // Enhanced interactions
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

// Cleanup on page unload to prevent memory leaks
window.addEventListener('beforeunload', ProfessionalGUIEnhancements.cleanup);

// Also cleanup on page visibility changes (development mode handling)
document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') {
        // Page hidden, potential module reload - clean up
        ProfessionalGUIEnhancements.cleanup();
    } else if (document.visibilityState === 'visible') {
        // Page visible again, reinitialize
        ProfessionalGUIEnhancements.initRippleEffects();
    }
});