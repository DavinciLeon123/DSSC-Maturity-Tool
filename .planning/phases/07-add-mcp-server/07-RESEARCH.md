# Phase 7: Implement Figma Design - Research

**Researched:** 2026-03-06
**Domain:** Frontend design implementation — Figma → React/antd v6 theming and screen-by-screen rebuild
**Confidence:** HIGH (stack well-understood; Figma content unverifiable without MCP access)

---

## Summary

Phase 7 implements the production Figma design on a React 19 + Vite + TanStack Router + Ant Design v6 frontend. The existing codebase uses raw inline `style={{}}` objects throughout — no antd components are currently used despite antd v6 being installed. The Figma design is at a private URL that requires authentication; its exact contents cannot be read without Figma MCP or user-provided screenshots/tokens. All CSS theming decisions must therefore be extracted by the user manually from Figma Dev Mode during each screen session.

The implementation strategy is: (1) establish a single antd v6 `ConfigProvider` theme at the root with project brand tokens, (2) migrate each screen one at a time in collaborative sessions, replacing inline styles with antd components styled via the theme token system, (3) keep the existing CSS custom properties in `globals.css` as a bridge until all screens are migrated.

**Primary recommendation:** Set up the `ConfigProvider` theme in `main.tsx` first (Session 0), then tackle screens in login → app-shell → dashboard → initiative → questionnaire-wizard → admin order. Use antd component tokens + CSS custom properties — not CSS modules, not styled-components.

---

## Standard Stack

### Core (already installed, no new installs needed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| antd | ^6.3.0 | Component library + design token system | Already installed; provides ConfigProvider, Button, Form, Layout, Menu etc. |
| React | ^19.2.0 | UI framework | Project baseline |
| @tanstack/react-router | ^1.160.0 | Routing | Project baseline |
| @tanstack/react-query | ^5.90.21 | Server state | Already used in Sidebar |

### Supporting (no new installs unless Figma MCP is connected)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| @ant-design/icons | ^6.x | Icon set | Only if Figma design uses icons from this set; install if needed |
| @ant-design/static-style-extract | latest | Zero-runtime SSR static CSS extraction | Only if switching to `zeroRuntime: true` for production; NOT needed for this phase |

**No new npm packages required** for the core design implementation. antd v6 is already installed and ships its full component + token system.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| antd tokens + ConfigProvider | CSS Modules (.module.css) | CSS Modules give full control but lose antd component tokens; creates parallel systems |
| antd tokens + ConfigProvider | styled-components | Heavy install, no antd v6 integration benefit, adds bundle weight |
| antd tokens + ConfigProvider | Tailwind CSS | Antd + Tailwind class conflicts; would need `important: true` workaround; out of scope |

**Installation (if icons needed):**
```bash
cd frontend && npm install @ant-design/icons
```

---

## Architecture Patterns

### Recommended Project Structure (additions only)

```
frontend/src/
├── styles/
│   └── globals.css          # Existing — keep brand CSS vars as bridge
├── lib/
│   └── theme.ts             # NEW — antd ThemeConfig export (single source of truth)
├── main.tsx                 # Add ConfigProvider wrapper here
├── routes/
│   ├── _auth/               # login, register, forgot-password, reset-password
│   └── _app/                # dashboard, initiative, questionnaire, admin, about
└── components/
    ├── layout/
    │   └── Sidebar.tsx      # Rebuild with antd Menu component
    └── questionnaire/       # Rebuild wizard cards with antd Card/Steps
```

### Pattern 1: Centralized Theme Token File

**What:** Export a single `ThemeConfig` object from `src/lib/theme.ts`. Import it in `main.tsx` and pass to `ConfigProvider`.

**When to use:** Always. Single source of truth for all brand colors/fonts.

**Example:**
```typescript
// src/lib/theme.ts
import type { ThemeConfig } from 'antd';

export const mamiTheme: ThemeConfig = {
  token: {
    // Seed tokens — antd derives the full palette from these
    colorPrimary: '#020059',      // --color-navy (current brand primary)
    colorSuccess: '#41A765',      // --color-green
    colorLink: '#41A765',
    fontFamily: "'Rubik', -apple-system, BlinkMacSystemFont, sans-serif",
    borderRadius: 6,              // --border-radius-sm
    colorBgLayout: '#F5F5F8',     // --color-bg-light
    colorText: '#4A495B',         // --color-text-gray
  },
  components: {
    // Per-component overrides go here as discovered during Figma sessions
    Button: {
      borderRadius: 30,           // --border-radius-lg for primary CTAs
    },
    Menu: {
      colorItemBg: 'transparent',
      colorItemText: 'rgba(255,255,255,0.8)',
      colorItemTextSelected: '#41A765',
      colorItemBgSelected: 'rgba(255,255,255,0.08)',
    },
  },
};
```

