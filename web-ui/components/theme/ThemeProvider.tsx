'use client';

import React, { createContext, useEffect, useState } from 'react';
import type { Theme, ThemeContextValue } from '@/hooks/useTheme';

const THEME_STORAGE_KEY = 'p2u-theme';
const DEFAULT_THEME: Theme = 'dark';

export const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

interface ThemeProviderProps {
  children: React.ReactNode;
}

/**
 * ThemeProvider component that manages dark/light mode for the application.
 * 
 * Features:
 * - Reads persisted theme from localStorage (key: 'p2u-theme')
 * - Defaults to 'dark' if no preference exists
 * - Applies/removes 'dark' class on document.documentElement
 * - Provides useTheme() hook returning { theme, toggleTheme }
 * - Persists theme changes to localStorage
 * 
 * Requirements: 11.1, 11.2, 11.3, 11.4, 11.5
 */
export function ThemeProvider({ children }: ThemeProviderProps) {
  const [theme, setTheme] = useState<Theme>(DEFAULT_THEME);
  const [mounted, setMounted] = useState(false);

  // Initialize theme from localStorage on mount
  useEffect(() => {
    const storedTheme = localStorage.getItem(THEME_STORAGE_KEY) as Theme | null;
    const initialTheme = storedTheme || DEFAULT_THEME;
    
    setTheme(initialTheme);
    applyThemeToDocument(initialTheme);
    setMounted(true);
  }, []);

  // Apply theme changes to document
  useEffect(() => {
    if (mounted) {
      applyThemeToDocument(theme);
    }
  }, [theme, mounted]);

  const toggleTheme = () => {
    setTheme((prevTheme) => {
      const newTheme: Theme = prevTheme === 'dark' ? 'light' : 'dark';
      
      // Persist to localStorage
      localStorage.setItem(THEME_STORAGE_KEY, newTheme);
      
      return newTheme;
    });
  };

  const value: ThemeContextValue = {
    theme,
    toggleTheme,
  };

  // Prevent flash of unstyled content by not rendering until mounted
  if (!mounted) {
    return null;
  }

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  );
}

/**
 * Applies the theme to the document by adding/removing the 'dark' class
 * on document.documentElement.
 */
function applyThemeToDocument(theme: Theme) {
  const root = document.documentElement;
  
  if (theme === 'dark') {
    root.classList.add('dark');
  } else {
    root.classList.remove('dark');
  }
}
