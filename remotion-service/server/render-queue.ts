import { bundle } from "@remotion/bundler";
import { renderMedia, selectComposition } from "@remotion/renderer";
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

export function makeRenderQueue(bundlePath: string) {
  const jobs = new Map<string, JobState>();
  let queue: Promise<void> = Promise.resolve();

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
    queue = queue.then(() => runRender(jobId, parseResult.data));
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

      // Build inputProps with local video path
      const renderInputProps = {
        ...validatedProps,
        sourceVideoLocalPath: videoLocalPath,
      };

      const composition = await selectComposition({
        serveUrl: bundlePath,
        id: "ReelTemplate",
        inputProps: renderInputProps,
      });

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
    entryPoint: path.join(process.cwd(), "remotion/index.ts"),
    webpackOverride: (config) => config,
  });
  return bundlePath;
}