**Note:** Figma may specify different colors than the current CSS vars. Update this file during each screen session when Figma values are extracted. The CSS vars in `globals.css` remain as fallback until all screens are migrated.

### Pattern 2: ConfigProvider in main.tsx

**What:** Wrap the entire app in `ConfigProvider` with the theme.

**Example:**
```typescript
// main.tsx
import { ConfigProvider } from 'antd';
import { mamiTheme } from './lib/theme';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ConfigProvider theme={mamiTheme}>
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>
    </ConfigProvider>
  </StrictMode>,
);
```

### Pattern 3: antd Layout for App Shell

**What:** Replace the manual `display: flex` app shell in `_app.tsx` with antd `Layout`, `Sider`, and `Content`.

**Example:**
```typescript
import { Layout } from 'antd';
const { Sider, Content } = Layout;

function AppLayout() {
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider width={240} style={{ background: 'var(--color-navy)' }}>
        <Sidebar />
      </Sider>
      <Content style={{ padding: '2rem', background: '#F5F5F8' }}>
        <Outlet />
      </Content>
    </Layout>
  );
}
```

### Pattern 4: antd Form for Auth Screens

**What:** Replace raw `<form>` and `<input>` elements in login/register with antd `Form`, `Form.Item`, `Input`, `Button`.

**When to use:** All auth screens (login, register, forgot-password, reset-password).

**Example:**
```typescript
import { Form, Input, Button } from 'antd';

<Form onFinish={handleSubmit} layout="vertical">
  <Form.Item name="email" label="Email" rules={[{ required: true, type: 'email' }]}>
    <Input />
  </Form.Item>
  <Form.Item name="password" label="Password" rules={[{ required: true }]}>
    <Input.Password />
  </Form.Item>
  <Button type="primary" htmlType="submit" block loading={loading}>
    Sign In
  </Button>
</Form>
```

### Pattern 5: Consuming Tokens in Custom Components

**What:** Use `theme.useToken()` hook to access resolved token values inside custom components.

**When to use:** When you need to apply brand colors inside components that aren't antd components (e.g., status badges, custom callouts).

**Example:**
```typescript
import { theme } from 'antd';

function ContextCallout({ text }: { text: string }) {
  const { token } = theme.useToken();
  return (
    <div style={{
      background: token.colorPrimaryBg,
      borderLeft: `4px solid ${token.colorPrimary}`,
      padding: token.paddingMD,
      borderRadius: token.borderRadius,
    }}>
      {text}
    </div>
  );
}
```

### Anti-Patterns to Avoid

- **Mixing CSS vars and antd tokens on the same component:** Pick one system per component. Use antd tokens for antd components; use CSS vars only in `globals.css` as global bridge.
- **Overriding antd with `.ant-*` CSS class selectors:** Fragile, breaks across antd versions. Use `components` override in ThemeConfig or `style` prop.
- **Creating CSS Modules for every screen:** Adds a parallel styling system. Prefer antd component props + ThemeConfig for consistent design.
- **Setting `zeroRuntime: true` now:** Requires importing `antd/dist/antd.css` and static style extraction — adds complexity with no benefit at this phase. Leave as default (runtime CSS-in-JS).

---

## How to Read Figma Without MCP

The Figma design URL (`https://www.figma.com/design/V3v7Oq6DfXMpQ86llyVCQ0/MAMI-tool?node-id=81-1464&m=dev`) requires authentication. WebFetch returns 403. The Figma MCP server is not connected.

### Manual Extraction Protocol (per screen session)

During each collaborative screen session, the user must open the Figma file and provide values. Here is the extraction checklist:

**For each screen, extract from Figma Dev Mode (Shift+D in Figma):**

1. **Colors** — Select the frame/component → inspect panel shows fill colors as hex. Note: background, text, border, button colors.
2. **Typography** — Select any text element → inspect panel shows font family, weight, size, line height, letter spacing.
3. **Spacing** — Select a container → inspect panel shows padding, gap (in px).
4. **Border radius** — Inspect shows `border-radius` value per element.
5. **Shadows** — Inspect shows `box-shadow` with blur/spread/color values.
6. **Right-click → Copy/Paste as → Copy as CSS** — For full CSS snippet of selected element.

