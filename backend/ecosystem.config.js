const rawNodePort = String(process.env.AIFL_NODE_PORT || "").trim();
const parsedNodePort = rawNodePort ? Number.parseInt(rawNodePort, 10) : NaN;
const nodePort = Number.isFinite(parsedNodePort) ? parsedNodePort : 3006;

module.exports = {
  apps: [{
    name: "language-learning-backend",
    script: "./dist/index.js",
    instances: 1, // Start with 1 instance for safety (due to in-memory sessions)
    exec_mode: "fork",
    watch: false, // Don't watch in production
    max_memory_restart: "1G", // Restart if memory exceeds 1GB
    env: {
      NODE_ENV: "production",
      // Legacy Node backend port (explicit override to avoid accidental conflict with FastAPI).
      PORT: nodePort
    },
    error_file: "./logs/pm2-error.log",
    out_file: "./logs/pm2-out.log",
    time: true, // Add timestamps to logs
    exp_backoff_restart_delay: 100 // Delay between restarts
  }]
};
