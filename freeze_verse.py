import json
import hashlib

def canonical_json_v1(data):
    """
    Produces CanonicalJson.v1 bytes.
    - Sorted keys
    - No whitespace separators
    - UTF-8 encoding
    """
    return json.dumps(data, sort_keys=True, separators=(',', ':')).encode('utf-8')

def hash_verse(operator: str, lines: list) -> str:
    """
    Calculates verse_hash based on the specification:
    SHA-256 over CanonicalJson.v1 of { operator, verse: lines }
    """
    payload = {
        "operator": operator,
        "verse": lines
    }
    canonical_bytes = canonical_json_v1(payload)
    sha256_hash = hashlib.sha256(canonical_bytes).hexdigest()
    return f"sha256:{sha256_hash}"

def main():
    # Test Data from User Request
    operator = "Crooked I"
    lines = [
        "Like A.I. I cross over when I’m near a mic",
        "I stay fly even though I got a fear of heights",
        "I aim steady when I’m gunning with one of them nines",
        "And you ain’t ready for a hustler who hugging his grind",
        "My chain heavy, so heavy the medallion broke the main levy",
        "Now that motherfucker is flooded with diamonds",
        "Like a broke ninja, I ain’t got nothing to lose",
        "But I’m Rich in Da Club, the couch is under my shoes."
    ]

    print("--- Freezing Verse ---\n")
    print(f"Operator: {operator}")
    print(f"Verse Lines: {len(lines)}")
    
    # Calculate Hash
    v_hash = hash_verse(operator, lines)
    print(f"\nCalculated Verse Hash: {v_hash}")
    
    # Verify Canonical Payload
    payload = {
        "operator": operator,
        "verse": lines
    }
    print(f"\nCanonical Payload (Preview):\n{json.dumps(payload, sort_keys=True, indent=2)}")

if __name__ == "__main__":
    main()
