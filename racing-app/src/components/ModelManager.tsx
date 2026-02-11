import React, { useState } from 'react'

const ModelManager: React.FC = () => {
    const [models] = useState([
        {
            name: 'rf_v1_baseline',
            version: 'v1.0',
            trained: '2026-01-15',
            r2_score: 0.9876,
            mse: 0.00234,
            status: 'ready'
        },
        {
            name: 'rf_v2_tuned',
            version: 'v2.0',
            trained: '2026-01-16',
            r2_score: 0.9912,
            mse: 0.00182,
            status: 'ready'
        }
    ])

    return (
        <div className="model-manager">
            <div className="card">
                <h2>🤖 AI Model Management</h2>

                <div className="model-list">
                    {models.map((model, idx) => (
                        <div key={idx} className="model-card">
                            <div className="model-header">
                                <h3>{model.name}</h3>
                                <span className={`status-badge ${model.status}`}>{model.status.toUpperCase()}</span>
                            </div>

                            <div className="model-info">
                                <div className="info-row">
                                    <span className="label">Version:</span>
                                    <span className="value">{model.version}</span>
                                </div>
                                <div className="info-row">
                                    <span className="label">Trained:</span>
                                    <span className="value">{model.trained}</span>
                                </div>
                                <div className="info-row">
                                    <span className="label">R² Score:</span>
                                    <span className="value">{model.r2_score.toFixed(4)}</span>
                                </div>
                                <div className="info-row">
                                    <span className="label">MSE:</span>
                                    <span className="value">{model.mse.toFixed(5)}</span>
                                </div>
                            </div>

                            <div className="model-actions">
                                <button className="btn-sm">Load Model</button>
                                <button className="btn-sm">View Details</button>
                                <button className="btn-sm btn-outline">Export</button>
                            </div>
                        </div>
                    ))}
                </div>

                <div className="training-section">
                    <h3>Train New Model</h3>
                    <div className="training-form">
                        <div className="form-group">
                            <label htmlFor="trainingDataSelect">Training Data</label>
                            <select id="trainingDataSelect" aria-label="Select training data file">
                                <option>telemetry_expert_001.ndjson</option>
                                <option>telemetry_expert_002.ndjson</option>
                            </select>
                        </div>

                        <div className="form-group">
                            <label htmlFor="nEstimatorsInput">n_estimators</label>
                            <input id="nEstimatorsInput" type="number" defaultValue={100} aria-label="Number of estimators" />
                        </div>

                        <div className="form-group">
                            <label htmlFor="maxDepthInput">max_depth</label>
                            <input id="maxDepthInput" type="number" defaultValue={18} aria-label="Maximum tree depth" />
                        </div>

                        <button className="btn-primary">🚀 Start Training</button>
                    </div>
                </div>
            </div>

            <div className="card">
                <h2>📊 Model Performance</h2>
                <p className="info-text">Comparison of steering, throttle, and brake prediction accuracy</p>

                <div className="performance-table">
                    <table>
                        <thead>
                            <tr>
                                <th>Model</th>
                                <th>Steering R²</th>
                                <th>Throttle R²</th>
                                <th>Brake R²</th>
                                <th>Avg R²</th>
                            </tr>
                        </thead>
                        <tbody>
                            {models.map((model, idx) => (
                                <tr key={idx}>
                                    <td>{model.name}</td>
                                    <td className="metric">{model.r2_score.toFixed(4)}</td>
                                    <td className="metric">{(model.r2_score + 0.003).toFixed(4)}</td>
                                    <td className="metric">{(model.r2_score + 0.005).toFixed(4)}</td>
                                    <td className="metric strong">{((model.r2_score * 3 + 0.008) / 3).toFixed(4)}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    )
}

export default ModelManager
