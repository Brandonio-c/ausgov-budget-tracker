import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",
  basePath: "/ausgov-budget-tracker",
  trailingSlash: true,
  transpilePackages: ["pdfjs-dist"],
};

export default nextConfig;
