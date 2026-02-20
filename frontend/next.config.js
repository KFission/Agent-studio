/** @type {import('next').NextConfig} */
const backendTarget = process.env.BACKEND_API_URL || "http://backend:8080";
const normalizedBackendTarget = backendTarget.endsWith("/")
  ? backendTarget.slice(0, -1)
  : backendTarget;

const nextConfig = {
  output: 'standalone',
  reactStrictMode: true,
  // Tree-shake lucide-react — transform barrel imports to direct per-icon imports
  modularizeImports: {
    'lucide-react': {
      transform: 'lucide-react/dist/esm/icons/{{ kebabCase member }}',
    },
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${normalizedBackendTarget}/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
