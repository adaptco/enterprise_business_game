"""
Node.js Bridge — Subprocess interface to TypeScript GT Racing kernel.
Executes headless GT Racing simulation and returns JSON results.
"""

import subprocess
import json
import os
from typing import Dict, Any


class NodeBridge:
    """
    Bridge to execute GT Racing TypeScript kernel via Node.js subprocess.
    Provides deterministic, headless simulation with JSON I/O.
    """

    def __init__(self, cli_script: str = "gt_racing_cli.js"):
        # Default to gt_racing_26 directory relative to kernel_boot_system
        base_dir = os.path.dirname(os.path.dirname(__file__))  # Go up to enterprise_business_game
        self.cli_path = os.path.join(base_dir, "gt_racing_26", cli_script)

    def run_simulation(
        self,
        seed: str,
        ticks: int,
        remote_agents: bool = False,
        timeout: int = 60
    ) -> Dict[str, Any]:
        """
        Execute GT Racing simulation via Node.js CLI.
        
        Args:
            seed: Deterministic seed for RNG
            ticks: Number of simulation ticks to run
            remote_agents: Enable remote agent enrichment (default: False)
            timeout: Subprocess timeout in seconds
        
        Returns:
            Dict with leaderboard, vehicles, ledger_valid, ledger_head_hash, etc.
        
        Raises:
            RuntimeError: If GT Racing execution fails
        """
        if not os.path.exists(self.cli_path):
            raise RuntimeError(f"GT Racing CLI not found: {self.cli_path}")

        # Build configuration
        config = {
            "seed": seed,
            "ticks": ticks,
            "enableRemoteAgents": remote_agents
        }

        # Execute Node.js subprocess
        try:
            result = subprocess.run(
                ["node", self.cli_path, "--config", json.dumps(config)],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=os.path.dirname(self.cli_path)
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"GT Racing subprocess timeout after {timeout}s")
        except FileNotFoundError:
            raise RuntimeError("Node.js not found in PATH — ensure Node.js is installed")
        except Exception as e:
            raise RuntimeError(f"GT Racing subprocess error: {e}")

        # Check return code
        if result.returncode != 0:
            raise RuntimeError(f"GT Racing failed (exit {result.returncode}): {result.stderr}")

        # Parse JSON output
        try:
            output = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"GT Racing output is not valid JSON: {e}\n{result.stdout[:500]}")

        # Validate expected fields
        required_fields = ["ledger_valid", "ledger_head_hash", "ticks_simulated", "leaderboard"]
        for field in required_fields:
            if field not in output:
                raise RuntimeError(f"GT Racing output missing required field: {field}")

        return output

    def check_availability(self) -> bool:
        """Check if Node.js and GT Racing CLI are available"""
        try:
            # Check Node.js
            node_check = subprocess.run(
                ["node", "--version"],
                capture_output=True,
                timeout=5
            )
            if node_check.returncode != 0:
                return False

            # Check CLI script exists
            if not os.path.exists(self.cli_path):
                return False

            return True
        except:
            return False
