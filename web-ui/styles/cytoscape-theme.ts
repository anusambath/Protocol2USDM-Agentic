import type { Stylesheet } from 'cytoscape';

export const cytoscapeStyles: Stylesheet[] = [
  {
    selector: 'node',
    style: {
      'background-color': '#ffffff',
      'border-color': '#6366f1',
      'border-width': 2,
      'label': 'data(label)',
      'color': '#1e293b',
      'font-size': 12,
      'text-valign': 'center',
      'text-halign': 'center',
      'text-wrap': 'wrap',
      'text-max-width': 120,
      'width': 140,
      'height': 40,
      'shape': 'roundrectangle',
      'padding': 8,
    },
  },
  {
    selector: 'node[type="epoch"]',
    style: {
      'background-color': '#e0e7ff',
      'border-color': '#4f46e5',
      'font-weight': 'bold',
    },
  },
  {
    selector: 'node[type="encounter"]',
    style: {
      'background-color': '#f0fdf4',
      'border-color': '#16a34a',
    },
  },
  {
    selector: 'node[type="activity"]',
    style: {
      'background-color': '#fefce8',
      'border-color': '#ca8a04',
      'width': 120,
      'height': 36,
    },
  },
  {
    selector: 'node:selected',
    style: {
      'border-color': '#7c3aed',
      'border-width': 3,
    },
  },
  {
    selector: 'node.highlighted',
    style: {
      'background-color': '#ddd6fe',
      'border-color': '#7c3aed',
    },
  },
  {
    selector: 'edge',
    style: {
      'line-color': '#94a3b8',
      'target-arrow-color': '#94a3b8',
      'target-arrow-shape': 'triangle',
      'curve-style': 'bezier',
      'width': 1.5,
      'arrow-scale': 0.8,
    },
  },
  {
    selector: 'edge[style="dashed"]',
    style: {
      'line-style': 'dashed',
    },
  },
  {
    selector: 'edge[style="dotted"]',
    style: {
      'line-style': 'dotted',
    },
  },
  {
    selector: 'edge:selected',
    style: {
      'line-color': '#7c3aed',
      'target-arrow-color': '#7c3aed',
      'width': 2.5,
    },
  },
];
