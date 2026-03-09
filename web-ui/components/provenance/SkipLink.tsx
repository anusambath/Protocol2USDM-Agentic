/**
 * SkipLink component
 * 
 * Provides a skip link for keyboard users to jump to main content
 * 
 * Features:
 * - Only visible when focused
 * - Allows keyboard users to skip navigation
 * - WCAG 2.1 Level AA compliant
 */

import React from 'react';

interface SkipLinkProps {
  href: string;
  children: React.ReactNode;
}

export function SkipLink({ href, children }: SkipLinkProps) {
  return (
    <a
      href={href}
      className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:px-4 focus:py-2 focus:bg-blue-600 focus:text-white focus:rounded focus:shadow-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
    >
      {children}
    </a>
  );
}
