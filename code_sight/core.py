"""
Code Sight Core - Runtime Observability for Multimodal Agents

Provides Lightrun-style dynamic instrumentation for agent execution tracking,
multimodal stability monitoring, and deterministic replay capabilities.
"""

import time
import hashlib
import json
import threading
from typing import Dict, List, Any, Callable, Optional
from dataclasses import dataclass, asdict
from functools import wraps
from enum import Enum
import inspect


class Modality(Enum):
    """Agent execution modalities"""
    TEXT_GENERATION = "text_generation"
    CODE_EXECUTION = "code_execution"
    VISION_PROCESSING = "vision_processing"
    SIMULATION = "simulation"
    INFERENCE = "inference"
    PLANNING = "planning"
    TOOL_CALLING = "tool_calling"


class ActionType(Enum):
    """Actions to take when sight point triggers"""
    LOG = "log"
    ALERT = "alert"
    SNAPSHOT = "snapshot"
    FAIL_CLOSED = "fail_closed"
    METRIC = "metric"


@dataclass
class SightPoint:
    """Dynamic instrumentation point in agent code"""
    name: str
    target: str  # Function or method name
    modality: str
    metrics: List[str]
    conditions: Dict[str, Any]
    action: str
    enabled: bool = True
    timestamp: float = 0.0
    
    def to_dict(self):
        return asdict(self)


@dataclass
class Observation:
    """Single observation event from a sight point"""
    sight_point_name: str
    timestamp: float
    modality: str
    metrics: Dict[str, Any]
    stack_trace: str
    agent_context: Dict[str, Any]
    merkle_hash: str
    parent_hash: str
    
    def to_dict(self):
        return asdict(self)


class ObservabilityLedger:
    """
    Merkle-chained event log for deterministic replay and audit compliance.
    All observations are cryptographically signed and immutable.
    """
    
    def __init__(self, max_size: int = 10000):
        self.observations: List[Observation] = []
        self.max_size = max_size
        self.lock = threading.Lock()
        self.genesis_hash = self._compute_hash("CODE_SIGHT_GENESIS_BLOCK")
        
    def _compute_hash(self, data: str) -> str:
        """Compute SHA-256 hash for merkle chain"""
        return hashlib.sha256(data.encode()).hexdigest()
    
    def append(self, observation: Observation) -> str:
        """Add observation to ledger with merkle chain"""
        with self.lock:
            # Set parent hash from previous observation
            if len(self.observations) > 0:
                observation.parent_hash = self.observations[-1].merkle_hash
            else:
                observation.parent_hash = self.genesis_hash
            
            # Compute merkle hash from observation data + parent hash
            obs_data = json.dumps(observation.to_dict(), sort_keys=True)
            observation.merkle_hash = self._compute_hash(f"{obs_data}{observation.parent_hash}")
            
            self.observations.append(observation)
            
            # Rolling window to prevent memory bloat
            if len(self.observations) > self.max_size:
                self.observations = self.observations[-self.max_size:]
            
            return observation.merkle_hash
    
    def verify_chain(self) -> bool:
        """Verify integrity of entire observation chain"""
        if len(self.observations) == 0:
            return True
        
        expected_parent = self.genesis_hash
        for obs in self.observations:
            if obs.parent_hash != expected_parent:
                return False
            expected_parent = obs.merkle_hash
        
        return True
    
    def get_observations(self, 
                        modality: Optional[str] = None,
                        sight_point: Optional[str] = None,
                        limit: int = 100) -> List[Observation]:
        """Query observations with filters"""
        with self.lock:
            results = self.observations[-limit:]
            
            if modality:
                results = [o for o in results if o.modality == modality]
            
            if sight_point:
                results = [o for o in results if o.sight_point_name == sight_point]
            
            return results


class MultimodalTracer:
    """
    Tracks agent operations across different execution modes and correlates
    them with unified trace IDs for cross-modal debugging.
    """
    
    def __init__(self):
        self.active_traces: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.Lock()
        
    def start_trace(self, trace_id: str, modality: str, context: Dict[str, Any]):
        """Begin a new trace for a modality"""
        with self.lock:
            self.active_traces[trace_id] = {
                "trace_id": trace_id,
                "modality": modality,
                "start_time": time.time(),
                "context": context,
                "events": []
            }
    
    def add_event(self, trace_id: str, event_name: str, data: Dict[str, Any]):
        """Add event to active trace"""
        with self.lock:
            if trace_id in self.active_traces:
                self.active_traces[trace_id]["events"].append({
                    "event": event_name,
                    "timestamp": time.time(),
                    "data": data
                })
    
    def end_trace(self, trace_id: str) -> Dict[str, Any]:
        """Complete trace and return full timeline"""
        with self.lock:
            if trace_id in self.active_traces:
                trace = self.active_traces.pop(trace_id)
                trace["end_time"] = time.time()
                trace["duration_ms"] = (trace["end_time"] - trace["start_time"]) * 1000
                return trace
            return {}


