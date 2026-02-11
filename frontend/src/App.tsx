import { useState, useEffect } from 'react'
import './App.css'

interface GameState {
    current_tick: number
    total_companies: number
    market_data?: any
}

interface Company {
    company_id: string
    company_name: string
    industry_sector: string
    is_ai: boolean
    employees: number
    cash_usd: number
    revenue_usd: number
}

function App() {
    const [gameState, setGameState] = useState<GameState | null>(null)
    const [companies, setCompanies] = useState<Company[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    // New company form
    const [companyName, setCompanyName] = useState('')
    const [capital, setCapital] = useState('100000')
    const [sector, setSector] = useState('TECH')

    const API_BASE = '/api'

    useEffect(() => {
        // Load initial game state
        fetchGameState()
        fetchCompanies()
    }, [])

    const fetchGameState = async () => {
        try {
            const res = await fetch(`${API_BASE}/game/state`)
            const data = await res.json()
            setGameState(data)
            setLoading(false)
        } catch (err) {
            setError('Failed to connect to game server')
            setLoading(false)
        }
    }

    const fetchCompanies = async () => {
        try {
            const res = await fetch(`${API_BASE}/game/companies`)
            const data = await res.json()
            setCompanies(data.companies || [])
        } catch (err) {
            console.error('Failed to fetch companies:', err)
        }
    }

    const advanceTick = async () => {
        try {
            const res = await fetch(`${API_BASE}/game/tick`, { method: 'POST' })
            const data = await res.json()
            setGameState({ current_tick: data.current_tick, total_companies: data.market_state.total_companies })
            fetchCompanies()
        } catch (err) {
            setError('Failed to advance tick')
        }
    }

    const registerCompany = async (e: React.FormEvent) => {
        e.preventDefault()
        try {
            const res = await fetch(`${API_BASE}/company/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    company_name: companyName,
                    founding_capital_usd: parseFloat(capital),
                    industry_sector: sector,
                    sovereign_signature: 'user_' + Date.now()
                })
            })

            if (res.ok) {
                setCompanyName('')
                fetchCompanies()
                fetchGameState()
            } else {
                const error = await res.json()
                setError(error.detail || 'Failed to register company')
            }
        } catch (err) {
            setError('Failed to register company')
        }
    }

    const executeOperation = async (companyId: string, opType: string) => {
        try {
            const params = opType === 'HIRE' ? { num_employees: 5 } :
                opType === 'PRODUCE' ? { units: 100 } :
                    opType === 'MARKET' ? { units: 50 } : {}

            await fetch(`${API_BASE}/company/${companyId}/operation`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    operation_type: opType,
                    params
                })
            })

            // Refresh after a brief delay
            setTimeout(() => fetchCompanies(), 500)
        } catch (err) {
            setError(`Failed to execute ${opType}`)
        }
    }

    if (loading) {
        return <div className="container"><h2>Connecting to game engine...</h2></div>
    }

    if (error) {
        return (
            <div className="container">
                <h2>Error: {error}</h2>
                <button onClick={() => window.location.reload()}>Retry</button>
            </div>
        )
    }

    return (
        <div className="container">
            <header>
                <h1>🏢 Enterprise Business Game</h1>
                <div className="game-status">
                    <span>Tick: <strong>{gameState?.current_tick || 0}</strong></span>
                    <span>Companies: <strong>{gameState?.total_companies || 0}</strong></span>
                    <button onClick={advanceTick} className="btn-primary">
                        ⏩ Advance Tick
                    </button>
                </div>
            </header>

            <div className="grid">
                <section className="card">
                    <h2>Register New Company</h2>
                    <form onSubmit={registerCompany}>
                        <input
                            type="text"
                            placeholder="Company Name"
                            value={companyName}
                            onChange={(e) => setCompanyName(e.target.value)}
                            required
                        />
                        <input
                            type="number"
                            placeholder="Capital (USD)"
                            value={capital}
                            onChange={(e) => setCapital(e.target.value)}
                            required
                        />
                        <select value={sector} onChange={(e) => setSector(e.target.value)}>
                            <option value="TECH">Technology</option>
                            <option value="MANUFACTURING">Manufacturing</option>
                            <option value="SERVICES">Services</option>
                            <option value="FINANCE">Finance</option>
                        </select>
                        <button type="submit" className="btn-primary">
                            Register Company
                        </button>
                    </form>
                </section>

                <section className="card">
                    <h2>Active Companies ({companies.length})</h2>
                    <div className="companies-list">
                        {companies.length === 0 ? (
                            <p>No companies registered yet</p>
                        ) : (
                            companies.map(company => (
                                <div key={company.company_id} className="company-card">
                                    <h3>{company.company_name}</h3>
                                    <div className="company-stats">
                                        <span>💰 ${company.cash_usd.toLocaleString()}</span>
                                        <span>👥 {company.employees} employees</span>
                                        <span>📊 {company.industry_sector}</span>
                                    </div>
                                    <div className="company-revenue">
                                        Revenue: ${company.revenue_usd.toLocaleString()}
                                    </div>
                                    <div className="company-actions">
                                        <button onClick={() => executeOperation(company.company_id, 'HIRE')} className="btn-sm">Hire</button>
                                        <button onClick={() => executeOperation(company.company_id, 'PRODUCE')} className="btn-sm">Produce</button>
                                        <button onClick={() => executeOperation(company.company_id, 'MARKET')} className="btn-sm">Market</button>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </section>
            </div>
        </div>
    )
}

export default App
