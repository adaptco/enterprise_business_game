import React, { useState, useEffect, useRef, useLayoutEffect } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import CodeSightClient, { Observation, SightPoint, Modality, CodeSightStats } from '../lib/CodeSightClient'

interface CodeSightDebuggerProps {
    wsUrl?: string
}

interface ModalityBarProps {
    modality: string
    count: number
    total: number
}

const ModalityBar: React.FC<ModalityBarProps> = ({ modality, count, total }) => {
    const width = `${(count / total) * 100}%`
    const ref = useRef<HTMLDivElement>(null)

    useLayoutEffect(() => {
        if (ref.current) {
            ref.current.style.setProperty('--modality-width', width)
        }
    }, [width])

    return (
        <div
            ref={ref}
            className={`modality-bar bg-modality-${modality.split('_').join('-')}`}
        />
    )
}

const CodeSightDebugger: React.FC<CodeSightDebuggerProps> = ({ wsUrl }) => {
    const [client] = useState(() => new CodeSightClient(wsUrl))
    const [observations, setObservations] = useState<Observation[]>([])
    const [sightPoints, setSightPoints] = useState<SightPoint[]>([])
    const [selectedModality, setSelectedModality] = useState<string>('all')
    const [selectedSightPoint, setSelectedSightPoint] = useState<string>('all')
    const [stats, setStats] = useState<CodeSightStats>({
        total_observations: 0,
        active_sight_points: 0,
        modalities_active: [] as string[],
        chain_valid: true,
        last_update: Date.now()
    })

    // Metric injection form state
    const [injectTarget, setInjectTarget] = useState('')
    const [injectMetric, setInjectMetric] = useState('')
    const [injectThreshold, setInjectThreshold] = useState('')

    useEffect(() => {
        const unsubObs = client.onObservation((obs: Observation) => {
            setObservations(prev => [...prev.slice(-200), obs])
        })

        const unsubStats = client.onStats((newStats) => {
            setStats(newStats)
        })

        // Periodically refresh sight points
        const interval = setInterval(() => {
            setSightPoints(client.getSightPoints())
        }, 1000)

        return () => {
            unsubObs()
            unsubStats()
            clearInterval(interval)
        }
    }, [client])

    const filteredObservations = observations.filter(obs => {
        if (selectedModality !== 'all' && obs.modality !== selectedModality) return false
        if (selectedSightPoint !== 'all' && obs.sight_point_name !== selectedSightPoint) return false
        return true
    })

    const handleInjectMetric = () => {
        if (injectTarget && injectMetric) {
            const threshold = injectThreshold ? parseFloat(injectThreshold) : undefined
            client.injectMetric(injectTarget, injectMetric, threshold)
            setInjectTarget('')
            setInjectMetric('')
            setInjectThreshold('')
        }
    }

    // Prepare latency timeline data
    const latencyData = filteredObservations
        .filter(obs => obs.metrics.latency_ms !== undefined)
        .slice(-50)
        .map(obs => ({
            timestamp: new Date(obs.timestamp * 1000).toLocaleTimeString(),
            latency: obs.metrics.latency_ms,
            sightPoint: obs.sight_point_name
        }))

    // Modality distribution
    const modalityCount: Record<string, number> = {}
    observations.forEach(obs => {
        modalityCount[obs.modality] = (modalityCount[obs.modality] || 0) + 1
    })



    return (
        <div className="code-sight-debugger">
            <div className="debugger-header">
                <h2>🔍 Code Sight - Live Agent Debugger</h2>
                <div className={`chain-status ${stats.chain_valid ? 'valid' : 'corrupted'}`}>
                    {stats.chain_valid ? '✓ Chain Valid' : '✗ Chain Corrupted'}
                </div>
            </div>

            {/* Stats Overview */}
            <div className="stats-grid">
                <div className="stat-card">
                    <span className="stat-label">Observations</span>
                    <span className="stat-value">{stats.total_observations}</span>
                </div>
                <div className="stat-card">
                    <span className="stat-label">Active Sight Points</span>
                    <span className="stat-value">{stats.active_sight_points}</span>
                </div>
                <div className="stat-card">
                    <span className="stat-label">Active Modalities</span>
                    <span className="stat-value">{stats.modalities_active.length}</span>
                </div>
            </div>

            {/* Modality Distribution */}
            <div className="card modality-viz">
                <h3>📊 Multimodal Activity Distribution</h3>
                <div className="modality-bars">
                    {Object.entries(modalityCount).map(([modality, count]) => (
                        <div key={modality} className="modality-bar-container">
                            <div className="modality-label">{modality}</div>
                            <div className="modality-bar-wrapper">
                                <ModalityBar
                                    modality={modality}
                                    count={count}
                                    total={observations.length}
                                />
                                <span className="modality-count">{count}</span>
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Latency Timeline */}
            {latencyData.length > 0 && (
                <div className="card">
                    <h3>⏱️ Execution Latency Timeline</h3>
                    <ResponsiveContainer width="100%" height={200}>
                        <LineChart data={latencyData}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#2a2a3e" />
                            <XAxis dataKey="timestamp" stroke="#a0a0a0" />
                            <YAxis stroke="#a0a0a0" />
                            <Tooltip />
                            <Line
                                type="monotone"
                                dataKey="latency"
                                stroke="#00BCD4"
                                strokeWidth={2}
                                dot={false}
                            />
                        </LineChart>
                    </ResponsiveContainer>
                </div>
            )}

            {/* Dynamic Instrumentation Panel */}
            <div className="card inject-panel">
                <h3>💉 Dynamic Instrumentation</h3>
                <div className="inject-form">
                    <input
                        type="text"
                        placeholder="Target (e.g., PhyAtteN_R32.forward)"
                        value={injectTarget}
                        onChange={(e) => setInjectTarget(e.target.value)}
                        className="inject-input"
                    />
                    <input
                        type="text"
                        placeholder="Metric name"
                        value={injectMetric}
                        onChange={(e) => setInjectMetric(e.target.value)}
                        className="inject-input"
                    />
                    <input
                        type="number"
                        step="0.001"
                        placeholder="Alert threshold (optional)"
                        value={injectThreshold}
                        onChange={(e) => setInjectThreshold(e.target.value)}
                        className="inject-input"
                    />
                    <button
                        onClick={handleInjectMetric}
                        className="btn-primary"
                        disabled={!injectTarget || !injectMetric}
                    >
                        Inject Metric
                    </button>
                </div>
            </div>

            {/* Sight Points Manager */}
            <div className="card sight-points-panel">
                <h3>🎯 Active Sight Points</h3>
                <div className="sight-points-list">
                    {sightPoints.length === 0 ? (
                        <div className="empty-state">No sight points registered</div>
                    ) : (
                        sightPoints.map(sp => (
                            <div key={sp.name} className="sight-point-item">
                                <div className="sight-point-header">
                                    <span className="sight-point-name">{sp.name}</span>
                                    <span
                                        className={`sight-point-modality-badge bg-modality-${sp.modality.split('_').join('-')}`}
                                    >
                                        {sp.modality}
                                    </span>
                                </div>
                                <div className="sight-point-target">{sp.target}</div>
                                <div className="sight-point-metrics">
                                    Metrics: {sp.metrics.join(', ')}
                                </div>
                                <button
                                    onClick={() => sp.enabled ?
                                        client.disableSightPoint(sp.name) :
                                        client.enableSightPoint(sp.name)
                                    }
                                    className={`btn-sight-point-toggle ${sp.enabled ? "btn-danger" : "btn-secondary"}`}
                                >
                                    {sp.enabled ? 'Disable' : 'Enable'}
                                </button>
                            </div>
                        ))
                    )}
                </div>
            </div>

            {/* Observation Log */}
            <div className="card observation-log">
                <h3>📋 Observation Stream</h3>

                <div className="log-filters">
                    <select
                        value={selectedModality}
                        onChange={(e) => setSelectedModality(e.target.value)}
                        className="filter-select"
                        aria-label="Filter observations by modality"
                    >
                        <option value="all">All Modalities</option>
                        {Object.values(Modality).map(m => (
                            <option key={m} value={m}>{m}</option>
                        ))}
                    </select>

                    <select
                        value={selectedSightPoint}
                        onChange={(e) => setSelectedSightPoint(e.target.value)}
                        className="filter-select"
                        aria-label="Filter observations by sight point"
                    >
                        <option value="all">All Sight Points</option>
                        {sightPoints.map(sp => (
                            <option key={sp.name} value={sp.name}>{sp.name}</option>
                        ))}
                    </select>
                </div>

                <div className="observation-list">
                    {filteredObservations.length === 0 ? (
                        <div className="empty-state">No observations yet</div>
                    ) : (
                        filteredObservations.slice().reverse().slice(0, 20).map((obs, idx) => (
                            <div key={`${obs.merkle_hash}-${idx}`} className="observation-item">
                                <div className="observation-header">
                                    <span className="observation-time">
                                        {new Date(obs.timestamp * 1000).toLocaleTimeString()}
                                    </span>
                                    <span
                                        className={`observation-modality-text modality-${obs.modality.split('_').join('-')}`}
                                    >
                                        {obs.modality}
                                    </span>
                                    <span className="observation-sight-point">
                                        {obs.sight_point_name}
                                    </span>
                                </div>
                                <div className="observation-metrics">
                                    {Object.entries(obs.metrics).map(([key, value]) => (
                                        <span key={key} className="metric-badge">
                                            {key}: {typeof value === 'number' ? value.toFixed(3) : value}
                                        </span>
                                    ))}
                                </div>
                                <div className="observation-hash" title={obs.merkle_hash}>
                                    Hash: {obs.merkle_hash.substring(0, 12)}...
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>


        </div>
    )
}

export default CodeSightDebugger