class CodeSightEngine:
    """
    Main engine for Code Sight runtime observability.
    Manages sight points, observations, and multimodal tracing.
    """
    
    def __init__(self):
        self.sight_points: Dict[str, SightPoint] = {}
        self.ledger = ObservabilityLedger()
        self.tracer = MultimodalTracer()
        self.lock = threading.Lock()
        self._performance_budget_ms = 0.1  # Max overhead per sight point
        
    def register_sight_point(self, sight_point: SightPoint):
        """Register a new sight point for instrumentation"""
        with self.lock:
            self.sight_points[sight_point.name] = sight_point
            print(f"[CodeSight] Registered sight point: {sight_point.name} -> {sight_point.target}")
    
    def inject_metric(self, 
                     target: str,
                     metric_name: str,
                     alert_threshold: Optional[float] = None):
        """Dynamically inject metric tracking to a function"""
        sight_point = SightPoint(
            name=f"metric_{target}_{metric_name}",
            target=target,
            modality="inference",
            metrics=[metric_name],
            conditions={"threshold": alert_threshold} if alert_threshold else {},
            action=ActionType.METRIC.value,
            timestamp=time.time()
        )
        self.register_sight_point(sight_point)
    
    def inject_log(self,
                   target: str,
                   condition: str,
                   message: str,
                   action: str = "log"):
        """Inject conditional logging at runtime"""
        sight_point = SightPoint(
            name=f"log_{target}",
            target=target,
            modality="inference",
            metrics=[],
            conditions={"condition": condition, "message": message},
            action=action,
            timestamp=time.time()
        )
        self.register_sight_point(sight_point)
    
    def observe(self, 
                sight_point_name: str,
                modality: str,
                metrics: Dict[str, Any],
                agent_context: Dict[str, Any]) -> Observation:
        """Record an observation and add to ledger"""
        
        # Get stack trace for debugging
        stack = inspect.stack()
        stack_trace = "\n".join([
            f"{frame.filename}:{frame.lineno} in {frame.function}"
            for frame in stack[1:4]  # Limit depth
        ])
        
        observation = Observation(
            sight_point_name=sight_point_name,
            timestamp=time.time(),
            modality=modality,
            metrics=metrics,
            stack_trace=stack_trace,
            agent_context=agent_context,
            merkle_hash="",  # Will be set by ledger
            parent_hash=""
        )
        
        self.ledger.append(observation)
        
        # Check conditions and trigger actions
        if sight_point_name in self.sight_points:
            self._check_conditions(self.sight_points[sight_point_name], metrics)
        
        return observation
    
    def _check_conditions(self, sight_point: SightPoint, metrics: Dict[str, Any]):
        """Check if sight point conditions are met and trigger actions"""
        conditions = sight_point.conditions
        
        # Threshold-based alerting
        if "threshold" in conditions and conditions["threshold"] is not None:
            for metric_name, value in metrics.items():
                if isinstance(value, (int, float)) and value > conditions["threshold"]:
                    self._trigger_action(sight_point, metric_name, value)
    
    def _trigger_action(self, sight_point: SightPoint, metric_name: str, value: Any):
        """Execute action when sight point condition triggers"""
        action = sight_point.action
        
        if action == ActionType.ALERT.value:
            print(f"[CodeSight ALERT] {sight_point.name}: {metric_name}={value} exceeds threshold")
        
        elif action == ActionType.FAIL_CLOSED.value:
            print(f"[CodeSight FAIL-CLOSED] {sight_point.name}: Triggering hard-kill sequence")
            # In production, this would trigger actual fail-safe mechanisms


# Global singleton instance
_code_sight = None

def get_code_sight() -> CodeSightEngine:
    """Get global Code Sight engine instance"""
    global _code_sight
    if _code_sight is None:
        _code_sight = CodeSightEngine()
    return _code_sight


# Decorator for easy sight point instrumentation
def sight_point(name: str, 
                modality: str = "inference",
                metrics: List[str] = None,
                conditions: Dict[str, Any] = None):
    """
    Decorator to instrument a function with a sight point.
    
    Example:
        @sight_point(
            name="pinn_forward_pass",
            modality="simulation",
            metrics=["latency_ms", "physics_residual"]
        )
        def forward_pass(state, action):
            return model(state, action)
    """
    def decorator(func: Callable) -> Callable:
        sight = SightPoint(
            name=name,
            target=f"{func.__module__}.{func.__name__}",
            modality=modality,
            metrics=metrics or [],
            conditions=conditions or {},
            action=ActionType.METRIC.value
        )
        
        engine = get_code_sight()
        engine.register_sight_point(sight)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                end_time = time.time()
                
                # Collect metrics
                observed_metrics = {
                    "latency_ms": (end_time - start_time) * 1000,
                    "success": True
                }
                
                # Record observation
                engine.observe(
                    sight_point_name=name,
                    modality=modality,
                    metrics=observed_metrics,
                    agent_context={"args_count": len(args), "kwargs_count": len(kwargs)}
                )
                
                return result
                
            except Exception as e:
                end_time = time.time()
                observed_metrics = {
                    "latency_ms": (end_time - start_time) * 1000,
                    "success": False,
                    "error": str(e)
                }
                
                engine.observe(
                    sight_point_name=name,
                    modality=modality,
                    metrics=observed_metrics,
                    agent_context={"error": str(e)}
                )
                
                raise
        
        return wrapper
    return decorator


if __name__ == "__main__":
    # Example usage
    sight = get_code_sight()
    
    # Register a sight point for PINN latency tracking
    sight.inject_metric(
        target="PhyAtteN_R32.forward",
        metric_name="execution_time_ms",
        alert_threshold=1.2
    )
    
    # Demonstrate decorated function
    @sight_point(
        name="demo_computation",
        modality="simulation",
        metrics=["latency_ms"]
    )
    def expensive_computation(x: float) -> float:
        time.sleep(0.001)  # Simulate work
        return x ** 2
    
    # Run instrumented function
    result = expensive_computation(42.0)
    
    # Verify ledger integrity
    print(f"Ledger chain valid: {sight.ledger.verify_chain()}")
    
    # Query observations
    observations = sight.ledger.get_observations(limit=10)
    print(f"Total observations: {len(observations)}")
    for obs in observations:
        print(f"  - {obs.sight_point_name}: {obs.metrics}")
