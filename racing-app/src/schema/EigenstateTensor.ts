/**
 * @title Eigenstate Tensor Contract
 * @description The formal definition of the Eigenstate Tensor, representing the quantum state of the system.
 */

/**
 * @enum BillingPosture
 * Represents the current billing enforcement state.
 */
export enum BillingPosture {
    OK = 'OK',
    WARN = 'WARN',
    BLOCKED = 'BLOCKED',
}

/**
 * @enum EigenstatePhase
 * The classified phase of the system based on the tensor coordinates.
 */
export enum EigenstatePhase {
    E1_WATCH = 'E1_WATCH', // Nominal monitoring state
    E3_Q_ACTIVE = 'E3_Q_ACTIVE', // Sovereign grade active state (Q Activation)
    E1_WTCH = 'E1_WTCH', // Fallback watch state (typo preservation from historical context)
    EQURT = 'EQURT', // Critical quantum uncertainty or load shedding state
}

/**
 * @interface KernelContext
 * The raw telemetry context fed into the tensor computation.
 */
export interface KernelContext {
    requestRate: number; // φ2
    tokenBurnRate: number; // φ3
    queueDepth: number; // φ3 (secondary)
    billingPosture: BillingPosture; // φ4 (billing)
    riskPosture: BillingPosture; // φ3 (risk)
    alertFlags: number[]; // J7 (attention)
    pendingDecisions: number[]; // J0 (invariant)
    unresolvedLong: number[]; // Q10 (causality)
}

/**
 * @interface KernelState
 * The aggregate state object containing the context.
 */
export interface KernelState {
    context: KernelContext;
}

/**
 * @interface EigenstateTensor
 * The computed tensor representation of the system state.
 */
export interface EigenstateTensor {
    /**
     * @description Load vector [requestRate, tokenBurnRate, queueDepth]
     * Maps to φ2, φ3 dimensions
     */
    load: [number, number, number];

    /**
     * @description Posture vector [billing, credit, risk]
     * Normalized integer representations of Posture enums.
     * Maps to φ4, φ3 dimensions
     */
    posture: [number, number, number];

    /**
     * @description Attention vector (Alert Flags)
     * Maps to J7 dimension
     */
    attention: number[];

    /**
     * @description Invariant vector (Pending Decisions)
     * Maps to J0 dimension
     */
    invariant: number[];

    /**
     * @description Causality vector (Unresolved Long-tail events)
     * Maps to Q10 dimension
     */
    causality: number[];

    /**
     * @description The scalar Load Score computed from the Load vector.
     */
    loadScore: number;

    /**
     * @description The scalar Tension Score computed from alerts and pending items.
     */
    tensionScore: number;

    /**
     * @description The classified Eigenstate Phase.
     */
    phase: EigenstatePhase;
}

/**
 * Encodes a Posture enum into a normalized tensor integer.
 * @param posture The billing or risk posture
 * @returns 0 for OK, 1 for WARN, 2 for BLOCKED
 */
export function postureToCode(posture: BillingPosture): number {
    switch (posture) {
        case BillingPosture.OK: return 0;
        case BillingPosture.WARN: return 1;
        case BillingPosture.BLOCKED: return 2;
        default: return 0;
    }
}

/**
 * Computes the Eigenstate Tensor from the Kernel State.
 * This is the pure function implementation of the Phase Map.
 * @param state The current Kernel State
 * @returns The computed EigenstateTensor
 */
export function computeEigenstateTensor(state: KernelState): EigenstateTensor {
    const {
        requestRate,
        tokenBurnRate,
        queueDepth,
        billingPosture,
        riskPosture,
        alertFlags,
        pendingDecisions,
        unresolvedLong
    } = state.context;

    // Dimension Mapping
    const load: [number, number, number] = [requestRate, tokenBurnRate, queueDepth];
    const posture: [number, number, number] = [
        postureToCode(billingPosture),
        postureToCode(billingPosture), // Using billing for credit slot as placeholder
        postureToCode(riskPosture)
    ];
    const attention = [...alertFlags];
    const invariant = [...pendingDecisions];
    const causality = [...unresolvedLong];

    // Scalar Computations (simplified for the Contract)
    // In a real implementation, these would be weighted sums or non-linear projections
    const loadScore = requestRate + tokenBurnRate + queueDepth;
    const tensionScore = attention.length + invariant.length + causality.length;

    // Phase Classification Logic (The "Q Activation Boundary")
    let phase = EigenstatePhase.E1_WATCH;

    // Critical Unresolved State Check (risk == 2 or unresolved > 3)
    const unresolvedCount = causality.length;
    const riskCode = postureToCode(riskPosture);

    if (unresolvedCount > 3 || riskCode === 2) {
        // "Red" Zone
        phase = EigenstatePhase.EQURT;
    } else if (loadScore > 20 || tensionScore > 5) {
        // High Load / High Tension -> Active Q Region
        phase = EigenstatePhase.E3_Q_ACTIVE;
    } else {
        // Nominal
        phase = EigenstatePhase.E1_WATCH;
    }

    return {
        load,
        posture,
        attention,
        invariant,
        causality,
        loadScore,
        tensionScore,
        phase
    };
}
