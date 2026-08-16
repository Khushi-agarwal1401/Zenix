import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  // React Compiler is disabled in dev for faster compilation speed.
  // It runs only in production builds.
  reactCompiler: process.env.NODE_ENV === 'production',
};

export default nextConfig;
