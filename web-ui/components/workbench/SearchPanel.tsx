'use client';

import React from 'react';
import { Search } from 'lucide-react';
import { ViewType } from '@/stores/layoutStore';

interface SearchPanelProps {
  onNavigate: (viewType: ViewType) => void;
}

export function SearchPanel({ onNavigate }: SearchPanelProps) {
  return (
    <div className="flex flex-col items-center justify-center h-full p-6 text-center">
      <Search className="h-12 w-12 text-muted-foreground mb-4" />
      <h3 className="text-sm font-medium text-foreground mb-2">
        Search functionality coming soon
      </h3>
      <p className="text-xs text-muted-foreground">
        This panel will allow you to search across all protocol sections and navigate quickly to specific content.
      </p>
    </div>
  );
}
