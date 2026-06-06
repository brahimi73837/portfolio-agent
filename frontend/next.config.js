/** @type {import('next').NextConfig} */
const nextConfig = {
  // 'standalone' produces a minimal self-contained server for a small Docker image.
  output: "standalone",
  reactStrictMode: true,
};
module.exports = nextConfig;
