/**
 * Code Sight Client - TypeScript/React Integration
 * 
 * Provides real-time visualization of Code Sight observations
 * and multimodal agent execution tracking for the racing dashboard.
 */

import { useState, useEffect } from 'react'

export enum Modality {
    TEXT_GENERATION = "text_generation",
    CODE_EXECUTION = "code_execution",
    VISION_PROCESSING = "vision_processing",
    SIMULATION = "simulation",
    INFERENCE = "inference",
    PLANNING = "planning",
    TOOL_CALLING = "tool_calling"
}

export enum ActionType {
    LOG = "log",
    ALERT = "alert",
    SNAPSHOT = "snapshot",
    FAIL_CLOSED = "fail_closed",
    METRIC = "metric"
}

export interface SightPoint {
    name: string
    target: string
    modality: string
    metrics: string[]
    conditions: Record<string, any>
    action: string
    enabled: boolean
    timestamp: number
}

export interface Observation {
    sight_point_name: string
    timestamp: number
    modality: string
    metrics: Record<string, any>
    stack_trace: string
    agent_context: Record<string, any>
    merkle_hash: string
    parent_hash: string
}

export interface CodeSightStats {
    total_observations: number
    active_sight_points: number
    modalities_active: string[]
    chain_valid: boolean
    last_update: number
}

/**
 * Code Sight WebSocket client for real-time observation streaming
 */
export class CodeSightClient {
    private ws: WebSocket | null = null
    private observations: Observation[] = []
    private sightPoints: Map<string, SightPoint> = new Map()
    private listeners: Set<(obs: Observation) => void> = new Set()
    private statsListeners: Set<(stats: CodeSightStats) => void> = new Set()

    constructor(private wsUrl: string = "ws://localhost:8765") {
        this.connect()
    }

    private connect() {
        try {
            this.ws = new WebSocket(this.wsUrl)

            this.ws.onopen = () => {
                console.log('[CodeSight] Connected to observation stream')
            }

            this.ws.onmessage = (event) => {
                const data = JSON.parse(event.data)
                this.handleMessage(data)
            }

            this.ws.onerror = (error) => {
                console.error('[CodeSight] WebSocket error:', error)
            }

            this.ws.onclose = () => {
                console.log('[CodeSight] Disconnected, reconnecting in 2s...')
                setTimeout(() => this.connect(), 2000)
            }
        } catch (error) {
            console.error('[CodeSight] Failed to connect:', error)
        }
    }

    private handleMessage(data: any) {
        if (data.type === 'observation') {
            const obs: Observation = data.payload
            this.observations.push(obs)

            // Keep rolling window
            if (this.observations.length > 1000) {
                this.observations = this.observations.slice(-1000)
            }

            // Notify listeners
            this.listeners.forEach(listener => listener(obs))

            // Update stats
            this.updateStats()
        }
        else if (data.type === 'sight_point_registered') {
            const sp: SightPoint = data.payload
            this.sightPoints.set(sp.name, sp)
        }
    }

    private updateStats() {
        const stats: CodeSightStats = {
            total_observations: this.observations.length,
            active_sight_points: this.sightPoints.size,
            modalities_active: Array.from(new Set(
                this.observations.map(o => o.modality)
            )),
            chain_valid: true, // Would verify merkle chain
            last_update: Date.now()
        }

        this.statsListeners.forEach(listener => listener(stats))
    }

    public onObservation(callback: (obs: Observation) => void) {
        this.listeners.add(callback)
        return () => this.listeners.delete(callback)
    }

    public onStats(callback: (stats: CodeSightStats) => void) {
        this.statsListeners.add(callback)
        return () => this.statsListeners.delete(callback)
    }

    public getObservations(
        modality?: string,
        sightPoint?: string,
        limit: number = 100
    ): Observation[] {
        let results = this.observations.slice(-limit)

        if (modality) {
            results = results.filter(o => o.modality === modality)
        }

        if (sightPoint) {
            results = results.filter(o => o.sight_point_name === sightPoint)
        }

        return results
    }

    public getSightPoints(): SightPoint[] {
        return Array.from(this.sightPoints.values())
    }

    public injectMetric(target: string, metricName: string, threshold?: number) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                type: 'inject_metric',
                payload: { target, metricName, threshold }
            }))
        }
    }

    public injectLog(target: string, condition: string, message: string) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                type: 'inject_log',
                payload: { target, condition, message }
            }))
        }
    }

    public enableSightPoint(name: string) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                type: 'enable_sight_point',
                payload: { name }
            }))
        }
    }

    public disableSightPoint(name: string) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                type: 'disable_sight_point',
                payload: { name }
            }))
        }
    }
}

/**
 * React hook for Code Sight integration
 */
export function useCodeSight(wsUrl?: string) {
    const [client] = useState(() => new CodeSightClient(wsUrl))
    const [observations, setObservations] = useState<Observation[]>([])
    const [stats, setStats] = useState<CodeSightStats>({
        total_observations: 0,
        active_sight_points: 0,
        modalities_active: [],
        chain_valid: true,
        last_update: Date.now()
    })

    useEffect(() => {
        const unsubObs = client.onObservation((obs: Observation) => {
            setObservations((prev: Observation[]) => [...prev.slice(-100), obs])
        })

        const unsubStats = client.onStats((newStats: CodeSightStats) => {
            setStats(newStats)
        })

        return () => {
            unsubObs()
            unsubStats()
        }
    }, [client])

    return {
        observations,
        stats,
        client,
        sightPoints: client.getSightPoints()
    }
}

export default CodeSightClient
