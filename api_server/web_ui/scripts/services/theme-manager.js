const STORAGE_KEY = 'cyberbackup-theme';

export class ThemeManager {
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
