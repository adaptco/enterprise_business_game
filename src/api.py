"""
FastAPI service for Enterprise Business Game.
Provides REST endpoints for company registration, operations, and game state.
"""

from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import uvicorn

from game_engine import GameEngine, IndustrySector, OperationType
from ledger import Account, TransactionType
try:
    from ipfs_bridge import IPFSBridge, IPFSConfig
except ImportError:
    IPFSBridge = None
    IPFSConfig = None

app = FastAPI(title="Enterprise Business Game API", version="1.0.0")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global game engine instance (with optional IPFS)
try:
    ipfs_bridge = IPFSBridge(IPFSConfig()) if IPFSBridge else None
    game = GameEngine(seed=42, ipfs_bridge=ipfs_bridge)
except Exception:
    # Fallback if IPFS not available
    game = GameEngine(seed=42)


# Pydantic models for request validation
class CompanyRegistrationRequest(BaseModel):
    company_name: str
    founding_capital_usd: float
    industry_sector: str
    sovereign_signature: str


class OperationRequest(BaseModel):
    operation_type: str
    params: Dict[str, Any]


class CheckpointCreateRequest(BaseModel):
    checkpoint_id: Optional[str] = None


# === Company Management Endpoints ===

@app.post("/company/register")
async def register_company(req: CompanyRegistrationRequest):
    """Register a new shell company"""
    try:
        sector = IndustrySector[req.industry_sector]
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Invalid industry sector: {req.industry_sector}")

    company = game.register_company(
        company_name=req.company_name,
        founding_capital_usd=req.founding_capital_usd,
        industry_sector=sector,
        sovereign_signature=req.sovereign_signature,
        is_ai=False
    )

    return {
        "status": "registered",
        "company": company.registration_info()
    }