**URL pattern for specific screens:**
The Figma node-id `81-1464` is the starting frame. Other screens likely have different node IDs. The user navigates to each screen in Figma and notes the node-id from the URL bar (`?node-id=XX-YYYY`).

**What to hand Claude during each session:**
- Screenshots of the screen from Figma (Claude can read images)
- OR the CSS block from Copy as CSS
- OR a text list of: background color, text color, button color, font size, padding

**If Figma MCP becomes available mid-phase:** Use `mcp__figma__*` tools to query node properties directly. The ThemeConfig structure would remain the same; only the value extraction becomes automated.

---

## Screens to Implement and Recommended Order

Based on the existing routes and standard MAMI tool patterns (login → authenticated app → questionnaire):

### Implementation Order

| Priority | Screen | Route | Complexity | Why This Order |
|----------|--------|-------|------------|----------------|
| 0 | Theme setup | `main.tsx` + `lib/theme.ts` | Low | Enables all subsequent work |
| 1 | Login | `/_auth/login` | Low | Entry point, self-contained, visible immediately |
| 2 | Register | `/_auth/register` | Low | Same card layout as login |
| 3 | Forgot / Reset Password | `/_auth/forgot-password`, `/_auth/reset-password` | Low | Same card layout |
| 4 | App shell + Sidebar | `/_app.tsx` + `Sidebar.tsx` | Medium | Affects all authenticated screens |
| 5 | Dashboard | `/_app/dashboard` | Medium | First screen after login |
| 6 | My Initiative | `/_app/initiative` | Medium | Initiative registration form |
| 7 | Questionnaire Wizard | `/_app/questionnaire` + components | High | Most complex, most components |
| 8 | Admin Panel | `/_app/admin` | Medium | Admin-only, isolated |
| 9 | About | `/_app/about` | Low | Static content |

**Rationale:** Auth screens share a card-on-dark-background layout — doing them together saves rework. App shell comes before inner screens because the sidebar layout wraps everything. Questionnaire is last authenticated screen because it has 9 components (`WizardPage`, `QuestionCard`, `AnswerButtonGroup`, `StepPills`, `ContextCallout`, `FollowupPanel`, `FindingsPanel`, `EvidenceInput`).

---

## Ant Design v6 Theming: Key Facts

**Confidence: HIGH** (verified via official docs, GitHub source, release notes)

### Token Hierarchy

```
Seed Tokens (you set these)
    ↓ antd algorithm derives →
Map Tokens (color palettes, computed values)
    ↓ antd maps to →
Alias Tokens (component-specific names like colorBgContainer)
    ↓ used by →
Component Tokens (per-component overrides via components: {})
```

**You only need to set Seed Tokens** (`colorPrimary`, `fontFamily`, `borderRadius`, `colorSuccess`, etc.). antd generates the full 10-step color palette automatically.

### Seed Tokens Relevant to MAMI Brand

| Token | Current Brand Value | Purpose |
|-------|---------------------|---------|
| `colorPrimary` | `#020059` (navy) | Primary buttons, links, active states |
| `colorSuccess` | `#41A765` (green) | Success states, positive badges |
| `colorLink` | `#41A765` (green) | Link color |
| `fontFamily` | `'Rubik', sans-serif` | All text |
| `borderRadius` | `6` | Default component rounding |
| `colorBgLayout` | `#F5F5F8` | Page background (behind Content) |
| `colorText` | `#4A495B` | Default text color |
| `colorBgContainer` | `#ffffff` | Card/container backgrounds |

**Note:** Figma may reveal different hex values. Update `lib/theme.ts` accordingly.

### v6-Specific Considerations

- **CSS Variables by default:** antd v6 uses `@layer antd` and pure CSS variables mode. This means theme changes propagate without page reload.
- **zeroRuntime:** Available but NOT recommended for this phase. Default (runtime CSS-in-JS) is simpler and works without any style import changes.
- **React 19 support:** antd v6 officially supports React 18+, recommends React 19. The project is on React 19 — no compatibility shims needed. Remove any `@ant-design/v5-patch-for-react-19` import if present.
- **No IE support:** Not a concern for this project.
- **@ant-design/icons must match:** If icons are added, use `@ant-design/icons@6` (not v5).

### Component-Level Overrides

