/**
 * Unit tests for ThemeProvider component
 * 
 * Tests verify:
 * - Default theme is 'dark' (Requirement 11.1, 11.5)
 * - Theme toggle switches between dark and light (Requirement 11.2)
 * - Theme persists to localStorage (Requirement 11.3)
 * - Theme restores from localStorage (Requirement 11.4)
 * - Document class is applied correctly
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { act } from 'react';
import { ThemeProvider } from '../ThemeProvider';
import { useTheme } from '@/hooks/useTheme';

// Test component that uses the theme hook
function TestComponent() {
  const { theme, toggleTheme } = useTheme();
  
  return (
    <div>
      <div data-testid="theme">{theme}</div>
      <button onClick={toggleTheme} data-testid="toggle">
        Toggle Theme
      </button>
    </div>
  );
}

describe('ThemeProvider', () => {
  beforeEach(() => {
    // Clear localStorage before each test
    localStorage.clear();
    // Clear document classes
    document.documentElement.classList.remove('dark');
  });

  afterEach(() => {
    localStorage.clear();
    document.documentElement.classList.remove('dark');
  });

  it('defaults to dark theme when no localStorage value exists', async () => {
    render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('theme')).toHaveTextContent('dark');
    });
    
    expect(document.documentElement.classList.contains('dark')).toBe(true);
    expect(localStorage.getItem('p2u-theme')).toBeNull();
  });

  it('restores theme from localStorage', async () => {
    localStorage.setItem('p2u-theme', 'light');

    render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('theme')).toHaveTextContent('light');
    });
    
    expect(document.documentElement.classList.contains('dark')).toBe(false);
  });

  it('toggles theme from dark to light', async () => {
    const { getByTestId } = render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    );

    await waitFor(() => {
      expect(getByTestId('theme')).toHaveTextContent('dark');
    });

    act(() => {
      getByTestId('toggle').click();
    });

    await waitFor(() => {
      expect(getByTestId('theme')).toHaveTextContent('light');
    });
    
    expect(document.documentElement.classList.contains('dark')).toBe(false);
    expect(localStorage.getItem('p2u-theme')).toBe('light');
  });

  it('toggles theme from light to dark', async () => {
    localStorage.setItem('p2u-theme', 'light');

    const { getByTestId } = render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    );

    await waitFor(() => {
      expect(getByTestId('theme')).toHaveTextContent('light');
    });

    act(() => {
      getByTestId('toggle').click();
    });

    await waitFor(() => {
      expect(getByTestId('theme')).toHaveTextContent('dark');
    });
    
    expect(document.documentElement.classList.contains('dark')).toBe(true);
    expect(localStorage.getItem('p2u-theme')).toBe('dark');
  });

  it('persists theme changes to localStorage', async () => {
    const { getByTestId } = render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    );

    await waitFor(() => {
      expect(getByTestId('theme')).toHaveTextContent('dark');
    });

    // Toggle to light
    act(() => {
      getByTestId('toggle').click();
    });

    await waitFor(() => {
      expect(localStorage.getItem('p2u-theme')).toBe('light');
    });

    // Toggle back to dark
    act(() => {
      getByTestId('toggle').click();
    });

    await waitFor(() => {
      expect(localStorage.getItem('p2u-theme')).toBe('dark');
    });
  });

  it('applies dark class to document.documentElement when theme is dark', async () => {
    render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    );

    await waitFor(() => {
      expect(document.documentElement.classList.contains('dark')).toBe(true);
    });
  });

  it('removes dark class from document.documentElement when theme is light', async () => {
    localStorage.setItem('p2u-theme', 'light');

    render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    );

    await waitFor(() => {
      expect(document.documentElement.classList.contains('dark')).toBe(false);
    });
  });

  it('throws error when useTheme is used outside ThemeProvider', () => {
    // Suppress console.error for this test
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});

    expect(() => {
      render(<TestComponent />);
    }).toThrow('useTheme must be used within a ThemeProvider');

    consoleError.mockRestore();
  });
});
