# verify_ledger_line

1. Read the single line from `ledger/ledger_line.jsonl`.
2. Parse as JSON; ensure `schema_version == "VaultLedgerLine.v1"`.
3. Confirm `anchor_id`, `anchor_hash`, `artifact_kind`, `payload_hash`, `run_id`, `ts`, and `vault_fingerprint` match `final_receipt/final_receipt.json`.
4. Optionally recompute `sha256` over final receipt JCS bytes and confirm it equals `anchor_hash`.
5. CI must fail on any mismatch.
