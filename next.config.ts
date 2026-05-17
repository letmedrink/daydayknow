import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Docker生产部署需要standalone模式
  output: 'standalone',
  
  // 禁用缓存（开发模式）
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'Cache-Control',
            value: 'no-cache, no-store, must-revalidate',
          },
          {
            key: 'Pragma',
            value: 'no-cache',
          },
          {
            key: 'Expires',
            value: '0',
          },
        ],
      },
    ];
  },
  
  // 实验性功能
  experimental: {
    optimizePackageImports: ['@supabase/supabase-js', 'openai'],
  },
};

export default nextConfig;
