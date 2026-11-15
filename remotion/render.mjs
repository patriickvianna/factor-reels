// Renderiza um Reels: node render.mjs props.json saida.mp4 capa.jpg
// O "bundle" do projeto é feito uma vez e reaproveitado (REMOTION_BUNDLE).
import { bundle } from "@remotion/bundler";
import { renderMedia, renderStill, selectComposition } from "@remotion/renderer";
import fs from "node:fs";
import path from "node:path";

const [propsFile, outMp4, outCover] = process.argv.slice(2);
const props = JSON.parse(fs.readFileSync(propsFile, "utf8"));
const cache = process.env.REMOTION_BUNDLE || "/tmp/remotion-bundle";
const browserExecutable = process.env.REMOTION_BROWSER || null; // só em teste local
let serveUrl = cache;
if (!fs.existsSync(path.join(cache, "index.html"))) {
  serveUrl = await bundle({ entryPoint: path.resolve("src/index.ts"), outDir: cache, publicDir: path.resolve("public") });
}
// o áudio do Reels vai para a pasta pública do bundle (o bundle já foi feito antes deste arquivo existir)
if (props.audio_file) {
  const rel = `jobs/${path.basename(props.audio_file)}`;
  fs.mkdirSync(path.join(serveUrl, "public", "jobs"), { recursive: true });
  fs.copyFileSync(props.audio_file, path.join(serveUrl, "public", rel));
  props.audio = rel;
  delete props.audio_file;
}
const composition = await selectComposition({ serveUrl, id: "Reel", inputProps: props, browserExecutable });
const t0 = Date.now();
await renderMedia({
  serveUrl, composition, inputProps: props, codec: "h264", outputLocation: outMp4, browserExecutable,
  crf: 19, pixelFormat: "yuv420p", audioCodec: "aac", audioBitrate: "192k", x264Preset: "medium",
  concurrency: Number(process.env.REMOTION_CONCURRENCY || 0) || null, licenseKey: "free-license",
  chromiumOptions: { gl: "swangle" },
});
if (outCover) {
  const frame = Math.min(composition.durationInFrames - 1, Math.round((props.cover ?? 1.4) * 30));
  await renderStill({ serveUrl, composition, inputProps: props, output: outCover, frame, imageFormat: "jpeg", jpegQuality: 92, browserExecutable, licenseKey: "free-license" });
}
console.log(JSON.stringify({ ok: true, seconds: Math.round((Date.now() - t0) / 1000) }));
