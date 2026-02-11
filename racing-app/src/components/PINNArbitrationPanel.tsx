import React, { useState, useEffect } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts'
import CodeSightClient from '../lib/CodeSightClient'

interface PINNMetrics {
    timestamp: number
    stateEstimationLatency: number // milliseconds
    physicsResidual: number // unitless loss value
    hausdorffDistance: number // nanometers
    pacejkaSlipAngle: number // radians
    idempotencyValid: boolean
    fpgaCycleCount: number
}

interface PINNArbitrationPanelProps {
    isActive: boolean
    mode: 'calibration' | 'first_light' | 'validation'
}

const PINNArbitrationPanel: React.FC<PINNArbitrationPanelProps> = ({ isActive, mode }) => {
    const [metrics, setMetrics] = useState<PINNMetrics[]>([])
    const [currentMetric, setCurrentMetric] = useState<PINNMetrics>({
        timestamp: 0,
        stateEstimationLatency: 0,
        physicsResidual: 0,
        hausdorffDistance: 0,
        pacejkaSlipAngle: 0,
        idempotencyValid: true,
        fpgaCycleCount: 0
    })

    const [failClosedTriggered, setFailClosedTriggered] = useState(false)
    const [calibrationStatus, setCalibrationStatus] = useState<'standby' | 'armed' | 'active' | 'fail-closed'>('standby')
    const [codeSight] = useState(() => new CodeSightClient('ws://localhost:8765'))

    // First Light telemetry simulation
    useEffect(() => {
        if (!isActive) {
            setCalibrationStatus('standby')
            return
        }

        setCalibrationStatus(mode === 'first_light' ? 'armed' : 'active')

        const interval = setInterval(() => {
            const now = Date.now()

            // Simulate PhyAtteN_R32 PINN metrics with realistic physics
            const baseLatency = 0.95 // Base ~0.95ms
            const jitter = (Math.random() - 0.5) * 0.3 // ±0.15ms jitter
            const latency = baseLatency + jitter

            // Physics residual with λ_physics = 0.85 bias
            const physicsLoss = 0.012 + Math.random() * 0.008 // Low residual indicates good physics alignment

            // Hausdorff distance (Pocket Bunny scan drift)
            const hausdorff = 0.015 + Math.random() * 0.025 // Target < 0.045nm

            // Pacejka tire slip angle (realistic tire model)
            const slipAngle = (Math.random() - 0.5) * 0.15 // ±0.15 rad

            // Idempotency check: random bit flip simulation
            const idempotent = Math.random() > 0.001 // 0.1% chance of failure

            // FPGA cycle counter
            const fpgaCycles = Math.floor(120000 + Math.random() * 5000)

            const newMetric: PINNMetrics = {
                timestamp: now,
                stateEstimationLatency: latency,
                physicsResidual: physicsLoss,
                hausdorffDistance: hausdorff,
                pacejkaSlipAngle: slipAngle,
                idempotencyValid: idempotent,
                fpgaCycleCount: fpgaCycles
            }

            setCurrentMetric(newMetric)
            setMetrics((prev: PINNMetrics[]) => [...prev.slice(-100), newMetric])

            // Fail-closed trigger conditions
            if (latency > 1.2) {
                setFailClosedTriggered(true)
                setCalibrationStatus('fail-closed')
            }

            if (hausdorff > 0.045) {
                setFailClosedTriggered(true)
                setCalibrationStatus('fail-closed')
            }

            if (!idempotent) {
                setFailClosedTriggered(true)
                setCalibrationStatus('fail-closed')
            }

            // Stream metrics to Code Sight Observability Layer
            if (codeSight) {
                codeSight.injectMetric('PhyAtteN_R32.latency', 'state_estimation_ms', latency)
                codeSight.injectMetric('PhyAtteN_R32.physics', 'residual_loss', physicsLoss)
                codeSight.injectMetric('PhyAtteN_R32.geometry', 'hausdorff_nm', hausdorff)
                codeSight.injectMetric('PhyAtteN_R32.idempotency', 'valid_bit', idempotent ? 1 : 0)

                // Trigger dynamic sight point log for violations
                if (latency > 1.2 || hausdorff > 0.045 || !idempotent) {
                    codeSight.injectMetric('PhyAtteN_R32.arbitrator', 'VIOLATION_TRIGGERED', 1)
                }
            }

        }, 100) // 10Hz update rate

        return () => clearInterval(interval)
    }, [isActive, mode, codeSight])


    const getLatencyStatus = () => {
        if (currentMetric.stateEstimationLatency < 1.0) return { color: '#4CAF50', text: 'NOMINAL' }
        if (currentMetric.stateEstimationLatency < 1.2) return { color: '#FF9800', text: 'MARGINAL' }
        return { color: '#f44336', text: 'VIOLATION' }
    }

    const getHausdorffStatus = () => {
        if (currentMetric.hausdorffDistance < 0.030) return { color: '#4CAF50', text: 'ALIGNED' }
        if (currentMetric.hausdorffDistance < 0.045) return { color: '#FF9800', text: 'DRIFT' }
        return { color: '#f44336', text: 'HARD-KILL' }
    }

    return (
        <div className="card pinn-arbitration-panel">
            <div className="panel-header">
                <h2>⚡ PhyAtteN_R32 PINN Arbitration Layer</h2>
                <div
                    className={`calibration-status-badge status-badge status-${calibrationStatus}`}
                >
                    {calibrationStatus.toUpperCase()}
                </div>
            </div>

            {
                failClosedTriggered && (
                    <div className="fail-closed-alert">
                        🚨 FAIL-CLOSED SEQUENCE TRIGGERED - CHAOS EMERALD STATE LOCKED 🚨
                    </div>
                )
            }

            <div className="pinn-metrics-grid">
                {/* State Estimation Latency */}
                <div className="metric-card">
                    <div className="metric-header">
                        <span className="metric-label">State-Estimation Latency</span>
                        <span
                            className={`metric-status metric-status-text status-${getLatencyStatus().text.toLowerCase()}`}
                        >
                            {getLatencyStatus().text}
                        </span>
                    </div>
                    <div className="metric-value-large">
                        {currentMetric.stateEstimationLatency.toFixed(3)} <span className="unit">ms</span>
                    </div>
                    <div className="metric-threshold">
                        Target: &lt; 1.200ms | Current: {(currentMetric.stateEstimationLatency / 1.2 * 100).toFixed(1)}%
                    </div>
                </div>

                {/* Physics Residual */}
                <div className="metric-card">
                    <div className="metric-header">
                        <span className="metric-label">Physics Residual (λ=0.85)</span>
                        <span
                            className={`metric-status metric-status-text ${currentMetric.physicsResidual < 0.020 ? 'status-converged' : 'status-optimizing'}`}
                        >
                            {currentMetric.physicsResidual < 0.020 ? 'CONVERGED' : 'OPTIMIZING'}
                        </span>
                    </div>
                    <div className="metric-value-large">
                        {currentMetric.physicsResidual.toFixed(4)} <span className="unit">loss</span>
                    </div>
                    <div className="metric-threshold">
                        Pacejka Slip Angle: {(currentMetric.pacejkaSlipAngle * 180 / Math.PI).toFixed(2)}°
                    </div>
                </div>

                {/* Hausdorff Distance */}
                <div className="metric-card">
                    <div className="metric-header">
                        <span className="metric-label">Hausdorff Distance (Pocket Bunny)</span>
                        <span
                            className={`metric-status metric-status-text status-${getHausdorffStatus().text.toLowerCase().replace(' ', '-')}`}
                        >
                            {getHausdorffStatus().text}
                        </span>
                    </div>
                    <div className="metric-value-large">
                        {currentMetric.hausdorffDistance.toFixed(4)} <span className="unit">nm</span>
                    </div>
                    <div className="metric-threshold">
                        Hard-Kill Threshold: 0.0450nm | Margin: {((0.045 - currentMetric.hausdorffDistance) / 0.045 * 100).toFixed(1)}%
                    </div>
                </div>

                {/* Idempotency Validator */}
                <div className="metric-card">
                    <div className="metric-header">
                        <span className="metric-label">Sovereign Event Schema</span>
                        <span
                            className={`metric-status metric-status-text ${currentMetric.idempotencyValid ? 'status-valid' : 'status-corrupted'}`}
                        >
                            {currentMetric.idempotencyValid ? 'VALID' : 'CORRUPTED'}
                        </span>
                    </div>
                    <div className="metric-value-large">
                        {currentMetric.idempotencyValid ? '✓' : '✗'} <span className="unit">Byte-Consistent</span>
                    </div>
                    <div className="metric-threshold">
                        FPGA Cycles: {currentMetric.fpgaCycleCount.toLocaleString()}
                    </div>
                </div>
            </div>

            {/* Real-time Charts */}
            <div className="pinn-charts">
                <div className="chart-section">
                    <h3>⏱️ State-Estimation Latency Timeline</h3>
                    <ResponsiveContainer width="100%" height={180}>
                        <LineChart data={metrics.slice(-50)}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#2a2a3e" />
                            <XAxis
                                dataKey="timestamp"
                                stroke="#a0a0a0"
                                tickFormatter={(ts) => new Date(ts).toLocaleTimeString()}
                            />
                            <YAxis stroke="#a0a0a0" domain={[0.5, 1.5]} />
                            <Tooltip
                                formatter={(value: number) => `${value.toFixed(3)}ms`}
                            />
                            <ReferenceLine y={1.2} stroke="#f44336" strokeDasharray="5 5" label="1.2ms Limit" />
                            <Line
                                type="monotone"
                                dataKey="stateEstimationLatency"
                                stroke="#00BCD4"
                                strokeWidth={2}
                                dot={false}
                                name="Latency"
                            />
                        </LineChart>
                    </ResponsiveContainer>
                </div>

                <div className="chart-section">
                    <h3>📐 Hausdorff Drift & Physics Residual</h3>
                    <ResponsiveContainer width="100%" height={180}>
                        <LineChart data={metrics.slice(-50)}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#2a2a3e" />
                            <XAxis
                                dataKey="timestamp"
                                stroke="#a0a0a0"
                                tickFormatter={(ts) => new Date(ts).toLocaleTimeString()}
                            />
                            <YAxis stroke="#a0a0a0" />
                            <Tooltip />
                            <ReferenceLine y={0.045} stroke="#f44336" strokeDasharray="5 5" label="Hausdorff Limit" />
                            <Line
                                type="monotone"
                                dataKey="hausdorffDistance"
                                stroke="#FF9800"
                                strokeWidth={2}
                                dot={false}
                                name="Hausdorff (nm)"
                            />
                            <Line
                                type="monotone"
                                dataKey="physicsResidual"
                                stroke="#9C27B0"
                                strokeWidth={2}
                                dot={false}
                                name="Physics Loss"
                            />
                        </LineChart>
                    </ResponsiveContainer>
                </div>
            </div>

            <div className="first-light-controls">
                <button
                    className="btn-danger"
                    onClick={() => {
                        setFailClosedTriggered(true)
                        setCalibrationStatus('fail-closed')
                    }}
                    disabled={calibrationStatus === 'fail-closed'}
                >
                    🔒 Inject Idempotency Violation
                </button>
                <button
                    className="btn-secondary"
                    onClick={() => {
                        setMetrics([])
                        setFailClosedTriggered(false)
                        setCalibrationStatus('standby')
                    }}
                >
                    🔄 Reset PINN State
                </button>
            </div>
        </div >
    )
}

export default PINNArbitrationPanel
