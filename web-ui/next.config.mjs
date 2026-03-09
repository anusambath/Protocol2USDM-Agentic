/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ['ag-grid-react', 'ag-grid-community', 'ag-grid-enterprise'],
  // Allow cross-origin hot-reload requests from LAN clients in dev (e.g. access via network IP)
  allowedDevOrigins: ['10.0.0.220'],
};

export default nextConfig;
