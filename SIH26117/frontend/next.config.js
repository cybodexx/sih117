/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  reactStrictMode: true,
  env: {
    NEXT_TELEMETRY_DISABLED: "1",
  },
  async rewrites() {
    // Same-origin API proxy: in airgapped mode the ONLY egress surface is this
    // web server; it relays /api/* to the API container over the internal net.
    return [
      {
        source: "/api/:path*",
        destination: "http://api:8000/api/:path*",
      },
    ];
  },
};

module.exports = nextConfig;
