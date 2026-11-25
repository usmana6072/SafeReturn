/** @type {import('next').NextConfig} */
const nextConfig = {
  allowedDevOrigins: ['10.20.236.91', 'localhost', '192.168.1.9'],
  compress: true,
  poweredByHeader: false,
  compiler: {
    removeConsole: process.env.NODE_ENV === 'production' ? { exclude: ['error', 'warn'] } : false,
  },
  async redirects() {
    return ['safe-return-frontend\\.vercel\\.app', 'safereturnqr\\.me'].map(host => ({
      source: '/:path*',
      has: [{ type: 'host', value: host }],
      destination: 'https://www.safereturnqr.me/:path*',
      permanent: true,
    }));
  },
  turbopack: {
    root: __dirname,
  },
};

module.exports = nextConfig;
