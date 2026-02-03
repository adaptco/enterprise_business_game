"""
Random Forest AI Driver Training Pipeline
Deterministic training with SSOT lineage tracking.
"""

import numpy as np
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Tuple
from datetime import datetime, timezone
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, r2_score
import joblib


class TrainingDataLoader:
    """Load and preprocess state-action pairs from NDJSON."""
    
    def __init__(self, training_file: str):
        self.training_file = training_file
        self.data: List[Dict] = []
        self.features: np.ndarray = None
        self.targets: Dict[str, np.ndarray] = {}
        
    def load(self) -> int:
        """Load NDJSON training data."""
        with open(self.training_file, 'r') as f:
            for line in f:
                self.data.append(json.loads(line.strip()))
        
        print(f"✓ Loaded {len(self.data)} training samples")
        return len(self.data)
    
    def extract_features(self) -> Tuple[np.ndarray, Dict[str, np.ndarray]]:
        """
        Extract feature matrix and target vectors.
        
        Returns:
            X: Feature matrix (N x D)
            y_dict: {'steering': [...], 'throttle': [...], 'brake': [...]}
        """
        N = len(self.data)
        
        # Define feature order (must be deterministic)
        feature_names = [
            'speed', 'yaw_rate', 'longitudinal_accel', 'lateral_accel',
            'steering_angle', 'throttle_input', 'brake_input',
            'engine_rpm', 'gear',
            'track_x', 'track_y', 'heading',
            'distance_to_centerline', 'track_progress',
            'current_curvature', 'track_gradient',
            'distance_to_apex', 'apex_radius',
            'dist_left_edge', 'dist_right_edge',
            'front_ray', 'front_left_ray', 'front_right_ray',
            # Degradation features (new)
            'tire_wear', 'tire_grip_mult', 'fuel_normalized',
            'weather_grip', 'rain_intensity'
        ]
        
        # Add upcoming curvature (5 horizon points)
        for i in range(5):
            feature_names.append(f'upcoming_curvature_{i}')
        
        # Add wheel speeds (4 wheels)
        for i in range(4):
            feature_names.append(f'wheel_speed_{i}')
        
        D = len(feature_names)
        X = np.zeros((N, D), dtype=np.float32)
        
        # Extract features
        for i, record in enumerate(self.data):
            state = record['state']
            
            for j, fname in enumerate(feature_names):
                if fname.startswith('upcoming_curvature'):
                    idx = int(fname.split('_')[-1])
                    X[i, j] = state['upcoming_curvature'][idx]
                elif fname.startswith('wheel_speed'):
                    idx = int(fname.split('_')[-1])
                    X[i, j] = state['wheel_speeds'][idx]
                else:
                    X[i, j] = state[fname]
        
        # Extract targets
        y_steering = np.array([record['action']['steering_command'] for record in self.data], dtype=np.float32)
        y_throttle = np.array([record['action']['throttle_command'] for record in self.data], dtype=np.float32)
        y_brake = np.array([record['action']['brake_command'] for record in self.data], dtype=np.float32)
        
        self.features = X
        self.targets = {
            'steering': y_steering,
            'throttle': y_throttle,
            'brake': y_brake
        }
        
        print(f"✓ Extracted features: {X.shape}")
        print(f"  - Feature dimension: {D}")
        print(f"  - Samples: {N}")
        
        return X, self.targets


