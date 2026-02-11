import React from 'react'

interface TrackVisualizationProps {
    progress: number
    speed: number
}

const TrackVisualization: React.FC<TrackVisualizationProps> = ({ progress, speed }) => {
    // Simplified Nürburgring representation
    const trackSections = [
        { name: 'Hatzenbach', start: 0, end: 0.06, color: '#4CAF50' },
        { name: 'Flugplatz', start: 0.06, end: 0.12, color: '#2196F3' },
        { name: 'Aremberg', start: 0.12, end: 0.18, color: '#FF9800' },
        { name: 'Fuchsröhre', start: 0.18, end: 0.26, color: '#E91E63' },
        { name: 'Adenauer Forst', start: 0.26, end: 0.35, color: '#9C27B0' },
        { name: 'Karussell', start: 0.35, end: 0.46, color: '#00BCD4' },
        { name: 'Pflanzgarten', start: 0.46, end: 0.58, color: '#CDDC39' },
        { name: 'Schwalbenschwanz', start: 0.58, end: 0.70, color: '#FFC107' },
        { name: 'Döttinger Höhe', start: 0.70, end: 0.89, color: '#795548' },
        { name: 'Antoniusbuche', start: 0.89, end: 1.0, color: '#607D8B' }
    ]

    const currentSection = trackSections.find(s => progress >= s.start && progress < s.end)

    const sectionRef = React.useRef<HTMLSpanElement>(null)
    const progressRef = React.useRef<HTMLDivElement>(null)

    React.useEffect(() => {
        if (sectionRef.current) {
            sectionRef.current.style.setProperty('--section-color', currentSection?.color || null)
        }
        if (progressRef.current) {
            progressRef.current.style.setProperty('--progress-width', `${progress * 100}%`)
        }
    }, [currentSection, progress])

    return (
        <div className="card track-visualization">
            <h2>🏁 Track Position</h2>

            <div className="track-map">
                <svg viewBox="0 0 400 300" className="track-svg">
                    {/* Simplified track outline */}
                    <path
                        d="M 50 150 Q 100 50, 200 50 Q 300 50, 350 150 Q 350 250, 200 250 Q 100 250, 50 150 Z"
                        fill="none"
                        stroke="#2a2a3e"
                        strokeWidth="30"
                    />

                    {/* Progress indicator */}
                    <circle
                        cx={200 + Math.cos(progress * Math.PI * 2) * 130}
                        cy={150 + Math.sin(progress * Math.PI * 2) * 100}
                        r="8"
                        fill={currentSection?.color || '#4CAF50'}
                        className="car-marker"
                    />
                </svg>
            </div>

            <div className="section-info">
                <div className="current-section">
                    <span className="label">Current Section:</span>
                    <span ref={sectionRef} className="value current-section-value">
                        {currentSection?.name || 'Start/Finish'}
                    </span>
                </div>

                <div className="progress-bar">
                    <div ref={progressRef} className="progress-fill dynamic" />
                </div>

                <div className="track-stats">
                    <div>Track Length: 20.8 km</div>
                    <div>Current Speed: {(speed * 3.6).toFixed(0)} km/h</div>
                </div>
            </div>
        </div>
    )
}

export default TrackVisualization
