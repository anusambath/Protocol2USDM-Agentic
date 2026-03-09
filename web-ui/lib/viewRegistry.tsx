import React from 'react';
import dynamic from 'next/dynamic';
import { ViewType } from '@/stores/layoutStore';
import { ProvenanceDataExtended } from '@/lib/provenance/types';

// Use dynamic imports to avoid massive import chain that causes segfaults
// Use ssr: false to prevent hydration mismatches
const StudyMetadataView = dynamic(() => import('@/components/protocol/StudyMetadataView').then(m => ({ default: m.StudyMetadataView })), { ssr: false });
const EligibilityCriteriaView = dynamic(() => import('@/components/protocol/EligibilityCriteriaView').then(m => ({ default: m.EligibilityCriteriaView })), { ssr: false });
const ObjectivesEndpointsView = dynamic(() => import('@/components/protocol/ObjectivesEndpointsView').then(m => ({ default: m.ObjectivesEndpointsView })), { ssr: false });
const StudyDesignView = dynamic(() => import('@/components/protocol/StudyDesignView').then(m => ({ default: m.StudyDesignView })), { ssr: false });
const InterventionsView = dynamic(() => import('@/components/protocol/InterventionsView').then(m => ({ default: m.InterventionsView })), { ssr: false });
const AmendmentHistoryView = dynamic(() => import('@/components/protocol/AmendmentHistoryView').then(m => ({ default: m.AmendmentHistoryView })), { ssr: false });
const ExtensionsView = dynamic(() => import('@/components/protocol/ExtensionsView').then(m => ({ default: m.ExtensionsView })), { ssr: false });
const AdvancedEntitiesView = dynamic(() => import('@/components/protocol/AdvancedEntitiesView').then(m => ({ default: m.AdvancedEntitiesView })), { ssr: false });
const ProceduresDevicesView = dynamic(() => import('@/components/protocol/ProceduresDevicesView').then(m => ({ default: m.ProceduresDevicesView })), { ssr: false });
const StudySitesView = dynamic(() => import('@/components/protocol/StudySitesView').then(m => ({ default: m.StudySitesView })), { ssr: false });
const FootnotesView = dynamic(() => import('@/components/protocol/FootnotesView').then(m => ({ default: m.FootnotesView })), { ssr: false });
const ScheduleTimelineView = dynamic(() => import('@/components/protocol/ScheduleTimelineView').then(m => ({ default: m.ScheduleTimelineView })), { ssr: false });
const NarrativeView = dynamic(() => import('@/components/protocol/NarrativeView').then(m => ({ default: m.NarrativeView })), { ssr: false });
const QualityMetricsDashboard = dynamic(() => import('@/components/quality/QualityMetricsDashboard').then(m => ({ default: m.QualityMetricsDashboard })), { ssr: false });
const ValidationResultsView = dynamic(() => import('@/components/quality/ValidationResultsView').then(m => ({ default: m.ValidationResultsView })), { ssr: false });
const DocumentStructureView = dynamic(() => import('@/components/intermediate/DocumentStructureView').then(m => ({ default: m.DocumentStructureView })), { ssr: false });
const SoAImagesTab = dynamic(() => import('@/components/intermediate/SoAImagesTab').then(m => ({ default: m.SoAImagesTab })), { ssr: false });
const SoAView = dynamic(() => import('@/components/soa/SoAView').then(m => ({ default: m.SoAView })), { ssr: false });
const TimelineView = dynamic(() => import('@/components/timeline/TimelineView').then(m => ({ default: m.TimelineView })), { ssr: false });
const ProvenanceView = dynamic(() => import('@/components/provenance/ProvenanceView').then(m => ({ default: m.ProvenanceView })), { 
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-full p-8">
      <div className="space-y-4 w-full max-w-4xl">
        {/* Stats skeleton */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="animate-pulse bg-gray-200 dark:bg-gray-700 rounded-lg h-24" />
          ))}
        </div>
        {/* Controls skeleton */}
        <div className="animate-pulse bg-gray-200 dark:bg-gray-700 rounded-lg h-32" />
        {/* Content skeleton */}
        <div className="space-y-2">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="animate-pulse bg-gray-200 dark:bg-gray-700 rounded-lg h-16" />
          ))}
        </div>
      </div>
    </div>
  )
});

/**
 * Props interface for all view components
 */
export interface ViewProps {
  usdm: Record<string, unknown>;
  protocolId: string;
  provenance: ProvenanceDataExtended | null;
  intermediateFiles?: Record<string, unknown> | null;
  onNodeSelect?: (nodeId: string, data: Record<string, unknown>) => void;
  onCellSelect?: (cellId: string) => void;
  executionModel?: unknown | null;
}

