// frontend/src/lib/theme.ts
// MCP unavailable — using locked token values from CONTEXT.md (Figma source of truth)
// Tokens: dark blue #06004f, green #399e5a, button blue #00006b, Rubik font, 16px/8px radius
import type { ThemeConfig } from 'antd';

export const mamiTheme: ThemeConfig = {
  token: {
    colorPrimary: '#06004f',          // DSC dark blue
    colorSuccess: '#399e5a',          // DSC green
    colorLink: '#399e5a',
    fontFamily: "'Rubik', -apple-system, BlinkMacSystemFont, sans-serif",
    borderRadius: 8,                  // choice cards, buttons
    borderRadiusLG: 16,               // panels, large cards
    colorBgLayout: 'rgba(57,158,90,0.1)',
    colorBgContainer: '#ffffff',
    colorText: '#06004f',
  },
  components: {
    Button: {
      colorPrimary: '#00006b',
      borderRadius: 8,
      controlHeight: 44,
    },
    Input: {
      controlHeight: 44,
      borderRadius: 8,
    },
    Layout: {
      bodyBg: 'rgba(57,158,90,0.1)',
    },
    Card: {
      borderRadiusLG: 16,
    },
    Form: {
      labelColor: '#06004f',
    },
  },
};
