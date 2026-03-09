'use client';

import { useContext } from 'react';
import { ThemeContext } from '@/components/theme/ThemeProvider';

export type Theme = 'dark' | 'light';

export interface ThemeContextValue {
  theme: Theme;
  toggleTheme: () => void;
}

/**
 * Hook to access the current theme and toggle function.
 * Must be used within a ThemeProvider.
 * 
 * @returns {ThemeContextValue} Object containing current theme and toggleTheme function
 * @throws {Error} If used outside of ThemeProvider
 */
export function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext);
  
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  
  return context;
}
