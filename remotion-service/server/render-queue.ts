import { bundle } from "@remotion/bundler";
import { renderMedia, selectComposition } from "@remotion/renderer";
import { execSync } from "node:child_process";
import fs from "node:fs";
import http from "node:http";
import https from "node:https";
import path from "node:path";
import { ReelInputSchema, type ReelInput } from "../remotion/schemas.js";

export type JobState = {
  state: "queued" | "in-progress" | "completed" | "failed";
  progress: number;
  videoUrl?: string;
  error?: string;
};

async function downloadVideo(url: string, destPath: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const client = url.startsWith("https") ? https : http;
    const file = fs.createWriteStream(destPath);
    client
      .get(url, (response) => {
        // Handle redirects
        if (
          response.statusCode &&
          response.statusCode >= 300 &&
          response.statusCode < 400 &&
          response.headers.location
        ) {
          file.close();
          fs.unlink(destPath, () => {});
          downloadVideo(response.headers.location, destPath)
            .then(resolve)
            .catch(reject);
          return;
        }

        if (response.statusCode && response.statusCode >= 400) {
          file.close();
          fs.unlink(destPath, () => {});
          reject(
            new Error(
              `Failed to download video: HTTP ${response.statusCode}`
            )
          );
          return;
        }

        response.pipe(file);
        file.on("finish", () => {
          file.close();
          resolve();
        });
      })
      .on("error", (err) => {
        file.close();
        fs.unlink(destPath, () => {});
        reject(err);
      });
  });
}

/**
 * Probe a local video file's duration in seconds using ffprobe.
 * Returns null if the probe fails (ffprobe not found, corrupt file, etc.).
 */
function getVideoDurationSeconds(filePath: string): number | null {
  try {
    const raw = execSync(
      `ffprobe -v error -show_entries format=duration -of csv=p=0 "${filePath}"`,
      { encoding: "utf-8", timeout: 10_000 }
    ).trim();
    const seconds = parseFloat(raw);
    return Number.isFinite(seconds) && seconds > 0 ? seconds : null;
  } catch {
    return null;
  }
}