/**
 * View registry entry mapping ViewType to React component and metadata
 */
export interface ViewRegistryEntry {
  viewType: ViewType;
  label: string;
  icon: string; // Lucide icon name
  group: 'protocol' | 'advanced' | 'quality' | 'data';
  component: React.ComponentType<any>; // Using any to accommodate different prop signatures
}

/**
 * View registry mapping ViewType enum to React component + metadata
 * Used by CenterPanel to render the correct component for each tab,
 * and by NavTree/CommandPalette to list available views.
 */
export const viewRegistry: Record<ViewType, ViewRegistryEntry> = {
  // Protocol group
  overview: {
    viewType: 'overview',
    label: 'Study Metadata',
    icon: 'FileText',
    group: 'protocol',
    component: StudyMetadataView,
  },
  eligibility: {
    viewType: 'eligibility',
    label: 'Eligibility Criteria',
    icon: 'UserCheck',
    group: 'protocol',
    component: EligibilityCriteriaView,
  },
  objectives: {
    viewType: 'objectives',
    label: 'Objectives & Endpoints',
    icon: 'Target',
    group: 'protocol',
    component: ObjectivesEndpointsView,
  },
  design: {
    viewType: 'design',
    label: 'Study Design',
    icon: 'Network',
    group: 'protocol',
    component: StudyDesignView,
  },
  interventions: {
    viewType: 'interventions',
    label: 'Interventions',
    icon: 'Pill',
    group: 'protocol',
    component: InterventionsView,
  },
  amendments: {
    viewType: 'amendments',
    label: 'Amendment History',
    icon: 'History',
    group: 'protocol',
    component: AmendmentHistoryView,
  },

  // Advanced group
  extensions: {
    viewType: 'extensions',
    label: 'Extensions',
    icon: 'Puzzle',
    group: 'advanced',
    component: ExtensionsView,
  },
  entities: {
    viewType: 'entities',
    label: 'Advanced Entities',
    icon: 'Database',
    group: 'advanced',
    component: AdvancedEntitiesView,
  },
  procedures: {
    viewType: 'procedures',
    label: 'Procedures & Devices',
    icon: 'Stethoscope',
    group: 'advanced',
    component: ProceduresDevicesView,
  },
  sites: {
    viewType: 'sites',
    label: 'Study Sites',
    icon: 'MapPin',
    group: 'advanced',
    component: StudySitesView,
  },
  footnotes: {
    viewType: 'footnotes',
    label: 'Footnotes',
    icon: 'MessageSquare',
    group: 'advanced',
    component: FootnotesView,
  },
  schedule: {
    viewType: 'schedule',
    label: 'Schedule Timeline',
    icon: 'Calendar',
    group: 'advanced',
    component: ScheduleTimelineView,
  },
  narrative: {
    viewType: 'narrative',
    label: 'Narrative',
    icon: 'BookOpen',
    group: 'advanced',
    component: NarrativeView,
  },

  // Quality group
  quality: {
    viewType: 'quality',
    label: 'Quality Metrics',
    icon: 'BarChart3',
    group: 'quality',
    component: QualityMetricsDashboard,
  },
  validation: {
    viewType: 'validation',
    label: 'Validation Results',
    icon: 'CheckCircle2',
    group: 'quality',
    component: ValidationResultsView,
  },

  // Data group
  document: {
    viewType: 'document',
    label: 'Document Structure',
    icon: 'FileTree',
    group: 'data',
    component: DocumentStructureView,
  },
  images: {
    viewType: 'images',
    label: 'SoA Images',
    icon: 'Image',
    group: 'data',
    component: SoAImagesTab,
  },
  soa: {
    viewType: 'soa',
    label: 'SoA Table',
    icon: 'Table',
    group: 'data',
    component: SoAView,
  },
  timeline: {
    viewType: 'timeline',
    label: 'Timeline',
    icon: 'GitBranch',
    group: 'data',
    component: TimelineView,
  },
  provenance: {
    viewType: 'provenance',
    label: 'Provenance',
    icon: 'Info',
    group: 'data',
    component: ProvenanceView,
  },
};

/**
 * Helper function to get view registry entry by ViewType
 */
export function getViewEntry(viewType: ViewType): ViewRegistryEntry | undefined {
  return viewRegistry[viewType];
}

/**
 * Helper function to get all views in a specific group
 */
export function getViewsByGroup(
  group: 'protocol' | 'advanced' | 'quality' | 'data'
): ViewRegistryEntry[] {
  return Object.values(viewRegistry).filter((entry) => entry.group === group);
}

/**
 * Helper function to get all view types
 */
export function getAllViewTypes(): ViewType[] {
  return Object.keys(viewRegistry) as ViewType[];
}
