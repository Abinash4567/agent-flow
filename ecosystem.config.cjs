module.exports = {
  apps: [
    {
      name: "btc-trading-bot",
      script: "bot.py",
      interpreter: "./.venv/bin/python3",
      args: "--daemon",
      cwd: __dirname,
      autorestart: true,
      watch: false,
      max_memory_restart: "1G",
      env: {
        DAEMON_MODE: "true",
        POLL_INTERVAL_SECONDS: "900",
        STOP_LOSS_PCT: "0.02",
        TAKE_PROFIT_PCT: "0.06",
      },
    },
  ],
};
