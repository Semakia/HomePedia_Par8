import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Emit a self-contained server bundle (.next/standalone) for a small prod
  // Docker image — see iac/docker/prod/frontend/Dockerfile.
  output: "standalone",
};

export default nextConfig;
