import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: false,
  poweredByHeader: false,
  images: { unoptimized: true },
  generateBuildId: async () => "vibe-memory-20261030-v029-2",
};

export default nextConfig;
