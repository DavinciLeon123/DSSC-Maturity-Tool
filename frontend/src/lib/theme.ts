// frontend/src/lib/theme.ts
// DSSC brand tokens: Blue #008ecf (primary), Green #76b82a (secondary), Jost typography
import type { ThemeConfig } from 'antd';

export const mamiTheme: ThemeConfig = {
  token: {
    colorPrimary: '#008ecf',          // DSSC Blue
    colorSuccess: '#76b82a',          // DSSC Green
    colorLink: '#76b82a',
    fontFamily: "'Jost', 'Helvetica Neue', Arial, sans-serif",
    borderRadius: 8,                  // choice cards, buttons
    borderRadiusLG: 16,               // panels, large cards
    colorBgLayout: '#ffffff',
    colorBgContainer: '#ffffff',
    colorText: '#1c2025',
  },
  components: {
    Button: {
      colorPrimary: '#008ecf',
      borderRadius: 0,
      controlHeight: 44,
    },
    Input: {
      controlHeight: 44,
      borderRadius: 8,
    },
    Layout: {
      bodyBg: '#ffffff',
    },
    Card: {
      borderRadiusLG: 0,
    },
    Form: {
      labelColor: '#008ecf',
    },
  },
};
