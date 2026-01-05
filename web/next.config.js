/** @type {import('next').NextConfig} */
const nextConfig = {
  // Required for react-leaflet
  transpilePackages: ['react-leaflet'],
  // Output standalone build for Docker
  output: 'standalone',
};

module.exports = nextConfig;
