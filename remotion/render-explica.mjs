// Renderiza um Reels explicativo 3D (GUT #112), inteiro ou em partes, para dividir o trabalho entre máquinas.
//   node render-explica.mjs props.json saida.mp4 [--part=2/6] [--still=12.5:capa.jpg]
// Com --part=i/n, renderiza só o pedaço i de n (quadros sem som); junte as partes com join-explica.sh.
import { bundle } from "@remotion/bundler";
import { renderMedia, renderStill, selectComposition } from "@remotion/renderer";
import fs from "node:fs";
import path from "node:path";

const args = process.argv.slice(2);
const [propsFile, out] = args.filter((a) => !a.startsWith("--"));
const opt = Object.fromEntries(args.filter((a) => a.startsWith("--")).map((a) => a.slice(2).split("=")));
const props = JSON.parse(fs.readFileSync(propsFile, "utf8"));
const cache = process.env.REMOTION_BUNDLE || "/tmp/remotion-bundle-explica";
const browserExecutable = process.env.REMOTION_BROWSER || null;
let serveUrl = cache;
if (!fs.existsSync(path.join(cache, "index.html"))) {
  serveUrl = await bundle({ entryPoint: path.resolve("src/index.ts"), outDir: cache, publicDir: path.resolve("public") });
}
if (props.audio_file) {
  const rel = `jobs/${path.basename(props.audio_file)}`;
  fs.mkdirSync(path.join(serveUrl, "public", "jobs"), { recursive: true });
  fs.copyFileSync(props.audio_file, path.join(serveUrl, "public", rel));
  props.audio = rel;
  delete props.audio_file;
}
const chromiumOptions = { gl: process.env.REMOTION_GL || "angle" };
const composition = await selectComposition({ serveUrl, id: "Explica3D", inputProps: props, browserExecutable, chromiumOptions });
const common = { serveUrl, composition, inputProps: props, browserExecutable, chromiumOptions, licenseKey: "free-license" };

if (opt.still) {
  const [sec, file] = opt.still.split(":");
  const frame = Math.min(composition.durationInFrames - 1, Math.round(Number(sec) * 30));
  await renderStill({ ...common, output: file, frame, imageFormat: "jpeg", jpegQuality: 92 });
  console.log(JSON.stringify({ ok: true, still: file, frame }));
  process.exit(0);
}

let frameRange = null;
if (opt.part) {
  const [i, n] = opt.part.split("/").map(Number);
  const total = composition.durationInFrames;
  const size = Math.ceil(total / n);
  frameRange = [(i - 1) * size, Math.min(total, i * size) - 1];
}
const t0 = Date.now();
await renderMedia({
  ...common, codec: "h264", outputLocation: out, crf: 18, pixelFormat: "yuv420p", x264Preset: "medium",
  frameRange, muted: Boolean(frameRange), audioCodec: frameRange ? null : "aac", audioBitrate: "192k",
  concurrency: Number(process.env.REMOTION_CONCURRENCY || 0) || null,
});
console.log(JSON.stringify({ ok: true, frameRange, seconds: Math.round((Date.now() - t0) / 1000) }));
