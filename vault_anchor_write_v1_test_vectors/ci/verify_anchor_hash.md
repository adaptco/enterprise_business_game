# verify_anchor_hash

1. Read `final_receipt/final_receipt_jcs_bytes.txt` as UTF-8 bytes.
2. Compute `sha256` over those bytes.
3. Hex-encode the digest (lowercase).
4. Compare to `final_receipt/anchor_hash_sha256.txt`.
5. CI must fail if they differ.
