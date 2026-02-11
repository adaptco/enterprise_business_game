"""
IPFS client for content-addressed checkpoint storage.
Provides wrapper around IPFS HTTP API for CID operations.
"""

import subprocess
import json
from typing import Optional


class IPFSClient:
    """
    Wrapper for IPFS HTTP API.
    Handles content-addressed storage and retrieval.
    """

    def __init__(self, api_url: str = "/ip4/127.0.0.1/tcp/5001"):
        self.api_url = api_url

    def cat(self, cid: str, max_retries: int = 3) -> str:
        """
        Fetch content by CID with retry logic.
        
        Args:
            cid: IPFS Content Identifier
            max_retries: Number of retry attempts
        
        Returns:
            Content as string
        
        Raises:
            RuntimeError: If fetch fails after retries
        """
        for attempt in range(max_retries):
            try:
                result = subprocess.run(
                    ["ipfs", "cat", cid],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode == 0:
                    return result.stdout
            except subprocess.TimeoutExpired:
                if attempt == max_retries - 1:
                    raise RuntimeError(f"IPFS cat timeout after {max_retries} attempts")
                continue
            except Exception as e:
                if attempt == max_retries - 1:
                    raise RuntimeError(f"IPFS cat failed: {e}")
                continue

        raise RuntimeError(f"IPFS cat failed for CID: {cid}")

    def add(self, content: str, pin: bool = True) -> str:
        """
        Add content to IPFS and optionally pin.
        
        Args:
            content: Content to add (string)
            pin: Whether to pin the content
        
        Returns:
            CID of added content
        
        Raises:
            RuntimeError: If add operation fails
        """
        try:
            cmd = ["ipfs", "add", "-Q"]
            if pin:
                cmd.append("--pin")

            result = subprocess.run(
                cmd,
                input=content,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                raise RuntimeError(f"IPFS add failed: {result.stderr}")

            return result.stdout.strip()

        except subprocess.TimeoutExpired:
            raise RuntimeError("IPFS add timeout")
        except Exception as e:
            raise RuntimeError(f"IPFS add error: {e}")

    def pin(self, cid: str):
        """
        Pin CID to local IPFS node.
        
        Args:
            cid: Content Identifier to pin
        """
        try:
            subprocess.run(
                ["ipfs", "pin", "add", cid],
                check=True,
                capture_output=True,
                timeout=30
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"IPFS pin failed: {e.stderr.decode()}")
        except subprocess.TimeoutExpired:
            raise RuntimeError("IPFS pin timeout")

    def is_available(self) -> bool:
        """Check if IPFS daemon is reachable"""
        try:
            result = subprocess.run(
                ["ipfs", "id"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except:
            return False

    def get_peer_id(self) -> Optional[str]:
        """Get IPFS peer ID"""
        try:
            result = subprocess.run(
                ["ipfs", "id", "-f", "<id>"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        return None
