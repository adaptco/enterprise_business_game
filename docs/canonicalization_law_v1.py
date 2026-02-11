"""
Canonicalization Law V1 - Deterministic JSON serialization for hash chains.

Implements:
- CanonicalJson.v1: Sorted keys, no whitespace, UTF-8 encoding
- verse_hash computation: sha256(canonical_bytes) -> "sha256:{hex}"
"""

import json
import hashlib
from typing import Any, Dict, List


def canonical_json(obj: Any) -> bytes:
    """
    Serialize object to canonical JSON bytes.

    CanonicalJson.v1 Law:
    - Keys sorted alphabetically (recursive)
    - No whitespace (separators=(',', ':'))
    - UTF-8 encoding
    - Ensure ASCII for maximum portability

    Args:
        obj: Python object to serialize

    Returns:
        UTF-8 encoded bytes of canonical JSON
    """
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(',', ':'),
        ensure_ascii=False
    ).encode('utf-8')


def compute_verse_hash(operator: str, lines: List[str]) -> str:
    """
    Compute verse_hash per VerseCapsule.v1 spec.

    Preimage structure:
    {
        "operator": "<operator>",
        "verse": ["<line1>", "<line2>", ...]
    }

    Args:
        operator: Primary vocal/author identity
        lines: Ordered lyrical lines of the verse

    Returns:
        Hash string in format "sha256:{64_hex_chars}"
    """
    preimage = {
        "operator": operator,
        "verse": lines
    }

    canonical_bytes = canonical_json(preimage)
    hash_digest = hashlib.sha256(canonical_bytes).hexdigest()

    return f"sha256:{hash_digest}"


def verify_verse_hash(operator: str, lines: List[str], expected_hash: str) -> bool:
    """
    Verify a verse_hash matches the expected value.

    Args:
        operator: Primary vocal/author identity
        lines: Ordered lyrical lines
        expected_hash: Expected hash in "sha256:{hex}" format

    Returns:
        True if hash matches, False otherwise
    """
    computed = compute_verse_hash(operator, lines)
    return computed == expected_hash


def create_verse_capsule(
    capsule_id: str,
    operator: str,
    work_id: str,
    track_id: str,
    verse_index: int,
    lines: List[str],
    metadata: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Create a complete VerseCapsule.v1 object.

    Args:
        capsule_id: Stable identifier for this verse capsule
        operator: Primary vocal/author identity
        work_id: Work or album identifier
        track_id: Track identifier within the work
        verse_index: Zero-based index of the verse
        lines: Ordered lyrical lines
        metadata: Optional extra tags

    Returns:
        Complete VerseCapsule.v1 dictionary
    """
    verse_hash = compute_verse_hash(operator, lines)

    capsule = {
        "schema_version": "VerseCapsule.v1",
        "capsule_id": capsule_id,
        "operator": operator,
        "work_id": work_id,
        "track_id": track_id,
        "verse_index": verse_index,
        "lines": lines,
        "canonicalization": {
            "encoding": "utf-8",
            "canonicalization_law": "CanonicalizationLawV1"
        },
        "verse_hash": verse_hash
    }

    if metadata:
        capsule["metadata"] = metadata

    return capsule


# === Demo ===

if __name__ == "__main__":
    # The Crooked I verse from the spec
    crooked_lines = [
        "Like A.I. I cross over when I'm near a mic",
        "I stay fly even though I got a fear of heights",
        "I aim steady when I'm gunning with one of them nines",
        "And you ain't ready for a hustler who hugging his grind",
        "My chain heavy, so heavy the medallion broke the main levy",
        "Now that motherfucker is flooded with diamonds",
        "Like a broke ninja, I ain't got nothing to lose",
        "But I'm Rich in Da Club, the couch is under my shoes."
    ]

    # Compute hash
    DEMO_VERSE_HASH = compute_verse_hash("Crooked I", crooked_lines)
    print(f"verse_hash: {DEMO_VERSE_HASH}")

    # Create full capsule
    demo_capsule = create_verse_capsule(
        capsule_id="verse:ourhouse:rich-in-da-club:crooked-i:0",
        operator="Crooked I",
        work_id="OUR_HOUSE",
        track_id="rich-in-da-club",
        verse_index=0,
        lines=crooked_lines,
        metadata={
            "session": "LBC_2024",
            "take": 1
        }
    )

    print("\n=== VerseCapsule.v1 ===")
    print(json.dumps(demo_capsule, indent=2))

    # Verify
    print(f"\n✅ Hash verified: {verify_verse_hash('Crooked I', crooked_lines, DEMO_VERSE_HASH)}")
