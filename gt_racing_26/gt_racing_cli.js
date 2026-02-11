// GT Racing CLI — Headless runner for deterministic simulation
// Outputs JSON with Replay Court hash for Python kernel integration

interface CLIConfig {
  seed: string;
  ticks: number;
  enableRemoteAgents: boolean;
}

// Stub implementation — placeholder for full GT Racing TypeScript codebase
// In production, this would import GameLoop, ReplayCourt, etc.

function main() {
  const args = process.argv.slice(2);
  const configIndex = args.indexOf("--config");

  if (configIndex === -1) {
    console.error("Missing --config argument");
    process.exit(1);
  }

  let config: CLIConfig;
  try {
    config = JSON.parse(args[configIndex + 1]);
  } catch (err) {
    console.error("Invalid JSON config:", err);
    process.exit(1);
  }

  // Stub simulation — deterministic hash based on seed + ticks
  const crypto = require("crypto");
  const ledgerInput = `${config.seed}:${config.ticks}`;
  const ledgerHash = crypto.createHash("sha256").update(ledgerInput).digest("hex");

  // Stub leaderboard — deterministic positions based on seed
  const hash = parseInt(ledgerHash.substring(0, 8), 16);
  const leaderboard = [
    { rank: 1, id: "car_1", lap: 3 + (hash % 2), distance: 200 + (hash % 100) },
    { rank: 2, id: "car_2", lap: 3, distance: 150 + (hash % 80) },
  ];

  const output = {
    ledger_valid: true,
    ledger_head_hash: ledgerHash,
    ledger_entry_count: config.ticks,
    ticks_simulated: config.ticks,
    leaderboard,
    vehicles: [
      { id: "car_1", x: 100, y: 50, velocity: 30, lap: 3 },
      { id: "car_2", x: 95, y: 48, velocity: 28, lap: 3 },
    ],
  };

  console.log(JSON.stringify(output, null, 2));
}

main();
