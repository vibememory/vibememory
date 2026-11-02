import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: false,
  poweredByHeader: false,
  images: { unoptimized: true },
  generateBuildId: async () => "vibe-memory-20261102-v030-4",
};

export default nextConfig;
