"""
Random Forest training script with explicit I/O contract.

Input:
    - Training data: NDJSON or CSV with schema_training_sample.json contract
    - Config: rf_default.yaml (hyperparameters)

Output:
    - Trained models: steering.joblib, throttle.joblib, brake.joblib
    - Scalers: scaler_features.joblib, scaler_*.joblib
    - Metadata: model_metadata.json (lineage, metrics, feature names)
"""

import argparse
import json
import hashlib
import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, r2_score
import yaml

# Add state module to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from state.state_space import VehicleStateV1


def load_config(config_path: str) -> dict:
    """Load training configuration."""
    with open(config_path) as f:
        return yaml.safe_load(f)


def load_training_data(data_path: str) -> pd.DataFrame:
    """Load NDJSON or CSV training data."""
    if data_path.endswith('.ndjson'):
        df = pd.read_json(data_path, lines=True)
    elif data_path.endswith('.csv'):
        df = pd.read_csv(data_path)
    else:
        raise ValueError(f"Unsupported format: {data_path}")
    
    # Filter valid samples
    df = df[df['valid'] == True].copy()
    
    # Filter out offtrack/crashes if configured
    df = df[df['event'] == ''].copy()
    
    print(f"✓ Loaded {len(df)} valid training samples from {data_path}")
    return df


def extract_features_targets(df: pd.DataFrame) -> tuple:
    """
    Extract X (features) and y (targets) from DataFrame.
    
    Returns:
        X: Feature matrix (N x 13)
        y_dict: {steering: array, throttle: array, brake: array}
    """
    feature_cols = VehicleStateV1.feature_names()
    
    # Build X matrix
    X = df[feature_cols].values.astype(np.float32)
    
    # Extract targets
    y_steering = df['steering_command'].values.astype(np.float32)
    y_throttle = df['throttle_command'].values.astype(np.float32)
    y_brake = df['brake_command'].values.astype(np.float32)
    
    print(f"✓ Extracted features: {X.shape}")
    print(f"  Feature names ({len(feature_cols)}): {feature_cols[:5]}...")
    
    return X, {
        'steering': y_steering,
        'throttle': y_throttle,
        'brake': y_brake
    }


def train_model(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: np.ndarray,
    y_val: np.ndarray,
    config: dict,
    target_name: str
) -> tuple:
    """
    Train single Random Forest model.
    
    Returns:
        (model, val_mse, val_r2)
    """
    print(f"\n🌲 Training {target_name} model...")
    
    rf = RandomForestRegressor(
        n_estimators=config['n_estimators'],
        max_depth=config['max_depth'],
        min_samples_leaf=config['min_samples_leaf'],
        min_samples_split=config.get('min_samples_split', 10),
        random_state=config['seed'],
        n_jobs=-1,
        verbose=0
    )
    
    rf.fit(X_train, y_train)
    
    # Validate
    y_val_pred = rf.predict(X_val)
    val_mse = mean_squared_error(y_val, y_val_pred)
    val_r2 = r2_score(y_val, y_val_pred)
    
    print(f"  ✓ Validation MSE: {val_mse:.6f}")
    print(f"  ✓ Validation R²: {val_r2:.4f}")
    
    return rf, val_mse, val_r2


