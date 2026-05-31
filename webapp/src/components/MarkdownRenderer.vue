<script setup lang="ts">
defineProps<{
  html: string;
}>();
</script>

<template>
  <!-- eslint-disable-next-line vue/no-v-html -->
  <div class="md-body" v-html="html" />
</template>

<style scoped>
.md-body {
  color: var(--text);
  font-family: var(--ui);
  font-size: 0.98rem;
  line-height: 1.7;
  min-width: 0;
}

/* Block spacing */
.md-body :deep(p),
.md-body :deep(ul),
.md-body :deep(ol),
.md-body :deep(blockquote),
.md-body :deep(pre),
.md-body :deep(table) {
  margin: 0 0 0.85em 0;
}

.md-body :deep(p:last-child),
.md-body :deep(ul:last-child),
.md-body :deep(ol:last-child),
.md-body :deep(blockquote:last-child),
.md-body :deep(pre:last-child),
.md-body :deep(table:last-child) {
  margin-bottom: 0;
}

/* Headings (infrequent in chat, but handle gracefully) */
.md-body :deep(h1),
.md-body :deep(h2),
.md-body :deep(h3),
.md-body :deep(h4),
.md-body :deep(h5),
.md-body :deep(h6) {
  font-family: var(--display);
  color: var(--text);
  line-height: 1.2;
  margin: 1em 0 0.4em 0;
  font-weight: 600;
}

.md-body :deep(h1) { font-size: 1.25rem; }
.md-body :deep(h2) { font-size: 1.1rem; }
.md-body :deep(h3) { font-size: 1rem; }
.md-body :deep(h4),
.md-body :deep(h5),
.md-body :deep(h6) { font-size: 0.95rem; }

/* Lists */
.md-body :deep(ul),
.md-body :deep(ol) {
  padding-left: 1.5em;
}

.md-body :deep(li) {
  margin-bottom: 0.2em;
}

.md-body :deep(li:last-child) {
  margin-bottom: 0;
}

/* Inline code */
.md-body :deep(code) {
  font-family: var(--mono);
  font-size: 0.84em;
  background: rgba(255, 255, 255, 0.07);
  border: 1px solid var(--border-muted);
  border-radius: 4px;
  padding: 0.1em 0.35em;
  color: var(--accent);
  word-break: break-word;
}

/* Code blocks (non-json fences, or malformed json fences) */
.md-body :deep(pre) {
  background: rgba(7, 10, 16, 0.9);
  border: 1px solid var(--border-muted);
  border-radius: var(--radius-sm);
  padding: 12px 14px;
  overflow-x: auto;
}

.md-body :deep(pre) > :deep(code) {
  background: transparent;
  border: none;
  padding: 0;
  font-size: 0.82rem;
  color: var(--text-dim);
  word-break: normal;
}

/* Blockquote */
.md-body :deep(blockquote) {
  border-left: 3px solid var(--accent-border);
  margin-left: 0;
  padding: 4px 0 4px 14px;
  color: var(--text-dim);
}

.md-body :deep(blockquote p) {
  margin: 0;
}

/* Links */
.md-body :deep(a) {
  color: var(--accent);
  text-decoration: underline;
  text-underline-offset: 2px;
}

.md-body :deep(a:hover) {
  color: var(--accent-strong);
}

/* Horizontal rule */
.md-body :deep(hr) {
  border: none;
  border-top: 1px solid var(--border-muted);
  margin: 1em 0;
}

/* Table */
.md-body :deep(table) {
  border-collapse: collapse;
  width: 100%;
  font-size: 0.88rem;
}

.md-body :deep(th),
.md-body :deep(td) {
  border: 1px solid var(--border-muted);
  padding: 6px 10px;
  text-align: left;
}

.md-body :deep(th) {
  background: rgba(255, 255, 255, 0.04);
  color: var(--text-dim);
  font-weight: 600;
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

/* Strong / Em */
.md-body :deep(strong) {
  color: var(--text);
  font-weight: 600;
}

.md-body :deep(em) {
  color: var(--text-dim);
}
</style>
