// frontend/src/lib/theme.ts
// DSSC brand tokens: Blue #008ecf (primary), Green #76b82a (secondary), Jost+Open Sans typography
import type { ThemeConfig } from 'antd';

export const mamiTheme: ThemeConfig = {
  token: {
    colorPrimary: '#008ecf',          // DSSC Blue
    colorSuccess: '#76b82a',          // DSSC Green
    colorLink: '#76b82a',
    fontFamily: "'Open Sans', -apple-system, BlinkMacSystemFont, sans-serif",
    borderRadius: 8,                  // choice cards, buttons
    borderRadiusLG: 16,               // panels, large cards
    colorBgLayout: '#ffffff',
    colorBgContainer: '#ffffff',
    colorText: '#008ecf',
  },
  components: {
    Button: {
      colorPrimary: '#008ecf',
      borderRadius: 8,
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
      borderRadiusLG: 16,
    },
    Form: {
      labelColor: '#008ecf',
    },
  },
};
