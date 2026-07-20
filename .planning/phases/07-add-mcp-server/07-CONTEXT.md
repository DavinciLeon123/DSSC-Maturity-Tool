# Phase 7: Implement Figma Design - Context

**Gathered:** 2026-03-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Restyle all existing frontend screens to match the production Figma design (colors, typography, layout, components). Also add the public landing page ("Start pagina") that doesn't yet exist. The compliance report is backend-generated HTML — out of scope. Backend logic, API calls, state management, and routing are not changed.

</domain>

<decisions>
## Implementation Decisions

### Navigation pattern
- **Replace the left sidebar with a top navbar** matching the Figma header exactly: CoE DSC logo (left) + hamburger icon + "Menu" text (right)
- Hamburger click opens a drawer/panel containing the same nav links as the current sidebar: Dashboard, My Initiative, Questionnaire, About, Admin (role-gated)
- The user will provide the CoE DSC logo file — it should be placed in frontend/public/ or frontend/src/assets/
- Top navbar applies to all authenticated screens (inside the `_app.tsx` shell)

### Background
- All authenticated screens get the light green-tinted background from Figma: `linear-gradient(90deg, rgba(57, 158, 90, 0.1) 0%, rgba(57, 158, 90, 0.1) 100%), white`
- Applied at the `_app.tsx` shell level so all inner routes inherit it automatically

### Public landing page
- **Implement the full "Start pagina"** as the app's home route (`/`) — replaces the current redirect-to-login behavior at root
- Implement **all sections** as shown in Figma: hero (title + subtitle + 2 CTA buttons), feature cards section, info section, footer
- Footer (dark navy, social links, Contact/Privacy/Newsletter) appears on **public pages only** (landing page, and optionally login/register) — NOT on authenticated app screens
- CTA buttons on landing page link to `/login` (primary) and `/register` (secondary)

### Answer option labels
- Change "Not there yet" → **"Not yet, but planning to"** in the UI across all questionnaire components
- Backend value stays `NOT_THERE_YET` — label change is UI only (display strings in AnswerButtonGroup.tsx)

### Styling approach
- **antd components + inline style objects** — no Tailwind
- Use antd `ConfigProvider` with a `ThemeConfig` for global tokens (colorPrimary, fontFamily, borderRadius)
- Figma values extracted from MCP are converted to antd token overrides and inline style props
- No new CSS libraries or build dependencies

### Design tokens (from Figma MCP)
- Dark blue: `#06004f` (DSC dark blue — primary text, borders, headings)
- Green: `#399e5a` (choice card borders, accents, progress indicators)
- Button blue: `#00006b`
- Question chip background: `rgba(61, 82, 213, 0.16)`
- Font: **Rubik** (Regular 400, Medium 500, SemiBold 600) — load via Google Fonts or local
- Card border-radius: `16px` (panels), `8px` (choice cards, buttons)
- Choice card: white bg, `1px solid #399e5a`, `p-32px`, `rounded-8px`

### Claude's Discretion
- Exact drawer/menu animation and open/close behavior
- Login and register screen layout (Figma does not show these screens — apply design tokens, Rubik font, and navy/white color scheme)
- Mobile responsiveness (Figma is 1728px wide — implement as-is, basic responsiveness optional)
- Admin panel screen (Figma does not show it — apply design tokens only)

</decisions>

<specifics>
## Specific Ideas

- Figma URL: https://www.figma.com/design/V3v7Oq6DfXMpQ86llyVCQ0/MAMI-tool?node-id=81-1464
- Questionnaire screen (Vragen flow / 1, node 81:1568) is the most detailed Figma screen — primary reference
- Progress indicator: left panel with "Your progress" heading, progress items (done=green circle+checkmark, current=navy filled circle, pending=empty circle outline), sub-items with vertical line connector
- Question card: white panel (`rounded-16px`), topic heading (H3, `#06004f`), "Question X of Y" chip (purple-tinted pill), question text, 3 choice cards vertically stacked
- Previous/Next buttons: outlined style, `1px solid #06004f`, navy text, `rounded-8px`, `px-24px py-12px`

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/src/routes/_app.tsx`: App shell layout — currently renders `<Sidebar />` + `<main>`. Replace Sidebar import with top navbar, update layout to `flex-col` instead of `flex-row`
- `frontend/src/components/layout/Sidebar.tsx`: Contains nav items array, admin role check, logout handler — reuse this logic in the new top navbar drawer
- `frontend/src/components/questionnaire/AnswerButtonGroup.tsx`: Contains the 3-option answer buttons — update display labels here
- `frontend/src/routes/_auth/login.tsx` and `register.tsx`: Auth screens — apply Rubik font and dark navy background from existing CSS vars

### Established Patterns
- Inline `style={{}}` objects are the current styling pattern — continue this for new code
- `authStore.isAuthenticated()` used in `_app.tsx` `beforeLoad` guard — do not change
- `api.get()` pattern for all API calls — do not change

### Integration Points
- `frontend/src/routes/__root.tsx` and `frontend/src/routes/_auth/index.tsx`: The root route currently redirects to `/login`. Adding `/` as a public landing page requires a new route file
- `frontend/src/main.tsx`: Where `ConfigProvider` will be added for antd theme tokens
- Logo file: user will provide — should go to `frontend/src/assets/` or `frontend/public/`

</code_context>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 07-add-mcp-server (Implement Figma Design)*
*Context gathered: 2026-03-07*
