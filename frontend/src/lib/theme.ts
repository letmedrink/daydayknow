/** macOS-inspired design tokens — high-contrast variant */
export const theme = {
  // 背景
  bg: {
    window: '#f0f0f3',
    sidebar: '#e8e8ec',
    content: '#ffffff',
    raised: '#f5f5f7',
    header: '#f8f8fa',
    overlay: 'rgba(0,0,0,0.06)',
    accent: '#f0f4ff',
  },
  // 文字
  text: {
    primary: '#1a1a1e',
    secondary: '#636366',
    tertiary: '#98989d',
    inverse: '#ffffff',
  },
  // 边框
  border: {
    light: '#d5d5d9',
    medium: '#c2c2c7',
    focus: '#007AFF',
  },
  // 强调色
  accent: '#007AFF',
  accentHover: '#0066dd',
  accentBg: 'rgba(0,122,255,0.08)',
  // 危险
  danger: '#FF3B30',
  // 成功
  success: '#34C759',
  // 警告
  warning: '#FF9500',
  // 圆角
  radius: {
    sm: 6,
    md: 10,
    lg: 14,
  },
  // 阴影
  shadow: {
    sm: '0 1px 4px rgba(0,0,0,0.08)',
    md: '0 3px 12px rgba(0,0,0,0.1)',
    lg: '0 8px 28px rgba(0,0,0,0.14)',
  },
  // 字体
  font: "-apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Helvetica Neue', Arial, sans-serif",
  fontMono: "'SF Mono', 'Menlo', 'Monaco', 'Consolas', monospace",
} as const;
