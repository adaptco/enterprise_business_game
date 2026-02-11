# verify_signature

1. Read `pre_anchor/pre_anchor_jcs_bytes.txt` as UTF-8 bytes.
2. Base64-decode `keys/ed25519_public.base64` to get the public key.
3. Base64-decode `pre_anchor/pre_anchor_signature.base64` to get the signature.
4. Verify Ed25519(public_key, message_bytes, signature).
5. CI must fail if verification fails.
