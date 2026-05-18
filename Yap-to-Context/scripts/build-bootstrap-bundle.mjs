/**
 * Next.js instrumentation uses webpackIgnore for `./db/bootstrap.cjs` so Node-only
 * code is not bundled into the Edge instrumentation graph. This script emits that
 * file next to `.next/server/instrumentation.js` after `next build`.
 */
import * as esbuild from "esbuild";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(__dirname, "..");
const outDir = path.join(root, ".next", "server", "db");
/* CommonJS so Node treats it as CJS without `"type": "module"` in package.json. */
const outfile = path.join(outDir, "bootstrap.cjs");

fs.mkdirSync(outDir, { recursive: true });

await esbuild.build({
  entryPoints: [path.join(root, "src", "db", "bootstrap.ts")],
  bundle: true,
  platform: "node",
  target: "node20",
  format: "cjs",
  outfile,
  absWorkingDir: root,
  plugins: [
    {
      name: "resolve-at-alias",
      setup(build) {
        build.onResolve({ filter: /^@\// }, (args) => {
          const rel = args.path.slice(2);
          const base = path.join(root, "src", rel);
          const candidates = [
            base + ".ts",
            base + ".tsx",
            path.join(base, "index.ts"),
          ];
          for (const c of candidates) {
            if (fs.existsSync(c)) return { path: c };
          }
          return { path: base + ".ts" };
        });
      },
    },
  ],
  logLevel: "info",
});

console.log(`Wrote ${path.relative(root, outfile)}`);
