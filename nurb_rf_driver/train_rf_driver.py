"""
Train RF Driver.
Training a Random Forest Regressor on Expert Data.
"""

import sys
import os
import json
import joblib
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score

# Ensure package path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from nurb_rf_driver.telemetry.ndjson_logger import load_ndjson
from nurb_rf_driver.state.feature_extractor import FeatureExtractor

INPUT_LOG = os.path.join(os.path.dirname(__file__), "data", "expert_run_001.ndjson")
MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "rf_driver_v1.joblib")

def train_rf_driver():
    print(f"🌲 Training RF Driver...")
    
    # 1. Load Data
    print(f"   Loading data from {INPUT_LOG}...")
    samples = load_ndjson(INPUT_LOG)
    print(f"   Loaded {len(samples)} samples.")
    
    if not samples:
        print("❌ No data found.")
        return
        
    extractor = FeatureExtractor()
    feature_names = extractor.get_feature_names()
    target_names = extractor.get_target_names()
    
    print(f"   Features ({len(feature_names)}): {feature_names}")
    print(f"   Targets ({len(target_names)}): {target_names}")
    
    # 2. Prepare Vectors
    X = []
    y = []
    
    print("   Preprocessing...")
    for s in samples:
        if not s.get("valid", True):
            continue
            
        # Features (Dict -> Normalized List)
        feat_dict = s["features"]
        # Convert to list in canonical order
        # FeatureExtractor expects list of floats (normalized)
        # But `extractor.normalize_features` takes raw list and returns normalized list.
        # So first: dict -> raw list
        raw_list = [feat_dict[name] for name in feature_names]
        
        # Normalize
        norm_list = extractor.normalize_features(raw_list)
        X.append(norm_list)
        
        # Targets
        tgt_dict = s["targets"]
        tgt_list = [tgt_dict[name] for name in target_names]
        y.append(tgt_list)
        
    X = np.array(X)
    y = np.array(y)
    
    print(f"   Dataset shape: X={X.shape}, y={y.shape}")
    
    # 3. Split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # 4. Train RF
    # Sim Env Spec: "small forest (e.g. 10 trees) to keep inference <1ms" if running in Python tick loop?
    # Actually, for 50Hz (20ms), even 100 trees is fine.
    # But let's start with 20 estimators for speed/latency balance.
    print("   Training RandomForestRegressor (n_estimators=20, max_depth=16)...")
    
    rf = RandomForestRegressor(
        n_estimators=20,
        max_depth=16,
        random_state=42,
        n_jobs=-1
    )
    
    rf.fit(X_train, y_train)
    
    # 5. Evaluate
    print("   Evaluating...")
    y_pred = rf.predict(X_test)
    
    mse = mean_squared_error(y_test, y_pred, multioutput='raw_values')
    r2 = r2_score(y_test, y_pred, multioutput='raw_values')
    
    print("-" * 40)
    for i, name in enumerate(target_names):
        print(f"   Target: {name:20s} | MSE: {mse[i]:.6f} | R2: {r2[i]:.4f}")
    print("-" * 40)
    
    avg_r2 = np.mean(r2)
    print(f"   Average R2: {avg_r2:.4f}")
    
    # 6. Save
    print(f"   Saving model to {MODEL_PATH}...")
    joblib.dump(rf, MODEL_PATH)
    print("✅ Training Complete.")

if __name__ == "__main__":
    train_rf_driver()
