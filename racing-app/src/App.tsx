import { useState, useEffect } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import './App.css'
import TrackVisualization from './components/TrackVisualization'
import TelemetryPanel from './components/TelemetryPanel'
import ModelManager from './components/ModelManager'
import CodeSightDebugger from './components/CodeSightDebugger'
import PINNArbitrationPanel from './components/PINNArbitrationPanel'

interface SimState {
    tick: number
    lap: number
    track_progress: number
    speed_mps: number
    is_running: boolean
    mode: 'expert' | 'ai' | 'stopped'
}

interface TelemetryData {
    tick: number
    speed: number
    throttle: number
    brake: number
    steering: number
    curvature: number
}

function App() {
    const [simState, setSimState] = useState<SimState>({
        tick: 0,
        lap: 0,
        track_progress: 0,
        speed_mps: 0,
        is_running: false,
        mode: 'stopped'
    })

    const [telemetry, setTelemetry] = useState<TelemetryData[]>([])
    const [activeTab, setActiveTab] = useState<'sim' | 'training' | 'models' | 'debug' | 'audit'>('audit')
    const [auditActive, setAuditActive] = useState(false)

    // Mock data for demonstration
    useEffect(() => {
        // In production, this would fetch from the backend API
        const interval = setInterval(() => {
            if (simState.is_running) {
                setSimState(prev => ({
                    ...prev,
                    tick: prev.tick + 1,
                    track_progress: (prev.track_progress + 0.001) % 1.0,
                    speed_mps: 40 + Math.random() * 20
                }))

                // Add telemetry point
                setTelemetry(prev => {
                    const newPoint = {
                        tick: simState.tick,
                        speed: simState.speed_mps,
                        throttle: 0.8 + Math.random() * 0.2,
                        brake: Math.random() < 0.1 ? Math.random() * 0.5 : 0,
                        steering: (Math.random() - 0.5) * 0.4,
                        curvature: Math.sin(simState.track_progress * Math.PI * 4) * 0.03
                    }
                    return [...prev.slice(-100), newPoint]
                })
            }
        }, 100)

        return () => clearInterval(interval)
    }, [simState.is_running, simState.tick, simState.speed_mps, simState.track_progress])

    const startExpertRun = () => {
        setSimState(prev => ({ ...prev, is_running: true, mode: 'expert', tick: 0 }))
        setTelemetry([])
    }

    const startAIRun = () => {
        setSimState(prev => ({ ...prev, is_running: true, mode: 'ai', tick: 0 }))
        setTelemetry([])
    }

    const stopSimulation = () => {
        setSimState(prev => ({ ...prev, is_running: false, mode: 'stopped' }))
    }

    const exportTelemetry = () => {
        const dataStr = JSON.stringify(telemetry, null, 2)
        const dataBlob = new Blob([dataStr], { type: 'application/json' })
        const url = URL.createObjectURL(dataBlob)
        const link = document.createElement('a')
        link.href = url
        link.download = `telemetry_${Date.now()}.json`
        link.click()
    }

    return (
        <div className="app">
            <header className="header">
                <div className="header-content">
                    <h1>🏎️ Nürburgring AI Racing Simulator</h1>
                    <div className="sim-status">
                        <span className={`status-indicator ${simState.is_running ? 'active' : 'inactive'}`}>
                            {simState.is_running ? '● RUNNING' : '○ STOPPED'}
                        </span>
                        <span className="mode-badge">{simState.mode.toUpperCase()}</span>
                    </div>
                </div>

                <nav className="tab-nav">
                    <button
                        className={activeTab === 'audit' ? 'active' : ''}
                        onClick={() => setActiveTab('audit')}
                    >
                        🛡️ Sovereign Audit
                    </button>
                    <button
                        className={activeTab === 'sim' ? 'active' : ''}
                        onClick={() => setActiveTab('sim')}
                    >
                        🎮 Simulator
                    </button>
                    <button
                        className={activeTab === 'training' ? 'active' : ''}
                        onClick={() => setActiveTab('training')}
                    >
                        📊 Training Data
                    </button>
                    <button
                        className={activeTab === 'models' ? 'active' : ''}
                        onClick={() => setActiveTab('models')}
                    >
                        🤖 AI Models
                    </button>
                    <button
                        className={activeTab === 'debug' ? 'active' : ''}
                        onClick={() => setActiveTab('debug')}
                    >
                        🔍 Observability
                    </button>
                </nav>
            </header>

            <main className="main-content">
                {activeTab === 'audit' && (
                    <div className="audit-tab">
                        <div className="card control-panel">
                            <h2>Sovereign Deployment: Audit & Synthesis Monitor</h2>
                            <p className="info-text">
                                Status: <strong>{auditActive ? 'SEALED_GOLD EXECUTIVE RUN' : 'STANDBY'}</strong> |
                                Mode: <strong>FIRST LIGHT</strong> |
                                Security: <strong>OBSIDIAN LOCK</strong>
                            </p>

                            {!auditActive ? (
                                <button
                                    className="btn-primary btn-trigger"
                                    onClick={() => setAuditActive(true)}
                                >
                                    🧬 TRIGGER RUN [High-Fidelity Audit]
                                </button>
                            ) : (
                                <button
                                    className="btn-danger"
                                    onClick={() => setAuditActive(false)}
                                >
                                    ⏹ TERMINATE AUDIT
                                </button>
                            )}
                        </div>

                        <PINNArbitrationPanel
                            isActive={auditActive}
                            mode="first_light"
                        />
                    </div>
                )}

                {activeTab === 'debug' && (
                    <CodeSightDebugger wsUrl="ws://localhost:8765" />
                )}
                {activeTab === 'sim' && (
                    <div className="sim-tab">
                        <div className="control-panel card">
                            <h2>Simulation Control</h2>

                            <div className="stats-grid">
                                <div className="stat-card">
                                    <span className="stat-label">Tick</span>
                                    <span className="stat-value">{simState.tick}</span>
                                </div>
                                <div className="stat-card">
                                    <span className="stat-label">Lap</span>
                                    <span className="stat-value">{simState.lap}</span>
                                </div>
                                <div className="stat-card">
                                    <span className="stat-label">Progress</span>
                                    <span className="stat-value">{(simState.track_progress * 100).toFixed(1)}%</span>
                                </div>
                                <div className="stat-card">
                                    <span className="stat-label">Speed</span>
                                    <span className="stat-value">{simState.speed_mps.toFixed(1)} m/s</span>
                                </div>
                            </div>

                            <div className="control-buttons">
                                <button
                                    className="btn-primary"
                                    onClick={startExpertRun}
                                    disabled={simState.is_running}
                                >
                                    🎯 Expert Run
                                </button>
                                <button
                                    className="btn-secondary"
                                    onClick={startAIRun}
                                    disabled={simState.is_running}
                                >
                                    🤖 AI Run
                                </button>
                                <button
                                    className="btn-danger"
                                    onClick={stopSimulation}
                                    disabled={!simState.is_running}
                                >
                                    ⏹ Stop
                                </button>
                                <button
                                    className="btn-outline"
                                    onClick={exportTelemetry}
                                    disabled={telemetry.length === 0}
                                >
                                    💾 Export
                                </button>
                            </div>
                        </div>

                        <div className="visualization-grid">
                            <TrackVisualization
                                progress={simState.track_progress}
                                speed={simState.speed_mps}
                            />

                            <TelemetryPanel
                                telemetry={telemetry}
                                isRunning={simState.is_running}
                            />
                        </div>

                        <div className="telemetry-charts card">
                            <h2>Real-time Telemetry</h2>

                            <div className="chart-container">
                                <h3>Speed Profile</h3>
                                <ResponsiveContainer width="100%" height={200}>
                                    <LineChart data={telemetry.slice(-50)}>
                                        <CartesianGrid strokeDasharray="3 3" stroke="#2a2a3e" />
                                        <XAxis dataKey="tick" stroke="#a0a0a0" />
                                        <YAxis stroke="#a0a0a0" />
                                        <Tooltip />
                                        <Line type="monotone" dataKey="speed" stroke="#4CAF50" strokeWidth={2} dot={false} />
                                    </LineChart>
                                </ResponsiveContainer>
                            </div>

                            <div className="chart-container">
                                <h3>Control Inputs</h3>
                                <ResponsiveContainer width="100%" height={200}>
                                    <LineChart data={telemetry.slice(-50)}>
                                        <CartesianGrid strokeDasharray="3 3" stroke="#2a2a3e" />
                                        <XAxis dataKey="tick" stroke="#a0a0a0" />
                                        <YAxis stroke="#a0a0a0" />
                                        <Tooltip />
                                        <Legend />
                                        <Line type="monotone" dataKey="throttle" stroke="#4CAF50" strokeWidth={2} dot={false} />
                                        <Line type="monotone" dataKey="brake" stroke="#f44336" strokeWidth={2} dot={false} />
                                        <Line type="monotone" dataKey="steering" stroke="#2196F3" strokeWidth={2} dot={false} />
                                    </LineChart>
                                </ResponsiveContainer>
                            </div>
                        </div>
                    </div>
                )}

                {activeTab === 'training' && (
                    <div className="training-tab">
                        <div className="card">
                            <h2>Training Data Collection</h2>
                            <p className="info-text">
                                Recorded sessions: {telemetry.length > 0 ? '1' : '0'}
                                <span className="separator">•</span>
                                Total samples: {telemetry.length}
                            </p>

                            {telemetry.length > 0 && (
                                <div className="data-preview">
                                    <h3>Latest Session Preview</h3>
                                    <div className="data-stats">
                                        <div className="stat">
                                            <span className="label">Duration:</span>
                                            <span className="value">{(telemetry.length / 60).toFixed(1)}s</span>
                                        </div>
                                        <div className="stat">
                                            <span className="label">Avg Speed:</span>
                                            <span className="value">
                                                {(telemetry.reduce((sum, t) => sum + t.speed, 0) / telemetry.length).toFixed(1)} m/s
                                            </span>
                                        </div>
                                        <div className="stat">
                                            <span className="label">Max Speed:</span>
                                            <span className="value">
                                                {Math.max(...telemetry.map(t => t.speed)).toFixed(1)} m/s
                                            </span>
                                        </div>
                                    </div>

                                    <button className="btn-primary" onClick={exportTelemetry}>
                                        💾 Export Training Data (NDJSON)
                                    </button>
                                </div>
                            )}

                            {telemetry.length === 0 && (
                                <div className="empty-state">
                                    <p>No training data collected yet.</p>
                                    <p>Run an Expert or AI session from the Simulator tab to collect data.</p>
                                </div>
                            )}
                        </div>
                    </div>
                )}

                {activeTab === 'models' && (
                    <ModelManager />
                )}
            </main>
        </div>
    )
}

export default App
