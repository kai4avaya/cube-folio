# Cubic Portfolio — Kai Kleinbard

Interactive 3D Escher isometric portfolio built with Three.js, WebGL, and real-time Image-to-3D multi-stratum dioramas.

- **Live Site**: https://cube.kaik.space/
- **GitHub Repo**: https://github.com/kai4avaya/cube-folio

---

## Google Analytics (GA4) Setup

All portfolio sites share a **single GA4 Property and Measurement ID** so traffic can be viewed both combined and broken down by hostname/path (`cube.kaik.space`, `kaik.space`, `cre8ture.github.io/*`, `kai4avaya.github.io/*`).

- **GA4 Property**: `Kai Portfolio` (`properties/565841989`)
- **Measurement ID**: `G-NVX0XJGFFL`
- **GTM Container ID (optional)**: `GTM-WB524F2N`

### Option 1: One-Line Shared Script (Recommended for New Sites)

Drop this single line inside `<head>` of any portfolio site:

```html
<script defer src="https://cube.kaik.space/analytics.js"></script>
```

The shared loader lives in [`analytics.js`](./analytics.js) and automatically skips tracking on local `file://` opens.

### Option 2: Standard Inline GA4 Tag

If you prefer a self-contained snippet with zero external dependency on `cube.kaik.space`:

```html
<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-NVX0XJGFFL"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-NVX0XJGFFL');
</script>
```

### Custom Events Tracked on `cube.kaik.space`

In addition to GA4 Enhanced Measurement (pageviews, scrolls, outbound clicks, video plays):

- `inspect_cube` — fired when opening a project cube (`project_id`, `project_title`)
- `launch_project` — fired when clicking **Launch Live Project** (`project_id`, `project_title`, `project_url`)
- `toggle_list_flow` — fired when switching between Escher Lattice and List Flow (`view_mode`)

### Querying Analytics via MCP (Antigravity CLI)

`analytics-mcp` is configured globally in `~/.gemini/config/mcp_config.json` (read-only Viewer access to property `565841989`). Run `/mcp` in Antigravity CLI to confirm it's connected, then ask questions like:

- *"Show me pageviews by hostname and page path for property 565841989 over the last 7 days."*
- *"Which cubes got the most `inspect_cube` events this week?"*

---

## Security Notes

- **Safe to keep public**: Your GA4 Measurement ID (`G-NVX0XJGFFL`), GTM ID (`GTM-WB524F2N`), and Property ID (`565841989`) are client-side identifiers exposed on every website in browser DevTools. They can only send events — they cannot read reports or modify your Analytics account.
- **Keep private (never commit)**: Your Google Cloud Service Account JSON key is stored outside this repo at `~/.config/google-analytics/` (`chmod 600`) with read-only **Viewer** access, and `.gitignore` blocks credential JSON patterns from being committed here.
