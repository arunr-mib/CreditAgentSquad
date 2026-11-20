// Builds the public demo: index.html (page with a document skeleton) and api/_evidence.mjs (the same evidence packs and prompt the page uses).
import fs from "node:fs";
const SRC = process.argv[2], OUT = process.argv[3];
const html = fs.readFileSync(SRC, "utf8");
const lines = html.split("\n");
const grab = (startRe, endRe) => { const i = lines.findIndex((l) => startRe.test(l)); let j = i; while (!endRe.test(lines[j])) j++; return lines.slice(i, j + 1).join("\n"); };
const parts = [
  grab(/^  const PORTFOLIO = \[/, /^  \];/),
  grab(/^  const WATCH = /, /^  const WATCH = /),
  grab(/^  const rml = /, /^  const rml = /),
  grab(/^  const PACKS = \{/, /^  \};/),
  grab(/^  PACKS\.portfolio = \{/, /^  \};/),
  grab(/^  const packText = /, /^  const packText = /),
  grab(/^  function prompt\(ctx/, /^  \}$/),
];
fs.mkdirSync(`${OUT}/api`, { recursive: true });
fs.writeFileSync(`${OUT}/api/_evidence.mjs`, `// GENERATED from the demo page by build.mjs. Do not edit by hand.\n${parts.join("\n")}\nexport { PACKS, prompt };\n`);
fs.writeFileSync(`${OUT}/index.html`, `<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n<meta name="robots" content="noindex, nofollow">\n</head>\n<body>\n${html}\n</body>\n</html>\n`);
fs.writeFileSync(`${OUT}/robots.txt`, "User-agent: *\nDisallow: /\n");
console.log("built", OUT);
