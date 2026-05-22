import markdownit from "markdown-it";

import { prepareDisplay } from "./json-display";

export type MessageBlock = { kind: "html"; html: string } | { kind: "json"; value: unknown };

interface RenderEnv {
  jsonStore: unknown[];
}

// Matches the placeholder tags we emit for json fences, capturing the index.
const PLACEHOLDER_SPLIT = /<div data-vjson="(\d+)"><\/div>/;

const md = markdownit({ html: false, linkify: false, typographer: false });

md.renderer.rules.fence = (tokens, idx, _options, env, _self) => {
  const mdEnv = env as RenderEnv;
  const token = tokens[idx];
  const lang = (token.info ?? "").trim().split(/\s+/)[0];

  if (lang === "json") {
    const display = prepareDisplay(token.content.trim());
    if (display.isJson) {
      const i = mdEnv.jsonStore.length;
      mdEnv.jsonStore.push(display.parsed);
      return `<div data-vjson="${i}"></div>`;
    }
  }

  // Fall back to standard pre/code rendering for all other fences (and malformed json).
  const escaped = md.utils.escapeHtml(token.content);
  const langClass = lang ? ` class="language-${md.utils.escapeHtml(lang)}"` : "";
  return `<pre><code${langClass}>${escaped}</code></pre>\n`;
};

/**
 * Render a joined message text as an ordered list of display blocks.
 *
 * - Regular Markdown → { kind: "html", html }
 * - ```json fences with valid object/array content → { kind: "json", value }
 * - Malformed json fences and all other fences → rendered as html code blocks
 * - Bare JSON strings (no fences) are treated as plain Markdown text — no special handling
 */
export function renderMessage(text: string): MessageBlock[] {
  if (!text.trim()) return [];

  // If the entire message is a bare JSON object or array, render it directly
  // without requiring fenced syntax.
  const wholeCheck = prepareDisplay(text.trim());
  if (wholeCheck.isJson) {
    return [{ kind: "json", value: wholeCheck.parsed }];
  }

  const env: RenderEnv = { jsonStore: [] };
  const rendered = md.render(text, env as object);

  const parts = rendered.split(PLACEHOLDER_SPLIT);
  const blocks: MessageBlock[] = [];

  for (let i = 0; i < parts.length; i++) {
    if (i % 2 === 0) {
      const html = parts[i];
      if (html.trim()) blocks.push({ kind: "html", html });
    } else {
      blocks.push({ kind: "json", value: env.jsonStore[parseInt(parts[i], 10)] });
    }
  }

  return blocks;
}
