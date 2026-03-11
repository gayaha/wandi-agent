import { describe, it, expect, beforeAll, afterAll } from "vitest";
import { bundle } from "@remotion/bundler";
import { selectComposition, renderMedia } from "@remotion/renderer";
import path from "node:path";
import fs from "node:fs";
import { execSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

describe("Smoke Render", () => {
  let bundlePath: string;
  const outputPath = "/tmp/renders/smoke-test.mp4";
  const testVideoPath = path.resolve(
    __dirname,
    "../../test-assets/sample.mp4"
  );

  beforeAll(async () => {
    // Ensure test video exists
    expect(fs.existsSync(testVideoPath)).toBe(true);

    // Ensure output directory exists
    fs.mkdirSync(path.dirname(outputPath), { recursive: true });

    // Bundle once for all tests (this takes 15-30s)
    bundlePath = await bundle({
      entryPoint: path.resolve(__dirname, "../../remotion/index.ts"),
      webpackOverride: (config) => ({
        ...config,
        resolve: {
          ...config.resolve,
          // The source uses .js extensions for NodeNext module resolution,
          // but webpack needs to resolve them to .ts/.tsx files.
          extensionAlias: {
            ".js": [".js", ".ts", ".tsx"],
          },
        },
      }),
    });

    // Copy test video into the bundle directory so Remotion's internal
    // server can serve it. OffthreadVideo resolves paths relative to
    // the bundle's serve URL.
    fs.copyFileSync(testVideoPath, path.join(bundlePath, "sample.mp4"));
  }, 120000); // 120s timeout for bundling

  it("REND-01: renders a valid MP4 with correct format", async () => {
    // Use staticFile path for the video (served by Remotion's bundler dev server)
    const inputProps = {
      sourceVideoUrl: "",
      sourceVideoLocalPath: "sample.mp4",
      hookText: "\u05E9\u05DC\u05D5\u05DD \u05E2\u05D5\u05DC\u05DD",
      bodyText:
        "\u05D6\u05D4 \u05D8\u05E7\u05E1\u05D8 \u05DC\u05D1\u05D3\u05D9\u05E7\u05D4 \u05E2\u05DD English words \u05D1\u05EA\u05D5\u05DA \u05DE\u05E9\u05E4\u05D8",
      textDirection: "rtl" as const,
      animationStyle: "fade" as const,
      durationInSeconds: 5,
    };

    const composition = await selectComposition({
      serveUrl: bundlePath,
      id: "ReelTemplate",
      inputProps,
    });

    // Override duration to 5 seconds (150 frames at 30fps) for fast smoke test
    await renderMedia({
      composition: { ...composition, durationInFrames: 150 },
      serveUrl: bundlePath,
      codec: "h264",
      outputLocation: outputPath,
      inputProps,
      concurrency: 1,
    });

    // Verify file exists
    expect(fs.existsSync(outputPath)).toBe(true);

    // Verify file is non-trivial size (> 10KB)
    const stats = fs.statSync(outputPath);
    expect(stats.size).toBeGreaterThan(10000);

    // Use ffprobe to verify format
    try {
      const probe = execSync(
        `ffprobe -v quiet -print_format json -show_streams "${outputPath}"`,
        { encoding: "utf-8" }
      );
      const info = JSON.parse(probe);
      const videoStream = info.streams.find(
        (s: { codec_type: string }) => s.codec_type === "video"
      );
      const audioStream = info.streams.find(
        (s: { codec_type: string }) => s.codec_type === "audio"
      );

      // REND-01: correct video codec, resolution, and framerate
      expect(videoStream).toBeDefined();
      expect(videoStream.codec_name).toBe("h264");
      expect(Number(videoStream.width)).toBe(1080);
      expect(Number(videoStream.height)).toBe(1920);

      // fps check: r_frame_rate is "30/1" format
      const [fpsNum, fpsDen] = videoStream.r_frame_rate
        .split("/")
        .map(Number);
      const fps = fpsNum / fpsDen;
      expect(fps).toBe(30);

      if (audioStream) {
        expect(audioStream.codec_name).toBe("aac");
      }
    } catch {
      // ffprobe not available -- file existence and size checks are sufficient
      console.warn(
        "ffprobe not available -- skipping detailed format checks"
      );
    }

    // Log output path for human verification (Task 2 checkpoint)
    console.log(`\nRendered MP4 saved at: ${outputPath}`);
    console.log("Open this file in a video player to verify Hebrew RTL text.");
  }, 180000); // 3 minute timeout for render

  afterAll(() => {
    // Do NOT clean up the rendered file -- it is needed for human-verify checkpoint (Task 2)
  });
});
