import React from 'react'

interface TelemetryPanelProps {
    telemetry: any[]
    isRunning: boolean
}

const TelemetryPanel: React.FC<TelemetryPanelProps> = ({ telemetry, isRunning }) => {
    const throttleRef = React.useRef<HTMLDivElement>(null)
    const brakeRef = React.useRef<HTMLDivElement>(null)
    const steeringRef = React.useRef<HTMLDivElement>(null)

    React.useEffect(() => {
        if (throttleRef.current) {
            throttleRef.current.style.setProperty('--gauge-width', `${latest.throttle * 100}%`)
        }
        if (brakeRef.current) {
            brakeRef.current.style.setProperty('--gauge-width', `${latest.brake * 100}%`)
        }
        if (steeringRef.current) {
            steeringRef.current.style.setProperty('--steering-pos', `${latest.steering * 100}px`)
        }
    }, [latest.throttle, latest.brake, latest.steering])

    return (
        <div className="card telemetry-panel">
            <h2>📡 Live Telemetry</h2>

            {latest ? (
                <div className="telemetry-grid">
                    <div className="telemetry-item">
                        <span className="label">Speed</span>
                        <span className="value">{latest.speed.toFixed(1)} m/s</span>
                        <span className="sub">{(latest.speed * 3.6).toFixed(0)} km/h</span>
                    </div>

                    <div className="telemetry-item">
                        <span className="label">Throttle</span>
                        <div className="gauge">
                            <div ref={throttleRef} className="gauge-fill throttle dynamic" />
                        </div>
                        <span className="value">{(latest.throttle * 100).toFixed(0)}%</span>
                    </div>

                    <div className="telemetry-item">
                        <span className="label">Brake</span>
                        <div className="gauge">
                            <div ref={brakeRef} className="gauge-fill brake dynamic" />
                        </div>
                        <span className="value">{(latest.brake * 100).toFixed(0)}%</span>
                    </div>

                    <div className="telemetry-item">
                        <span className="label">Steering</span>
                        <div className="steering-indicator">
                            <div className="steering-center" />
                            <div
                                ref={steeringRef}
                                className="steering-pointer dynamic"
                            />
                        </div>
                        <span className="value">{latest.steering.toFixed(3)}</span>
                    </div>

                    <div className="telemetry-item">
                        <span className="label">Curvature</span>
                        <span className="value">{latest.curvature.toFixed(4)} 1/m</span>
                    </div>

                    <div className="telemetry-item">
                        <span className="label">Tick</span>
                        <span className="value">{latest.tick}</span>
                    </div>

                    {isRunning && (
                        <div className="recording-indicator">
                            <span className="rec-dot"></span>
                            Recording
                        </div>
                    )}
                </div>
            ) : (
                <div className="empty-state">
                    <p>No telemetry data</p>
                    <p>Start a simulation to see live data</p>
                </div>
            )}
        </div>
    )
}

export default TelemetryPanel