The `components` key in ThemeConfig accepts per-component token overrides. Useful tokens:

```typescript
components: {
  Button: {
    colorPrimary: '#020059',
    borderRadius: 30,        // pill buttons
    controlHeight: 44,       // taller buttons
  },
  Input: {
    controlHeight: 44,
    borderRadius: 6,
  },
  Layout: {
    siderBg: '#020059',
    bodyBg: '#F5F5F8',
  },
  Menu: {
    darkItemBg: '#020059',
    darkItemSelectedBg: 'rgba(255,255,255,0.08)',
    darkItemSelectedColor: '#41A765',
  },
  Form: {
    labelColor: '#020059',
    labelFontSize: 14,
  },
}
```

---

## CSS Strategy Decision

**Use: antd tokens via ConfigProvider + minimal CSS custom properties in globals.css**

Do NOT use CSS Modules. Do NOT use styled-components.

**Reasoning:**
- The project currently uses inline `style={{}}` objects everywhere. Moving to antd components with token-driven props is a direct upgrade path with no new file types or build configuration.
- CSS Modules would add `.module.css` files for every screen — a parallel system that doesn't integrate with antd tokens.
- styled-components has no integration benefit with antd v6 and adds ~17KB gzip to bundle.
- The existing CSS custom properties in `globals.css` (`--color-navy`, `--color-green`, etc.) are a useful bridge: keep them during migration, remove when all screens are migrated.

**The pattern for each screen:**
1. Replace raw HTML elements (`<button>`, `<input>`, `<form>`) with antd components.
2. Let antd tokens handle color/size/font via ConfigProvider.
3. Use `style={{}}` only for layout overrides (margin, padding, display) that aren't available as component props.
4. Do NOT fight antd defaults with CSS selectors — adjust via the `token` or `components` keys in ThemeConfig.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Form validation | Custom error state + regex | `antd Form` with `rules` prop | Built-in required/email/custom validators, error display, accessibility |
| Loading states on buttons | `disabled` + custom spinner | `antd Button loading={true}` | Built-in spinner + disabled state |
| Navigation menu with active state | CSS class toggling | `antd Menu` with `selectedKeys` | Handles active highlight, keyboard nav, RTL |
| Sidebar layout | Manual `display:flex` with `width:240px` | `antd Layout.Sider` | Collapsible, responsive breakpoints built in |
| Table/list for admin | `<table>` HTML | `antd Table` | Sorting, pagination, expandable rows all built in |
| Notification/feedback | Custom toast div | `antd message` or `antd notification` | App-level singleton, stacks correctly |
| Step indicator | Manual StepPills component | `antd Steps` | Accessible, themeable, handles click navigation |

**Key insight:** The project already has antd v6 installed but uses zero antd components. Every raw HTML element in the current codebase is a candidate for replacement with an antd equivalent.

---

## Common Pitfalls

### Pitfall 1: antd component styles not matching Figma because seed tokens are wrong

**What goes wrong:** Button looks blue (antd default `#1677ff`) instead of navy (`#020059`).
**Why it happens:** ConfigProvider not wrapping the component, or wrong `colorPrimary` value.
**How to avoid:** Wrap at the very top of `main.tsx` — before QueryClientProvider and RouterProvider. Verify in browser with `document.documentElement.style.getPropertyValue('--ant-color-primary')`.
**Warning signs:** Buttons/links still show the antd default blue.

### Pitfall 2: Figma uses a color that differs from existing CSS vars

**What goes wrong:** Figma shows `#0A0060` for navy but CSS var is `#020059`. Developer picks the wrong one.
**Why it happens:** Design evolved after the initial CSS vars were set.
**How to avoid:** Treat Figma as the source of truth. Update `lib/theme.ts` AND `globals.css` to match Figma values when they differ.
**Warning signs:** Side-by-side comparison between app and Figma screenshot shows color mismatch.

### Pitfall 3: Overriding antd component styles with `.ant-button {}` CSS selectors

**What goes wrong:** Selector works but breaks on antd minor version update, or conflicts with hashed class names.
**Why it happens:** Developers default to CSS overrides from muscle memory.
**How to avoid:** Always use `components: { Button: { ... } }` in ThemeConfig, or the component's `style`/`className` prop.
**Warning signs:** CSS file contains `.ant-` prefixed selectors.

### Pitfall 4: index.css overriding globals.css