@app.get("/company/{company_id}/status")
async def get_company_status(company_id: str):
    """Get current company state"""
    company = game.get_company(company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    return company.to_dict()


@app.get("/company/{company_id}/ledger")
async def get_company_ledger(company_id: str):
    """Export company transaction history"""
    company = game.get_company(company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    return {
        "company_id": company_id,
        "company_name": company.company_name,
        "transactions": company.ledger.export_audit_trail(),
        "genesis_hash": company.ledger.get_genesis_hash(),
        "chain_valid": company.ledger.verify_chain()
    }


@app.post("/company/{company_id}/operation")
async def submit_operation(company_id: str, req: OperationRequest):
    """Submit a business operation for execution on next tick"""
    try:
        operation_type = OperationType[req.operation_type]
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Invalid operation type: {req.operation_type}")

    try:
        result = game.execute_operation(company_id, operation_type, req.params)
        return {
            "status": "executed",
            "operation": result
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# === Game Management Endpoints ===

@app.post("/game/tick")
async def advance_tick():
    """Advance simulation by one tick (admin/scheduler only)"""
    game.tick()
    market_state = game.get_market_state()

    return {
        "status": "advanced",
        "current_tick": game.current_tick,
        "market_state": market_state
    }


@app.get("/game/state")
async def get_game_state():
    """Get current market state and company rankings"""
    return game.get_market_state()


@app.get("/game/verify")
async def verify_integrity():
    """Verify Merkle chain integrity for all companies"""
    results = game.verify_all_chains()

    all_valid = all(results.values())

    return {
        "overall_integrity": "INTACT" if all_valid else "CORRUPTED",
        "company_chains": results
    }


@app.get("/game/companies")
async def list_companies():
    """List all registered companies"""
    companies = []
    for company in game.companies.values():
        companies.append({
            "company_id": company.company_id,
            "company_name": company.company_name,
            "industry_sector": company.industry_sector.value,
            "is_ai": company.is_ai,
            "employees": company.resources.employees,
            "cash_usd": company.resources.cash_usd,
            "revenue_usd": company.financial.total_revenue_usd
        })

    return {"companies": companies}


# === Health Check ===

@app.get("/health")
async def health_check():
    """API health check"""
    return {
        "status": "healthy",
        "current_tick": game.current_tick,
        "total_companies": len(game.companies)
    }


# === Checkpoint Management Endpoints ===

@app.post("/checkpoint/create")
async def create_checkpoint(req: Optional[CheckpointCreateRequest] = None):
    """Create a checkpoint of current game state (optionally pinned to IPFS)"""
    checkpoint_id = req.checkpoint_id if req else None
    
    try:
        checkpoint = game.create_checkpoint(checkpoint_id=checkpoint_id)
        
        response = {
            "status": "created",
            "checkpoint_id": checkpoint["checkpoint_id"],
            "canonical_sha256": checkpoint["canonical_sha256"],
            "tick": checkpoint["tick"],
            "timestamp_utc": checkpoint["timestamp_utc"]
        }
        
        # Include IPFS fields if available
        if "ipfs_cid" in checkpoint:
            response["ipfs_cid"] = checkpoint["ipfs_cid"]
            response["storage_uri"] = checkpoint["storage_uri"]
        
        return response
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Checkpoint creation failed: {str(e)}")


@app.get("/checkpoint/{cid}")
async def get_checkpoint(cid: str):
    """Fetch checkpoint by CID or checkpoint_id"""
    # Try to find in local history first
    checkpoint = next((c for c in game.checkpoint_history if c.get("ipfs_cid") == cid or c["checkpoint_id"] == cid), None)
    
    if checkpoint:
        return checkpoint
    
    # If not found locally and IPFS bridge is available, try to fetch from IPFS
    if game.ipfs_bridge:
        try:
            checkpoint = game.ipfs_bridge.fetch_capsule(cid)
            if checkpoint:
                return checkpoint
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to fetch from IPFS: {str(e)}")
    
    raise HTTPException(status_code=404, detail="Checkpoint not found")


@app.post("/checkpoint/restore/{cid}")
async def restore_checkpoint(cid: str):
    """Restore game state from a checkpoint CID"""
    if not game.ipfs_bridge:
        raise HTTPException(status_code=400, detail="IPFS bridge not configured")
    
    try:
        game.load_checkpoint(cid)
        
        return {
            "status": "restored",
            "cid": cid,
            "restored_tick": game.current_tick,
            "total_companies": len(game.companies)
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Restore failed: {str(e)}")


@app.get("/checkpoint/verify/{cid}")
async def verify_checkpoint(cid: str):
    """Verify checkpoint CID integrity"""
    # Find checkpoint
    checkpoint = next((c for c in game.checkpoint_history if c.get("ipfs_cid") == cid), None)
    
    if not checkpoint:
        # Try to fetch from IPFS
        if game.ipfs_bridge:
            checkpoint = game.ipfs_bridge.fetch_capsule(cid)
        
        if not checkpoint:
            raise HTTPException(status_code=404, detail="Checkpoint not found")
    
    # Verify CID
    cid_valid = False
    if game.ipfs_bridge and "ipfs_cid" in checkpoint:
        cid_valid = game.ipfs_bridge.verify_cid(cid, checkpoint)
    
    # Verify canonical hash
    import json
    import hashlib
    flow_state = checkpoint.get("flow_state", {})
    canonical_json = json.dumps(flow_state, sort_keys=True, separators=(',', ':'))
    computed_hash = hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()
    hash_valid = computed_hash == checkpoint.get("canonical_sha256")
    
    return {
        "checkpoint_id": checkpoint["checkpoint_id"],
        "cid": cid,
        "cid_valid": cid_valid,
        "hash_valid": hash_valid,
        "canonical_sha256": checkpoint["canonical_sha256"],
        "tick": checkpoint["tick"]
    }


@app.get("/checkpoint/history")
async def get_checkpoint_history():
    """Get all checkpoints created in this session"""
    checkpoints = []
    
    for checkpoint in game.checkpoint_history:
        summary = {
            "checkpoint_id": checkpoint["checkpoint_id"],
            "tick": checkpoint["tick"],
            "timestamp_utc": checkpoint["timestamp_utc"],
            "canonical_sha256": checkpoint["canonical_sha256"],
            "total_companies": checkpoint["flow_state"]["total_companies"]
        }
        
        if "ipfs_cid" in checkpoint:
            summary["ipfs_cid"] = checkpoint["ipfs_cid"]
            summary["storage_uri"] = checkpoint["storage_uri"]
        
        checkpoints.append(summary)
    
    return {"checkpoints": checkpoints}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
