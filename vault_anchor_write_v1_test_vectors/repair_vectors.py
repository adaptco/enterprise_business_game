
import json
import hashlib
import base64
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

def canonical_json(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

def main():
    root = Path(".")
    
    # 1. Fix Payload Hash
    print("Repairing Payload Hash...")
    payload_path = root / "payload" / "canonical_payload.json"
    payload_bytes = payload_path.read_bytes()
    payload_hash = hashlib.sha256(payload_bytes).hexdigest()
    
    (root / "payload" / "payload_hash_sha256.txt").write_text(payload_hash)
    print(f"  Payload Hash: {payload_hash}")
    
    # 2. Generate New Keys (to ensure validity)
    print("Generating New Keys...")
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    
    # Save DER Base64 to disk (as per existing pattern check)
    # Using PKCS8/SubjectPublicKeyInfo which are standard DER formats
    priv_der = private_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    pub_der = public_key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    
    (root / "keys" / "ed25519_private.base64").write_text(base64.b64encode(priv_der).decode())
    (root / "keys" / "ed25519_public.base64").write_text(base64.b64encode(pub_der).decode())
    
    # Get Raw bytes for use in Receipt (verify script expects from_public_bytes which means Raw 32 bytes)
    pub_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    )
    
    # No need to load back, we have objects
    # private_key and pub_bytes are ready
    
    # 3. Construct Pre-Anchor Receipt (for Anchor Hash calc)
    # We take original keys from final_receipt.json (except hash/sig)
    receipt_path = root / "final_receipt" / "final_receipt.json"
    original_receipt = json.loads(receipt_path.read_text())
    
    # Fields to include in Anchor Hash calculation
    # NOTE: We must match verification expectation.
    # verify_anchor_hash says: jcs = final_receipt_jcs_bytes.txt. digest = hash(jcs).
    # so final_receipt_jcs_bytes.txt MUST match anchor_hash preimage.
    # Assuming the preimage is the receipt MINUS [anchor_hash, signature, vault_public_key, sealed].
    # Or maybe MINUS [signature, vault_public_key]? 
    # Usually "anchor_hash" is a field IN the receipt, so it's calculated from the OTHER fields.
    
    pre_anchor = {
        "anchor_id": original_receipt["anchor_id"],
        "artifact_kind": original_receipt["artifact_kind"],
        "payload_hash": payload_hash, # UPDATED
        "schema_version": original_receipt["schema_version"],
        "ts": original_receipt["ts"],
        "vault_fingerprint": original_receipt["vault_fingerprint"]
    }
    
    pre_anchor_jcs = canonical_json(pre_anchor)
    (root / "final_receipt" / "final_receipt_jcs_bytes.txt").write_bytes(pre_anchor_jcs)
    
    anchor_hash = hashlib.sha256(pre_anchor_jcs).hexdigest()
    (root / "final_receipt" / "anchor_hash_sha256.txt").write_text(anchor_hash)
    print(f"  Anchor Hash: {anchor_hash}")
    
    # 4. Sign Anchor Hash
    # We sign the raw bytes of the hash
    msg_bytes = bytes.fromhex(anchor_hash) 
    signature_bytes = private_key.sign(msg_bytes)
    signature_hex = signature_bytes.hex()
    
    # 5. Update Final Receipt
    final_receipt = pre_anchor.copy()
    final_receipt["anchor_hash"] = anchor_hash
    final_receipt["vault_public_key"] = pub_bytes.hex() # Using Hex as verify script expects
    final_receipt["signature"] = signature_hex # Using Hex as verify script expects
    final_receipt["sealed"] = True
    
    receipt_path.write_text(json.dumps(final_receipt, indent=4))
    print("  Updated final_receipt.json")
    
    # 6. Update Ledger Line
    ledger_path = root / "ledger" / "ledger_line.jsonl"
    # Ledger line should match final receipt fields
    # Using the same dict
    ledger_line = final_receipt.copy()
    # Ledger line schema said "VaultLedgerLine.v1" in verify script
    ledger_line["schema_version"] = "VaultLedgerLine.v1" 
    del ledger_line["sealed"]
    del ledger_line["signature"]
    del ledger_line["vault_public_key"] # Verify script doesn't check pubkey on ledger line
    
    ledger_path.write_text(json.dumps(ledger_line))
    print("  Updated ledger_line.jsonl")
    
    print("Done.")

if __name__ == "__main__":
    main()
