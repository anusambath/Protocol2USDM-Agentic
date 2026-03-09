/**
 * Centralized constants for Protocol2USDM web UI.
 */

/** Extension namespace for USDM extensionAttributes */
export const EXTENSION_NAMESPACE =
  'https://anusambath.github.io/Protocol2USDM-Agentic/extensions';

/** Build a full extension URL from a short name, e.g. 'x-epochCategory' */
export function extensionUrl(name: string): string {
  return `${EXTENSION_NAMESPACE}/${name}`;
}
