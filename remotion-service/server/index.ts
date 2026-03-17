import crypto from "node:crypto";
import path from "node:path";
import express from "express";
import { initBundle, makeRenderQueue } from "./render-queue.js";

const app = express();
app.use(express.json());

// Serve downloaded source videos so Remotion's headless Chrome can access them
app.use("/tmp", express.static("/tmp"));

app.get("/health", (_req, res) => {
  res.json({ status: "ok" });
});

async function start() {
  console.log("Bundling Remotion composition...");
  const bundlePath = await initBundle();
  console.log("Bundle ready.");

  const port = Number(process.env.PORT) || 3000;
  const queue = makeRenderQueue(bundlePath, port);

  app.post("/renders", (req, res) => {
    const jobId = crypto.randomUUID();
    queue.enqueue(jobId, req.body);
    res.status(202).json({ jobId });
  });

  app.get("/renders/:id", (req, res) => {
    const job = queue.getJob(req.params.id);
    if (!job) {
      res.status(404).json({ error: "Job not found" });
      return;
    }
    res.json(job);
  });

  app.get("/renders/:id/file", (req, res) => {
    const job = queue.getJob(req.params.id);
    if (!job || job.state !== "completed") {
      res.status(404).json({ error: "Render not complete or not found" });
      return;
    }
    const filePath = path.join("/tmp/renders", `${req.params.id}.mp4`);
    res.download(filePath, `${req.params.id}.mp4`, (err) => {
      if (err && !res.headersSent) {
        res.status(500).json({ error: "File not found on disk" });
      }
    });
  });

  app.listen(port, () => {
    console.log(`Remotion render server ready on port ${port}`);
  });
}

start().catch((err) => {
  console.error("Failed to start server:", err);
  process.exit(1);
});

export { app };
