module.exports = {
  apps: [
    {
      name: "wandi-agent",
      script: "main.py",
      interpreter: "python3",
      cwd: __dirname,
    },
    {
      name: "remotion-service",
      script: "npm",
      args: "run dev",
      cwd: __dirname + "/remotion-service",
    },
  ],
};
