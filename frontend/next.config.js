/** @type {import('next').NextConfig} */
const nextConfig = {
  distDir: '.next-3100',
  allowedDevOrigins: ['10.20.236.91', 'localhost', '192.168.1.9'],
  turbopack: {
    root: __dirname,
  },
};

module.exports = nextConfig;