**What goes wrong:** `index.css` (the Vite default, still present) sets `body { display: flex; place-items: center; }` which centers the whole app and disrupts layout.
**Why it happens:** It was left from the Vite scaffold and `globals.css` does not reset it.
**How to avoid:** Check `main.tsx` import order. `globals.css` is imported — confirm `index.css` is NOT imported in `main.tsx`. (Currently it is not imported in `main.tsx` — only `globals.css` is. Safe.)
**Warning signs:** App is vertically/horizontally centered incorrectly.

### Pitfall 5: Figma MCP unavailable — no way to inspect node values programmatically

**What goes wrong:** Can't auto-extract colors, spacing, font sizes from Figma during implementation.
**Why it happens:** MCP server not connected.
**How to avoid:** Plan for manual extraction per the protocol above. Use Figma's built-in Dev Mode inspect panel. Accept screenshots from user as the primary design artifact per screen. If MCP becomes available, the ThemeConfig approach is compatible — MCP just speeds up extraction.
**Warning signs:** Implementation stalls waiting for automated Figma access.

### Pitfall 6: Questionnaire wizard components have complex state — antd migration risks regression

**What goes wrong:** Replacing `WizardPage` internals with antd components breaks answer saving, forward-blocking, or autosave badge.
**Why it happens:** Logic is coupled to inline style rendering.
**How to avoid:** Migrate wizard components last (priority 7). During migration, change only visual markup — not state logic or event handlers. Test each wizard step manually after migration.
**Warning signs:** Autosave badge disappears, Next button always enabled, answers not saving.

---

## Code Examples

Verified patterns from official sources:

### Theme setup (Session 0)

```typescript
// src/lib/theme.ts
import type { ThemeConfig } from 'antd';

export const mamiTheme: ThemeConfig = {
  token: {
    colorPrimary: '#020059',
    colorSuccess: '#41A765',
    colorLink: '#41A765',
    fontFamily: "'Rubik', -apple-system, BlinkMacSystemFont, sans-serif",
    borderRadius: 6,
    colorBgLayout: '#F5F5F8',
    colorText: '#4A495B',
    colorBgContainer: '#ffffff',
  },
};
```

```typescript
// main.tsx — add ConfigProvider import + wrapper
import { ConfigProvider } from 'antd';
import { mamiTheme } from './lib/theme';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ConfigProvider theme={mamiTheme}>
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>
    </ConfigProvider>
  </StrictMode>,
);
```

### Login screen (antd Form pattern)

```typescript
// _auth/login.tsx — replaces raw form
import { Form, Input, Button, Card, Typography, Alert } from 'antd';
const { Title, Text } = Typography;

function LoginPage() {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onFinish = async (values: { email: string; password: string }) => {
    setLoading(true);
    // ... existing fetch logic
  };

  return (
    <div style={{ minHeight: '100vh', background: 'var(--color-navy)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '2rem' }}>
      <Card style={{ width: 420 }}>
        {error && <Alert message={error} type="error" style={{ marginBottom: 16 }} />}
        <Form form={form} onFinish={onFinish} layout="vertical">
          <Form.Item name="email" label="Email" rules={[{ required: true, type: 'email' }]}>
            <Input size="large" />
          </Form.Item>
          <Form.Item name="password" label="Password" rules={[{ required: true }]}>
            <Input.Password size="large" />
          </Form.Item>
          <Button type="primary" htmlType="submit" block size="large" loading={loading}>
            Sign In
          </Button>
        </Form>
      </Card>
    </div>
  );
}
```

### Reading token values in custom components

