"""
IPFS Bridge for content-addressed checkpoint storage.
Provides CID generation, pinning, and fetching capabilities.
"""

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Dict, Any, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


@dataclass
class IPFSConfig:
    """Configuration for IPFS node connection."""
    api_endpoint: str = "http://127.0.0.1:5001"
    gateway_endpoint: str = "http://127.0.0.1:8080"
    timeout_seconds: int = 30
    max_retries: int = 3
    retry_backoff_factor: float = 0.5


class IPFSBridge:
    """
    Bridge to IPFS node for content-addressed storage.
    Supports pinning, fetching, and CID verification.
    """
    
    def __init__(self, config: Optional[IPFSConfig] = None):
        self.config = config or IPFSConfig()
        self.session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        """Create requests session with retry logic."""
        session = requests.Session()
        retry_strategy = Retry(
            total=self.config.max_retries,
            backoff_factor=self.config.retry_backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session
    
    def generate_multihash(self, payload: Dict[str, Any]) -> str:
        """
        Generate keccak-256 multihash from payload.
        
        Args:
            payload: Dictionary to hash (will be canonicalized via JCS)
        
        Returns:
            Hex-encoded multihash with prefix (0x1b20 + 32-byte hash)
        """
        # Serialize to canonical JSON (sorted keys, no whitespace)
        canonical_json = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        
        # Compute keccak-256 hash
        from Crypto.Hash import keccak
        k = keccak.new(digest_bits=256)
        k.update(canonical_json.encode('utf-8'))
        hash_bytes = k.digest()
        
        # Build multihash: 0x1b (keccak-256) + 0x20 (32 bytes) + hash
        multihash = "0x1b20" + hash_bytes.hex()
        return multihash
    
    def multihash_to_cid(self, multihash: str, codec: str = "dag-json") -> str:
        """
        Convert multihash to CIDv1 (base32-encoded).
        
        Args:
            multihash: Hex-encoded multihash (e.g., "0x1b20...")
            codec: IPFS codec ("dag-json", "dag-cbor", or "raw")
        
        Returns:
            CIDv1 string in base32 format (e.g., "bagiacgza...")
        """
        try:
            from cid import make_cid
            import base58
            
            # Remove 0x prefix if present
            if multihash.startswith("0x"):
                multihash = multihash[2:]
            
            # Convert multihash hex to bytes
            multihash_bytes = bytes.fromhex(multihash)
            
            # Map codec names to codes
            codec_map = {
                "dag-json": 0x0129,
                "dag-cbor": 0x71,
                "raw": 0x55
            }
            codec_code = codec_map.get(codec, 0x0129)
            
            # Build CIDv1: version (1) + codec + multihash
            cid = make_cid(1, codec, multihash_bytes)
            
            # Encode to base32
            return cid.encode('base32').decode('utf-8')
        except ImportError:
            # Fallback: manual base32 encoding (basic implementation)
            import base64
            if multihash.startswith("0x"):
                multihash = multihash[2:]
            
            # Simple CIDv1 construction (version 1 + dag-json codec 0x0129)
            version = b'\x01'
            codec_bytes = b'\x29\x01'  # dag-json in varint encoding
            multihash_bytes = bytes.fromhex(multihash)
            
            cid_bytes = version + codec_bytes + multihash_bytes
            # Base32 encode (lowercase, no padding)
            b32 = base64.b32encode(cid_bytes).decode('utf-8').lower().rstrip('=')
            return 'b' + b32  # CIDv1 base32 prefix
    
    def cid_to_multihash(self, cid: str) -> str:
        """
        Extract multihash from CIDv1.
        
        Args:
            cid: CIDv1 string (base32-encoded)
        
        Returns:
            Hex-encoded multihash (e.g., "0x1b20...")
        """
        try:
            from cid import make_cid
            
            cid_obj = make_cid(cid)
            multihash_bytes = cid_obj.multihash
            return "0x" + multihash_bytes.hex()
        except ImportError:
            # Fallback: manual base32 decoding
            import base64
            
            # Remove 'b' prefix for base32
            if cid.startswith('b'):
                cid = cid[1:]
            
            # Decode base32
            # Pad to multiple of 8
            padding_needed = (8 - len(cid) % 8) % 8
            cid_padded = cid.upper() + '=' * padding_needed
            
            cid_bytes = base64.b32decode(cid_padded)
            
            # Skip version (1 byte) and codec (varint, typically 2 bytes)
            # For dag-json: version 0x01, codec 0x0129 (varint encoded as 0x29 0x01)
            multihash_bytes = cid_bytes[3:]  # Skip first 3 bytes
            
            return "0x" + multihash_bytes.hex()
    
    def verify_cid(self, cid: str, payload: Dict[str, Any]) -> bool:
        """
        Verify that CID matches the payload.
        
        Args:
            cid: CIDv1 to verify
            payload: Dictionary that should match the CID
        
        Returns:
            True if CID is valid for payload, False otherwise
        """
        try:
            # Extract multihash from CID
            cid_multihash = self.cid_to_multihash(cid)
            
            # Compute multihash from payload
            computed_multihash = self.generate_multihash(payload)
            
            return cid_multihash == computed_multihash
        except Exception:
            return False
    
    def pin_capsule(self, payload: Dict[str, Any], codec: str = "dag-json") -> Optional[str]:
        """
        Pin checkpoint capsule to IPFS.
        
        Args:
            payload: Checkpoint capsule dictionary
            codec: IPFS codec to use ("dag-json" or "dag-cbor")
        
        Returns:
            CIDv1 string if successful, None if IPFS unavailable
        """
        try:
            # Serialize payload
            if codec == "dag-json":
                data = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode('utf-8')
                content_type = "application/json"
            elif codec == "dag-cbor":
                import cbor2
                data = cbor2.dumps(payload)
                content_type = "application/cbor"
            else:
                raise ValueError(f"Unsupported codec: {codec}")
            
            # Call IPFS API: /api/v0/add
            url = f"{self.config.api_endpoint}/api/v0/add"
            files = {'file': ('checkpoint.json', data, content_type)}
            params = {
                'cid-version': 1,
                'hash': 'keccak-256',
                'pin': 'true'
            }
            
            response = self.session.post(
                url,
                files=files,
                params=params,
                timeout=self.config.timeout_seconds
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('Hash')  # CIDv1
            else:
                print(f"IPFS pin failed: {response.status_code} - {response.text}")
                return None
        
        except requests.exceptions.RequestException as e:
            print(f"IPFS connection error: {e}")
            return None
        except Exception as e:
            print(f"IPFS pin error: {e}")
            return None
    
    def fetch_capsule(self, cid: str) -> Optional[Dict[str, Any]]:
        """
        Fetch checkpoint capsule from IPFS by CID.
        
        Args:
            cid: CIDv1 identifier
        
        Returns:
            Checkpoint capsule dictionary if found, None otherwise
        """
        try:
            # Call IPFS API: /api/v0/cat
            url = f"{self.config.api_endpoint}/api/v0/cat"
            params = {'arg': cid}
            
            response = self.session.post(
                url,
                params=params,
                timeout=self.config.timeout_seconds
            )
            
            if response.status_code == 200:
                # Try to parse as JSON
                try:
                    return response.json()
                except json.JSONDecodeError:
                    # Might be CBOR
                    import cbor2
                    return cbor2.loads(response.content)
            else:
                print(f"IPFS fetch failed: {response.status_code}")
                return None
        
        except requests.exceptions.RequestException as e:
            print(f"IPFS connection error: {e}")
            return None
        except Exception as e:
            print(f"IPFS fetch error: {e}")
            return None
    
    def is_available(self) -> bool:
        """
        Check if IPFS node is available.
        
        Returns:
            True if IPFS node is reachable, False otherwise
        """
        try:
            url = f"{self.config.api_endpoint}/api/v0/version"
            response = self.session.post(url, timeout=5)
            return response.status_code == 200
        except Exception:
            return False
