import { describe, it, expect, vi } from "vitest";

// Mock the Remotion modules to prevent importing the actual bundler/renderer
// which require Chrome and webpack infrastructure
vi.mock("@remotion/bundler", () => ({
  bundle: vi.fn().mockResolvedValue("/tmp/mock-bundle"),
}));

vi.mock("@remotion/renderer", () => ({
  selectComposition: vi.fn().mockResolvedValue({
    id: "ReelTemplate",
    width: 1080,
    height: 1920,
    fps: 30,
    durationInFrames: 2700,
  }),
  renderMedia: vi.fn().mockResolvedValue(undefined),
}));

// Import after mocks are set up
const { makeRenderQueue } = await import("../../server/render-queue.js");

describe("makeRenderQueue", () => {
  it("returns enqueue and getJob functions", () => {
    const queue = makeRenderQueue("/tmp/mock-bundle");
    expect(typeof queue.enqueue).toBe("function");
    expect(typeof queue.getJob).toBe("function");
  });

  it("enqueue creates a job with queued state", () => {
    const queue = makeRenderQueue("/tmp/mock-bundle");
    const jobId = "test-job-1";
    queue.enqueue(jobId, {
      sourceVideoUrl: "https://example.com/video.mp4",
      hookText: "Test hook",
      bodyText: "Test body",
    });
    const job = queue.getJob(jobId);
    expect(job).toBeDefined();
    expect(job?.state).toBe("queued");
    expect(job?.progress).toBe(0);
  });

  it("getJob returns undefined for unknown jobId", () => {
    const queue = makeRenderQueue("/tmp/mock-bundle");
    const job = queue.getJob("nonexistent-id");
    expect(job).toBeUndefined();
  });
});
