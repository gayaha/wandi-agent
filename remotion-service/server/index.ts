import crypto from "node:crypto";
import express from "express";
import { initBundle, makeRenderQueue } from "./render-queue.js";

const app = express();
app.use(express.json());

app.get("/health", (_req, res) => {
  res.json({ status: "ok" });
});

async function start() {
  console.log("Bundling Remotion composition...");
  const bundlePath = await initBundle();
  console.log("Bundle ready.");

  const queue = makeRenderQueue(bundlePath);

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

  const port = process.env.PORT || 3000;
  app.listen(port, () => {
    console.log(`Remotion render server ready on port ${port}`);
  });
}

start().catch((err) => {
  console.error("Failed to start server:", err);
  process.exit(1);
});

export { app };
