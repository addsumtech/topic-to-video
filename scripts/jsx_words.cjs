#!/usr/bin/env node
// WORDS WRITTEN INTO A FILM'S CODE — the static half of "every word on screen comes from a prop", for
// scripts/workshop.py. Usage: node jsx_words.cjs <typescript module dir> <file.tsx|.ts>...
// Prints {"hits": [{file, line, text, rule}], "declared": [text]} as JSON.
//
// The rules, calibrated on the 187 library registers (2026-09-27: 300 hits, every one a word a viewer reads —
// demo defaults and intrinsic labels — once HTML entities are decoded; `&nbsp;` alone was the one false shape):
//   jsx-text      text written between JSX tags
//   jsx-literal   a string drawn as a JSX child: {'…'}, {x ? '…' : '…'}, {x ?? '…'}, `…${x}`
//   word-attr     a literal handed to a prop that carries words (text, label, title, caption, …)
//   default-copy  a destructuring default that is a phrase, or CJK — it prints whenever the film passes nothing
//   cjk-literal   Chinese/Japanese/Korean anywhere in the code (no CSS keyword or identifier is CJK)
// A line carrying `@fixed-text: <reason>`, or with it on the line above, is exempt; its literals are reported as
// `declared` so the render-side check (scripts/shot_proof.py, textSafe `unfed`) accepts the same words.
'use strict';
const fs = require('fs');
const ts = require(process.argv[2]);

const LETTER = /\p{L}/u;
const CJK = /[\p{Script=Han}\p{Script=Hiragana}\p{Script=Katakana}\p{Script=Hangul}]/u;
const ENTITY = /&(#\d+|#x[0-9a-fA-F]+|[a-zA-Z]+);/g;
const WORD_ATTRS = new Set(['text', 'label', 'title', 'caption', 'kicker', 'note', 'subtitle', 'heading',
  'tagline', 'body', 'quote', 'children']);
const hasWord = (s) => LETTER.test(String(s).replace(ENTITY, ' '));

const literalParts = (e) => {
  if (!e) return [];
  if (ts.isParenthesizedExpression(e)) return literalParts(e.expression);
  if (ts.isStringLiteral(e) || ts.isNoSubstitutionTemplateLiteral(e)) return hasWord(e.text) ? [[e, e.text]] : [];
  if (ts.isTemplateExpression(e)) {
    return [[e.head, e.head.text], ...e.templateSpans.map((s) => [s.literal, s.literal.text])]
      .filter(([, t]) => hasWord(t));
  }
  if (ts.isConditionalExpression(e)) return [...literalParts(e.whenTrue), ...literalParts(e.whenFalse)];
  if (ts.isBinaryExpression(e) && [ts.SyntaxKind.QuestionQuestionToken, ts.SyntaxKind.BarBarToken,
    ts.SyntaxKind.AmpersandAmpersandToken].includes(e.operatorToken.kind)) return literalParts(e.right);
  return [];
};

const inTypeOrImport = (n) => {
  for (let p = n.parent; p; p = p.parent) {
    if (ts.isImportDeclaration(p) || ts.isExportDeclaration(p) || ts.isTypeNode(p)) return true;
  }
  return false;
};

const hits = [];
const declared = [];
for (const file of process.argv.slice(3)) {
  const src = fs.readFileSync(file, 'utf8');
  const sf = ts.createSourceFile(file, src, ts.ScriptTarget.Latest, true,
    file.endsWith('.tsx') ? ts.ScriptKind.TSX : ts.ScriptKind.TS);
  const lines = src.split('\n');
  const isDeclared = (ln) => [ln, ln - 1].some((k) => /@fixed-text:\s*\S/.test(lines[k] || ''));
  const add = (node, text, rule) => {
    const ln = sf.getLineAndCharacterOfPosition(node.getStart(sf)).line;
    const t = String(text).replace(ENTITY, ' ').replace(/\s+/g, ' ').trim();
    if (isDeclared(ln)) {
      declared.push(t);
      return;
    }
    hits.push({file, line: ln + 1, text: t.slice(0, 60), rule});
  };
  const visit = (node) => {
    if (ts.isJsxText(node)) {
      if (hasWord(node.text)) add(node, node.text, 'jsx-text');
    } else if (ts.isJsxExpression(node) && node.expression &&
               (ts.isJsxElement(node.parent) || ts.isJsxFragment(node.parent))) {
      for (const [n, t] of literalParts(node.expression)) add(n, t, 'jsx-literal');
    } else if (ts.isJsxAttribute(node) && node.initializer && WORD_ATTRS.has(node.name.getText(sf))) {
      const init = node.initializer;
      if (ts.isStringLiteral(init)) {
        if (hasWord(init.text)) add(init, init.text, 'word-attr');
      } else if (ts.isJsxExpression(init)) {
        for (const [n, t] of literalParts(init.expression)) add(n, t, 'word-attr');
      }
    } else if (ts.isBindingElement(node) && node.initializer) {
      for (const [n, t] of literalParts(node.initializer)) {
        if (CJK.test(t) || /\S\s+\S/.test(t.trim())) add(n, t, 'default-copy');
      }
    }
    if ((ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node)) && CJK.test(node.text) &&
        !inTypeOrImport(node)) add(node, node.text, 'cjk-literal');
    ts.forEachChild(node, visit);
  };
  visit(sf);
}
const seen = new Set();
const out = hits.filter((h) => {
  const k = h.file + ':' + h.line + ':' + h.text;
  if (seen.has(k)) return false;
  seen.add(k);
  return true;
});
process.stdout.write(JSON.stringify({hits: out, declared: [...new Set(declared)]}));
