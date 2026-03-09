'use client';

import React from 'react';
import { CheckCircle2 } from 'lucide-react';

export function QualityPanel() {
  return (
    <div className="flex flex-col items-center justify-center h-full p-6 text-center">
      <CheckCircle2 className="h-12 w-12 text-muted-foreground mb-4" />
      <h3 className="text-sm font-medium text-foreground mb-2">
        Quality panel coming soon
      </h3>
      <p className="text-xs text-muted-foreground">
        This panel will display validation summaries, quality metrics, and issue breakdowns for the current protocol.
      </p>
    </div>
  );
}