export function makeRenderQueue(bundlePath: string, servePort?: number) {
  const jobs = new Map<string, JobState>();
  const MAX_CONCURRENT = Number(process.env.MAX_CONCURRENT_RENDERS) || 2;
  let running = 0;
  const pending: Array<{ jobId: string; props: ReelInput }> = [];

  function processNext(): void {
    while (running < MAX_CONCURRENT && pending.length > 0) {
      const next = pending.shift()!;
      running++;
      console.log(
        `[queue] Starting ${next.jobId} (running=${running}/${MAX_CONCURRENT}, pending=${pending.length})`
      );
      runRender(next.jobId, next.props).finally(() => {
        running--;
        processNext();
      });
    }
  }

  function enqueue(jobId: string, inputProps: unknown): void {
    const parseResult = ReelInputSchema.safeParse(inputProps);
    if (!parseResult.success) {
      jobs.set(jobId, {
        state: "failed",
        progress: 0,
        error: `Validation error: ${parseResult.error.message}`,
      });
      return;
    }

    jobs.set(jobId, { state: "queued", progress: 0 });
    pending.push({ jobId, props: parseResult.data });
    processNext();
  }

  async function runRender(
    jobId: string,
    validatedProps: ReelInput
  ): Promise<void> {
    const videoLocalPath = path.join("/tmp", `${jobId}-source.mp4`);
    const outputDir = "/tmp/renders";
    const outputPath = path.join(outputDir, `${jobId}.mp4`);

    try {
      jobs.set(jobId, { state: "in-progress", progress: 0 });

      // Ensure output directory exists
      fs.mkdirSync(outputDir, { recursive: true });

      // Pre-download source video to local disk
      await downloadVideo(validatedProps.sourceVideoUrl, videoLocalPath);

      // Probe actual video duration so the rendered output matches the source
      const actualDuration = getVideoDurationSeconds(videoLocalPath);

      if (actualDuration !== null) {
        console.log(
          `[${jobId}] ffprobe detected video duration: ${actualDuration.toFixed(1)}s`
        );
      } else {
        console.warn(
          `[${jobId}] ffprobe failed to detect video duration — ` +
            `falling back to ${validatedProps.durationInSeconds || 15}s. ` +
            `Video may appear stretched or frozen at the end if actual duration differs.`
        );
      }

      // Build inputProps with HTTP URL so Remotion's headless Chrome can fetch it.
      // The Express server serves /tmp as static files.
      const port = servePort ?? (Number(process.env.PORT) || 3000);
      const videoServeUrl = `http://localhost:${port}/tmp/${jobId}-source.mp4`;

      // If we got the actual video duration, override durationInSeconds and
      // rescale segment timing proportionally so text overlays span the full video.
      const declaredDuration = validatedProps.durationInSeconds ?? null;
      const effectiveDuration = actualDuration ?? declaredDuration ?? 15;

      // Diagnostic logging for duration debugging
      console.log(
        `[${jobId}] DURATION DIAG: ffprobe=${actualDuration}, ` +
          `payloadDuration=${validatedProps.durationInSeconds}, ` +
          `declared=${declaredDuration}, ` +
          `effective=${effectiveDuration}, ` +
          `frames=${Math.round(effectiveDuration * 30)}`
      );
      if (actualDuration === null && declaredDuration === null) {
        console.warn(
          `[${jobId}] No duration detected (ffprobe failed, no declared duration). Using 15s fallback.`
        );
      }

      const originalDuration = declaredDuration ?? effectiveDuration;

      let effectiveSegments = validatedProps.segments;
      if (
        actualDuration !== null &&
        validatedProps.segments &&
        validatedProps.segments.length > 0 &&
        originalDuration > 0
      ) {
        const scale = actualDuration / originalDuration;
        effectiveSegments = validatedProps.segments.map((seg) => ({
          ...seg,
          startSeconds: seg.startSeconds * scale,
          endSeconds: seg.endSeconds * scale,
        }));
      }

      const renderInputProps = {
        ...validatedProps,
        sourceVideoLocalPath: videoServeUrl,
        durationInSeconds: effectiveDuration,
        ...(effectiveSegments !== validatedProps.segments
          ? { segments: effectiveSegments }
          : {}),
      };

      const composition = await selectComposition({
        serveUrl: bundlePath,
        id: "ReelTemplate",
        inputProps: renderInputProps,
      });

      // Override composition duration to match the actual video length.
      // This replaces the removed calculateMetadata in Root.tsx to avoid
      // potential prop-delivery interference in Remotion v4.
      const FPS = 30;
      composition.durationInFrames = Math.round(effectiveDuration * FPS);

      await renderMedia({
        composition,
        serveUrl: bundlePath,
        codec: "h264",
        outputLocation: outputPath,
        inputProps: renderInputProps,
        concurrency: 1,
        onProgress: ({ progress }) => {
          jobs.set(jobId, { state: "in-progress", progress });
        },
      });

      jobs.set(jobId, {
        state: "completed",
        progress: 1,
        videoUrl: outputPath,
      });
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Unknown render error";
      jobs.set(jobId, {
        state: "failed",
        progress: 0,
        error: errorMessage,
      });
    } finally {
      // Clean up temp source video
      fs.unlink(videoLocalPath, () => {});
    }
  }

  function getJob(id: string): JobState | undefined {
    return jobs.get(id);
  }

  return { enqueue, getJob };
}

export async function initBundle(): Promise<string> {
  const bundlePath = await bundle({
    entryPoint: path.join(process.cwd(), "remotion", "index.ts"),
    webpackOverride: (config) => ({
      ...config,
      resolve: {
        ...config.resolve,
        extensionAlias: {
          ".js": [".tsx", ".ts", ".js"],
        },
      },
    }),
  });
  return bundlePath;
}
