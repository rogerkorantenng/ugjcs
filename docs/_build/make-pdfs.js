/**
 * Render docs/html/*.html to docs/pdf/*.pdf on A4 portrait.
 *
 * Printing from the browser is workable but leaves the submission at the mercy of
 * whatever the print dialog's "Headers and footers" checkbox happens to be set to: on, it
 * stamps the file:// URL and today's date onto every page; off, the pages carry no numbers
 * at all. Neither is right for a document being handed in, so the header and footer are
 * defined here instead.
 *
 * Run from the repo root:  node docs/_build/make-pdfs.js
 * Needs playwright, which frontend/node_modules already provides.
 */

const http = require("http");
const fs = require("fs");
const path = require("path");

const REPO = path.resolve(__dirname, "..", "..");
const HTML = path.join(REPO, "docs", "html");
const OUT = path.join(REPO, "docs", "pdf");
const PORT = 8911;

const { chromium } = require(path.join(REPO, "frontend", "node_modules", "playwright"));

const TITLES = {
  "01-project-documentation": "01 · Project Documentation",
  "02-srs": "02 · Software Requirements Specification",
  "03-effort-estimation": "03 · Effort Estimation (UCP + COCOMO II)",
  "04-technical-debt-register": "04 · Technical Debt Register",
  "05-api-contract": "05 · API Contract",
  "06-testing-report": "06 · Testing Report",
  "07-user-manual": "07 · User Manual",
  "08-qa-report": "08 · QA Report",
};

const TYPE = { ".html": "text/html; charset=utf-8", ".svg": "image/svg+xml" };

function serve() {
  return http
    .createServer((req, res) => {
      const name = decodeURIComponent(req.url.split("?")[0]).replace(/^\/+/, "");
      const file = path.join(HTML, name || "index.html");
      if (!file.startsWith(HTML) || !fs.existsSync(file)) {
        res.writeHead(404).end("not found");
        return;
      }
      res.writeHead(200, { "Content-Type": TYPE[path.extname(file)] || "text/plain" });
      fs.createReadStream(file).pipe(res);
    })
    .listen(PORT);
}

const header = (title) => `
<div style="width:100%;font-family:Georgia,serif;font-size:7pt;color:#5a6068;
            padding:0 14mm;display:flex;justify-content:space-between;">
  <span>SDJ Editorial Portal</span><span>${title}</span>
</div>`;

const footer = `
<div style="width:100%;font-family:Georgia,serif;font-size:7pt;color:#5a6068;
            padding:0 14mm;display:flex;justify-content:space-between;">
  <span>Roger Koranteng Obeng · 22424140 · Advanced Software Engineering final project</span>
  <span>Page <span class="pageNumber"></span> of <span class="totalPages"></span></span>
</div>`;

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const server = serve();
  const browser = await chromium.launch();
  const page = await browser.newPage();

  for (const [stem, title] of Object.entries(TITLES)) {
    await page.goto(`http://localhost:${PORT}/${stem}.html`, { waitUntil: "networkidle" });
    const file = path.join(OUT, `${stem}.pdf`);
    await page.pdf({
      path: file,
      format: "A4",
      printBackground: true,
      displayHeaderFooter: true,
      headerTemplate: header(title),
      footerTemplate: footer,
      // Room for the running header and footer; the sides match the stylesheet.
      margin: { top: "18mm", bottom: "16mm", left: "14mm", right: "14mm" },
    });
    const kb = Math.round(fs.statSync(file).size / 1024);
    console.log(`${stem}.pdf  ${kb} KB`);
  }

  await browser.close();
  server.close();
})();