```typescript
// Source: https://ant.design/docs/react/customize-theme/
import { theme } from 'antd';

function MyBadge({ label }: { label: string }) {
  const { token } = theme.useToken();
  return (
    <span style={{
      background: token.colorSuccessBg,
      color: token.colorSuccess,
      padding: `${token.paddingXXS}px ${token.paddingXS}px`,
      borderRadius: token.borderRadiusSM,
      fontSize: token.fontSizeSM,
    }}>
      {label}
    </span>
  );
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| antd CSS-in-JS hash injection | Pure CSS Variables + `@layer antd` | antd v6.0 (Nov 2025) | Styles apply without runtime overhead; theme switching without rebuild |
| `v5-patch-for-react-19` shim | No shim needed | antd v6.0 (Nov 2025) | Remove any `@ant-design/v5-patch-for-react-19` import if found |
| `less` variable override system | `ConfigProvider token` system | antd v5 (2023) | No LESS required; pure JS config |
| Figma "Copy as CSS" block | Dev Mode inspect panel with variable names | Figma 2024+ | Dev Mode shows variable names/tokens, not just raw hex values |

**Deprecated/outdated:**
- `antd/dist/reset.css`: Replaced by `App` component wrapper in antd v5+. Not needed unless using v4 patterns.
- LESS variable theming: Removed in v5+. The project doesn't use it — no action needed.
- `@ant-design/v5-patch-for-react-19`: Not found in project — confirm not present before completing Session 0.

---

## Open Questions

1. **Exact Figma color values**
   - What we know: Current CSS vars are `#020059` (navy), `#41A765` (green), `#3D52D5` (blue), `#4A495B` (text-gray), `#F5F5F8` (bg-light). Rubik font is already used.
   - What's unclear: Whether Figma uses the same values or updated ones. Whether the design introduces any new colors not in the current CSS vars.
   - Recommendation: User shares Figma screenshots or Dev Mode CSS export for the login screen in the first session. Update `lib/theme.ts` from those values.

2. **Which antd components to use for the questionnaire wizard step indicator**
   - What we know: Current `StepPills.tsx` is a custom component with inline styles.
   - What's unclear: Whether Figma shows a standard steps pattern (antd `Steps` component fits) or a custom pill design that must remain custom.
   - Recommendation: Show user the antd `Steps` component in the first questionnaire session and confirm match with Figma. If Figma shows a pill shape, use antd `Steps` with `type="inline"` or keep custom with token values.

3. **Figma MCP availability during execution**
   - What we know: Not connected as of research date.
   - What's unclear: Whether it will be connected before Phase 7 starts.
   - Recommendation: Plan for NO MCP (manual extraction per session). If MCP becomes available, use it to accelerate — the ThemeConfig + screen-by-screen approach is compatible regardless.

4. **Whether the Figma design has a completely different layout (e.g., top navigation instead of sidebar)**
   - What we know: node-id `81-1464` is the Figma starting frame. Layout specifics are unknown.
   - What's unclear: Whether the sidebar remains in the production design or is replaced.
   - Recommendation: Make this the first question in Session 0 (app shell session). Layout changes affect every screen; confirm before implementing any inner screen.

5. **Admin panel: does Figma include an admin design?**
   - What we know: Admin is an existing route `/admin` with 3 tabs.
   - What's unclear: Whether the Figma has admin screens or if admin is out of scope for the design implementation.
   - Recommendation: Ask user in scoping discussion before planning admin session.

---

## Sources

### Primary (HIGH confidence)
- https://github.com/ant-design/ant-design/blob/master/components/config-provider/context.ts — ThemeConfig interface structure (token, components, algorithm, zeroRuntime, cssVar)
- https://github.com/ant-design/ant-design/blob/master/docs/react/customize-theme.en-US.md — Seed/Map/Alias token hierarchy, ConfigProvider examples
- https://dev.to/zombiej/ant-design-60-is-released-bfa — antd v6 release notes (Nov 24 2025): React 18+ requirement, CSS vars default, zeroRuntime, smooth v5→v6 migration
- https://help.figma.com/hc/en-us/articles/15023124644247-Guide-to-Dev-Mode — Figma Dev Mode inspect panel usage for manual CSS extraction

### Secondary (MEDIUM confidence)
- https://ant.design/docs/react/migration-v6/ — v5→v6 migration notes (CSS vars, removed deprecated APIs, no compatibility package needed)
- https://ant.design/docs/react/css-variables/ — CSS Variables mode in antd v6
- Existing project files (`globals.css`, `main.tsx`, `Sidebar.tsx`, `login.tsx`) — current state of frontend styling

### Tertiary (LOW confidence)
- WebSearch results on antd ConfigProvider theme patterns — cross-referenced with official docs, elevated to MEDIUM where confirmed

---

## Metadata

**Confidence breakdown:**
- Standard stack (antd v6 ConfigProvider + token system): HIGH — verified from official source and release notes
- Figma extraction without MCP: HIGH (process) / LOW (actual design values — unverifiable without access)
- Implementation order: HIGH — based on dependency analysis of existing screen graph
- antd v6 + React 19 compatibility: HIGH — explicitly confirmed in v6 release notes
- Exact Figma color values: NOT RESEARCHED — blocked by Figma auth; extracted per-session

**Research date:** 2026-03-06
**Valid until:** 2026-06-06 (antd stable APIs; Figma Dev Mode process stable)
