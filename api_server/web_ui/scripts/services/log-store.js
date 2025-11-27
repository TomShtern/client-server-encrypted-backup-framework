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

export class LogStore {
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

