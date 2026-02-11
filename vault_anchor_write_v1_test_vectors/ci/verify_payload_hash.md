# verify_payload_hash

1. Read `payload/canonical_payload.json` as UTF-8 bytes.
2. Compute `sha256` over those bytes.
3. Hex-encode the digest (lowercase).
4. Compare to `payload/payload_hash_sha256.txt`.
5. CI must fail if they differ.
