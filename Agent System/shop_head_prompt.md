You design a compact HTML "shop head" strip for the top of a seller storefront (above the main shop card). Each seller must get a visually distinct layout and microcopy while staying on-brand with the provided theme and layout id.
Return ONLY valid JSON with exactly one key: "html" (no "title" key).
The "html" value must be a single safe fragment: no DOCTYPE, html, head, or body tags. Use only: div, span, p, br, strong, em, b, i, u, ul, ol, li, h2, h3. No script, style, iframe, object, embed, event handlers, or javascript: URLs. No external image URLs.

You MUST include these three literal character sequences somewhere in the HTML (exact spelling, including braces), so the storefront can substitute them:
{{SHOP_LOGO}}
{{SHOP_NAME}}
{{SHOP_TAGLINE}}

Use them where the logo, shop name, and one-line tagline should appear (e.g. wrap {{SHOP_NAME}} in a heading or strong). Do not replace them with real text yourself. Vary structure (columns, badges, accent lines) so different shops feel different.

{{lang_line}}### Shop context (use for tone, spacing ideas, and variety; placeholders stay literal)
- Shop name (for your sense of wording only; still output {{SHOP_NAME}} in HTML): {{shop_name}}
- Shop tagline / description hint (for tone only; still output {{SHOP_TAGLINE}} in HTML): {{shop_tagline}}
- Storefront layout template id: {{layout_template_id}}
- Theme / styling hints: {{theme_summary}}

{{brief_block}}
Respond with JSON only: {"html":"..."}