def main():
    parser = argparse.ArgumentParser(description="Train Random Forest driver")
    parser.add_argument('--data', required=True, help='Training data path (.ndjson or .csv)')
    parser.add_argument('--config', default='training/configs/rf_default.yaml', 
                       help='Config file')
    parser.add_argument('--output-dir', default='data/models', 
                       help='Output directory for models')
    
    args = parser.parse_args()
    
    # Load config
    config = load_config(args.config)
    print(f"✓ Loaded config: {args.config}")
    print(f"  - n_estimators: {config['n_estimators']}")
    print(f"  - max_depth: {config['max_depth']}")
    print(f"  - seed: {config['seed']}")
    
    # Load data
    df = load_training_data(args.data)
    
    # Extract features & targets
    X, y_dict = extract_features_targets(df)
    
    # Train/val/test split (deterministic)
    test_size = config.get('test_size', 0.2)
    val_size = config.get('val_size', 0.1)
    
    X_train, X_temp = train_test_split(
        X, test_size=(test_size + val_size), random_state=config['seed']
    )
    X_val, X_test = train_test_split(
        X_temp, test_size=(test_size / (test_size + val_size)), 
        random_state=config['seed']
    )
    
    print(f"\n✓ Data split:")
    print(f"  - Train: {len(X_train)} samples")
    print(f"  - Val: {len(X_val)} samples")
    print(f"  - Test: {len(X_test)} samples")
    
    # Normalize features (fit on training data)
    scaler_features = StandardScaler()
    X_train_scaled = scaler_features.fit_transform(X_train)
    X_val_scaled = scaler_features.transform(X_val)
    X_test_scaled = scaler_features.transform(X_test)
    
    # Train each model
    models = {}
    scalers = {'features': scaler_features}
    metrics = {}
    
    for target_name in ['steering', 'throttle', 'brake']:
        # Split target
        y_train_target = y_dict[target_name][:len(X_train)]
        y_val_target = y_dict[target_name][len(X_train):len(X_train)+len(X_val)]
        y_test_target = y_dict[target_name][len(X_train)+len(X_val):]
        
        # Normalize target (optional, but helps)
        scaler_target = StandardScaler()
        y_train_scaled = scaler_target.fit_transform(y_train_target.reshape(-1, 1)).ravel()
        y_val_scaled = scaler_target.transform(y_val_target.reshape(-1, 1)).ravel()
        
        # Train
        model, val_mse, val_r2 = train_model(
            X_train_scaled, y_train_scaled,
            X_val_scaled, y_val_scaled,
            config, target_name
        )
        
        # Test evaluation (inverse transform)
        y_test_pred_scaled = model.predict(X_test_scaled)
        y_test_pred = scaler_target.inverse_transform(y_test_pred_scaled.reshape(-1, 1)).ravel()
        
        test_mse = mean_squared_error(y_test_target, y_test_pred)
        test_r2 = r2_score(y_test_target, y_test_pred)
        
        print(f"  ✓ Test MSE: {test_mse:.6f}")
        print(f"  ✓ Test R²: {test_r2:.4f}")
        
        models[target_name] = model
        scalers[target_name] = scaler_target
        metrics[target_name] = {
            'val_mse': float(val_mse),
            'val_r2': float(val_r2),
            'test_mse': float(test_mse),
            'test_r2': float(test_r2)
        }
    
    # Save models and scalers
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for name, model in models.items():
        joblib.dump(model, output_dir / f"{name}.joblib")
    
    for name, scaler in scalers.items():
        joblib.dump(scaler, output_dir / f"scaler_{name}.joblib")
    
    print(f"\n✓ Saved models to {output_dir}/")
    
    # Compute training data hash for lineage
    data_hash = hashlib.sha256(Path(args.data).read_bytes()).hexdigest()
    
    # Save metadata
    metadata = {
        "model_type": "RandomForestRegressor",
        "version": "v1.0",
        "n_estimators": config['n_estimators'],
        "max_depth": config['max_depth'],
        "min_samples_leaf": config['min_samples_leaf'],
        "feature_names": VehicleStateV1.feature_names(),
        "targets": ["steering", "throttle", "brake"],
        "train_data_path": str(args.data),
        "train_data_hash": f"sha256:{data_hash}",
        "metrics": metrics,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "config": config
    }
    
    with open(output_dir / "model_metadata.json", 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"✓ Saved metadata to {output_dir}/model_metadata.json")
    print(f"\n✅ Training complete!")
    print(f"  - Model hash (lineage): sha256:{data_hash[:16]}...")
    print(f"  - Avg test R²: {np.mean([m['test_r2'] for m in metrics.values()]):.4f}")


if __name__ == "__main__":
    main()
