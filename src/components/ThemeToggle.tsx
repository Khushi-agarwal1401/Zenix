/**
 * Theme Toggle Component for Zenix AI
 * Provides dark mode toggle with localStorage persistence
 */

'use client';

import React, { useEffect, useState } from 'react';

type Theme = 'light' | 'dark' | 'system';

interface ThemeToggleProps {
  className?: string;
}

export default function ThemeToggle({ className = '' }: ThemeToggleProps) {
  const [theme, setTheme] = useState<Theme>('system');
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    // Load saved theme from localStorage
    const savedTheme = localStorage.getItem('zenix-theme') as Theme;
    if (savedTheme) {
      setTheme(savedTheme);
      applyTheme(savedTheme);
    } else {
      // Check system preference
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      setTheme(prefersDark ? 'dark' : 'light');
      applyTheme(prefersDark ? 'dark' : 'light');
    }
  }, []);

  const applyTheme = (newTheme: Theme) => {
    const root = document.documentElement;
    
    if (newTheme === 'dark' || (newTheme === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
      root.classList.add('dark');
      root.classList.remove('light');
    } else {
      root.classList.add('light');
      root.classList.remove('dark');
    }
  };

  const handleThemeChange = (newTheme: Theme) => {
    setTheme(newTheme);
    localStorage.setItem('zenix-theme', newTheme);
    applyTheme(newTheme);
  };

  if (!mounted) {
    return null;
  }

  return (
    <div className={`theme-toggle ${className}`}>
      <button
        onClick={() => handleThemeChange('light')}
        className={`theme-btn ${theme === 'light' ? 'active' : ''}`}
        aria-label="Light mode"
        title="Light Mode"
      >
        ☀️
      </button>
      <button
        onClick={() => handleThemeChange('dark')}
        className={`theme-btn ${theme === 'dark' ? 'active' : ''}`}
        aria-label="Dark mode"
        title="Dark Mode"
      >
        🌙
      </button>
      <button
        onClick={() => handleThemeChange('system')}
        className={`theme-btn ${theme === 'system' ? 'active' : ''}`}
        aria-label="System theme"
        title="System Theme"
      >
        💻
      </button>
    </div>
  );
}

// CSS styles for theme toggle
export const themeToggleStyles = `
.theme-toggle {
  display: flex;
  gap: 4px;
  padding: 4px;
  background: var(--bg-secondary, #f3f4f6);
  border-radius: 8px;
}

.theme-btn {
  padding: 6px 10px;
  border: none;
  border-radius: 6px;
  background: transparent;
  cursor: pointer;
  font-size: 16px;
  transition: all 0.2s ease;
}

.theme-btn:hover {
  background: var(--bg-hover, #e5e7eb);
}

.theme-btn.active {
  background: var(--bg-active, #ffffff);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

/* Dark mode styles */
.dark {
  --bg-primary: #111827;
  --bg-secondary: #1f2937;
  --bg-hover: #374151;
  --bg-active: #4b5563;
  --text-primary: #f9fafb;
  --text-secondary: #d1d5db;
  --border-color: #374151;
}

.dark body {
  background-color: #111827;
  color: #f9fafb;
}

/* Light mode styles */
.light {
  --bg-primary: #ffffff;
  --bg-secondary: #f3f4f6;
  --bg-hover: #e5e7eb;
  --bg-active: #ffffff;
  --text-primary: #111827;
  --text-secondary: #4b5563;
  --border-color: #e5e7eb;
}
`;