class DeterministicRandomForest:
    """
    Random Forest with deterministic training for reproducibility.
    """
    
    def __init__(self, seed: int=42, n_estimators: int=100, max_depth: int=20):
        self.seed = seed
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        
        # Create three models (one per control output)
        self.models = {
            'steering': RandomForestRegressor(
                n_estimators=n_estimators,
                max_depth=max_depth,
                min_samples_split=10,
                min_samples_leaf=5,
                random_state=seed,
                n_jobs=-1
            ),
            'throttle': RandomForestRegressor(
                n_estimators=n_estimators,
                max_depth=max_depth,
                min_samples_split=10,
                min_samples_leaf=5,
                random_state=seed,
                n_jobs=-1
            ),
            'brake': RandomForestRegressor(
                n_estimators=n_estimators,
                max_depth=max_depth,
                min_samples_split=10,
                min_samples_leaf=5,
                random_state=seed,
                n_jobs=-1
            )
        }
        
        # Scalers for normalization
        self.scalers = {
            'features': StandardScaler(),
            'steering': StandardScaler(),
            'throttle': StandardScaler(),
            'brake': StandardScaler()
        }
        
        # Training lineage
        self.training_lineage = {
            'seed': seed,
            'n_estimators': n_estimators,
            'max_depth': max_depth,
            'train_time': None,
            'training_hash': None,
            'model_version': None
        }
    
    def train(
        self,
        X: np.ndarray,
        y_dict: Dict[str, np.ndarray],
        test_size: float=0.2,
        validation_size: float=0.1
    ) -> Dict[str, Any]:
        """
        Train all three Random Forest models.
        
        Args:
            X: Feature matrix
            y_dict: Targets for steering, throttle, brake
            test_size: Fraction for test set
            validation_size: Fraction for validation set
        
        Returns:
            Training report with metrics and lineage
        """
        start_time = datetime.now(timezone.utc)
        
        # Split data (deterministic with fixed seed)
        X_train, X_temp, y_train, y_temp = {}, {}, {}, {}
        
        for control_name, y in y_dict.items():
            X_t, X_tmp, y_t, y_tmp = train_test_split(
                X, y,
                test_size=(test_size + validation_size),
                random_state=self.seed
            )
            
            X_val, X_test, y_val, y_test = train_test_split(
                X_tmp, y_tmp,
                test_size=(test_size / (test_size + validation_size)),
                random_state=self.seed
            )
            
            X_train[control_name] = X_t
            y_train[control_name] = y_t
            X_temp[control_name] = (X_val, X_test)
            y_temp[control_name] = (y_val, y_test)
        
        print(f"✓ Data split:")
        print(f"  - Training: {len(y_train['steering'])} samples")
        print(f"  - Validation: {len(y_temp['steering'][0])} samples")
        print(f"  - Test: {len(y_temp['steering'][1])} samples")
        
        # Normalize features (fit on training data only)
        X_train_scaled = self.scalers['features'].fit_transform(X_train['steering'])
        
        # Train each model
        metrics = {}
        for control_name in ['steering', 'throttle', 'brake']:
            print(f"\n🌲 Training {control_name} model...")
            
            # Normalize target
            y_train_scaled = self.scalers[control_name].fit_transform(
                y_train[control_name].reshape(-1, 1)
            ).ravel()
            
            # Train
            self.models[control_name].fit(X_train_scaled, y_train_scaled)
            
            # Validate
            X_val, X_test = X_temp[control_name]
            y_val, y_test = y_temp[control_name]
            
            X_val_scaled = self.scalers['features'].transform(X_val)
            X_test_scaled = self.scalers['features'].transform(X_test)
            
            # Predictions
            y_val_pred_scaled = self.models[control_name].predict(X_val_scaled)
            y_test_pred_scaled = self.models[control_name].predict(X_test_scaled)
            
            # Inverse transform
            y_val_pred = self.scalers[control_name].inverse_transform(
                y_val_pred_scaled.reshape(-1, 1)
            ).ravel()
            y_test_pred = self.scalers[control_name].inverse_transform(
                y_test_pred_scaled.reshape(-1, 1)
            ).ravel()
            
            # Metrics
            val_mse = mean_squared_error(y_val, y_val_pred)
            val_r2 = r2_score(y_val, y_val_pred)
            test_mse = mean_squared_error(y_test, y_test_pred)
            test_r2 = r2_score(y_test, y_test_pred)
            
            metrics[control_name] = {
                'val_mse': float(val_mse),
                'val_r2': float(val_r2),
                'test_mse': float(test_mse),
                'test_r2': float(test_r2)
            }
            
            print(f"  - Validation MSE: {val_mse:.6f}, R²: {val_r2:.4f}")
            print(f"  - Test MSE: {test_mse:.6f}, R²: {test_r2:.4f}")
        
        # Compute training lineage hash
        training_manifest = {
            'seed': self.seed,
            'n_estimators': self.n_estimators,
            'max_depth': self.max_depth,
            'training_samples': len(y_train['steering']),
            'metrics': metrics,
            'timestamp': start_time.isoformat()
        }
        
        training_json = json.dumps(training_manifest, sort_keys=True, separators=(',', ':'))
        training_hash = hashlib.sha256(training_json.encode('utf-8')).hexdigest()
        
        self.training_lineage.update({
            'train_time': start_time.isoformat(),
            'training_hash': training_hash,
            'model_version': f'rf_v1_{training_hash[:8]}',
            'metrics': metrics
        })
        
        return {
            'status': 'success',
            'lineage_hash': training_hash,
            'model_version': self.training_lineage['model_version'],
            'metrics': metrics,
            'training_duration': (datetime.now(timezone.utc) - start_time).total_seconds()
        }
    
    def predict(self, state_dict: Dict[str, Any]) -> Dict[str, float]:
        """
        Predict control commands from vehicle state.
        
        Args:
            state_dict: VehicleState as dictionary
        
        Returns:
            {'steering': ..., 'throttle': ..., 'brake': ...}
        """
        # Extract features in deterministic order
        features = self._extract_features_from_state(state_dict)
        X = np.array([features], dtype=np.float32)
        
        # Normalize
        X_scaled = self.scalers['features'].transform(X)
        
        # Predict
        predictions = {}
        for control_name in ['steering', 'throttle', 'brake']:
            y_pred_scaled = self.models[control_name].predict(X_scaled)
            y_pred = self.scalers[control_name].inverse_transform(
                y_pred_scaled.reshape(-1, 1)
            ).ravel()[0]
            
            predictions[control_name] = float(y_pred)
        
        # Clamp to valid ranges
        predictions['steering'] = np.clip(predictions['steering'], -1.0, 1.0)
        predictions['throttle'] = np.clip(predictions['throttle'], 0.0, 1.0)
        predictions['brake'] = np.clip(predictions['brake'], 0.0, 1.0)
        
        return predictions
    
    def _extract_features_from_state(self, state: Dict) -> List[float]:
        """Extract feature vector from state dictionary."""
        features = [
            state['speed'], state['yaw_rate'],
            state['longitudinal_accel'], state['lateral_accel'],
            state['steering_angle'], state['throttle_input'], state['brake_input'],
            state['engine_rpm'], state['gear'],
            state['track_x'], state['track_y'], state['heading'],
            state['distance_to_centerline'], state['track_progress'],
            state['current_curvature'], state['track_gradient'],
            state['distance_to_apex'], state['apex_radius'],
            state['dist_left_edge'], state['dist_right_edge'],
            state['front_ray'], state['front_left_ray'], state['front_right_ray'],
            # Degradation features (new, with defaults for backwards compat)
            state.get('tire_wear', 0.0),
            state.get('tire_grip_mult', 1.0),
            state.get('fuel_normalized', 1.0),
            state.get('weather_grip', 1.2),
            state.get('rain_intensity', 0.0)
        ]
        
        # Add upcoming curvature
        features.extend(state['upcoming_curvature'])
        
        # Add wheel speeds
        features.extend(state['wheel_speeds'])
        
        return features
    
    def save_models(self, directory: str="./models"):
        """Save trained models and scalers with lineage."""
        Path(directory).mkdir(exist_ok=True)
        
        # Save models
        for name, model in self.models.items():
            joblib.dump(model, f"{directory}/rf_{name}.joblib")
        
        # Save scalers
        for name, scaler in self.scalers.items():
            joblib.dump(scaler, f"{directory}/scaler_{name}.joblib")
        
        # Save lineage
        with open(f"{directory}/training_lineage.json", 'w') as f:
            json.dump(self.training_lineage, f, indent=2)
        
        print(f"✓ Saved models to {directory}/")
        print(f"  - Model version: {self.training_lineage['model_version']}")
        print(f"  - Lineage hash: {self.training_lineage['training_hash'][:16]}...")
    
    @classmethod
    def load_models(cls, directory: str="./models"):
        """Load trained models from directory."""
        instance = cls()
        
        # Load models
        for name in ['steering', 'throttle', 'brake']:
            instance.models[name] = joblib.load(f"{directory}/rf_{name}.joblib")
        
        # Load scalers
        for name in ['features', 'steering', 'throttle', 'brake']:
            instance.scalers[name] = joblib.load(f"{directory}/scaler_{name}.joblib")
        
        # Load lineage
        with open(f"{directory}/training_lineage.json", 'r') as f:
            instance.training_lineage = json.load(f)
        
        print(f"✓ Loaded model version: {instance.training_lineage['model_version']}")
        
        return instance


def create_training_ledger_entry(
    training_data_file: str,
    training_report: Dict,
    model_directory: str
) -> Dict[str, Any]:
    """
    Create governance ledger entry for model training.
    Compatible with existing ledger format.
    """
    # Compute training data hash
    data_hash = hashlib.sha256(
        Path(training_data_file).read_bytes()
    ).hexdigest()
    
    entry = {
        'event_type': 'model_training',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'training_data': {
            'file': training_data_file,
            'data_hash': data_hash
        },
        'model_version': training_report['model_version'],
        'lineage_hash': training_report['lineage_hash'],
        'metrics': training_report['metrics'],
        'model_directory': model_directory,
        'training_duration_sec': training_report['training_duration']
    }
    
    # Compute entry hash
    entry_json = json.dumps(entry, sort_keys=True, separators=(',', ':'))
    entry['hash'] = hashlib.sha256(entry_json.encode('utf-8')).hexdigest()
    
    return entry
