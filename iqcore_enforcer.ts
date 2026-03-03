// iqcore_enforcer.ts
//
// IQcore Enforcer — TypeScript
// Deterministic cognitive budget enforcement for the Agent X organism.
// Alan: 60 IQcores (operator), AgentX: 40 IQcores (governor).

export type Actor = "Alan" | "AgentX";

interface IQcoreLedger {
  Alan: number;
  AgentX: number;
  limits: {
    Alan: number;
    AgentX: number;
  };
  calls: {
    Alan: number;
    AgentX: number;
  };
}

export const IQCORES: IQcoreLedger = {
  Alan: 0,
  AgentX: 0,
  limits: {
    Alan: 60,
    AgentX: 40
  },
  calls: {
    Alan: 0,
    AgentX: 0
  }
};

export class IQcoreExceededError extends Error {
  actor: Actor;
  cost: number;

  constructor(actor: Actor, cost: number) {
    super(`${actor} exceeded IQcore budget by attempting cost ${cost} (current: ${IQCORES[actor]}/${IQCORES.limits[actor]})`);
    this.actor = actor;
    this.cost = cost;
  }
}

/**
 * Try to log burn to dashboard. Best-effort, never throws.
 */
function tryLogBurn(actor: Actor, cost: number, functionName: string): void {
  try {
    // Dynamic import to avoid hard dependency
    const { logBurn } = require("./iqcore_dashboard");
    logBurn(actor, cost, functionName);
  } catch {
    // Dashboard is optional
  }
}

/**
 * Decorator that enforces IQcore budget for a method.
 *
 * Usage:
 *   class AlanRuntime {
 *     @iqcoreCost("Alan", 3)
 *     chooseScript(segment: string) { ... }
 *   }
 */
export function iqcoreCost(actor: Actor, cost: number) {
  return function (
    _target: any,
    propertyKey: string,
    descriptor: PropertyDescriptor
  ) {
    const original = descriptor.value;

    descriptor.value = function (...args: any[]) {
      const current = IQCORES[actor];
      const limit = IQCORES.limits[actor];

      if (current + cost > limit) {
        throw new IQcoreExceededError(actor, cost);
      }

      IQCORES[actor] += cost;
      IQCORES.calls[actor] += 1;
      tryLogBurn(actor, cost, propertyKey);

      try {
        return original.apply(this, args);
      } finally {
        IQCORES[actor] -= cost;
      }
    };

    return descriptor;
  };
}

/**
 * Get a snapshot of the current ledger state.
 */
export function getSnapshot(): Record<Actor, { current: number; limit: number; remaining: number; total_calls: number }> {
  return {
    Alan: {
      current: IQCORES.Alan,
      limit: IQCORES.limits.Alan,
      remaining: IQCORES.limits.Alan - IQCORES.Alan,
      total_calls: IQCORES.calls.Alan
    },
    AgentX: {
      current: IQCORES.AgentX,
      limit: IQCORES.limits.AgentX,
      remaining: IQCORES.limits.AgentX - IQCORES.AgentX,
      total_calls: IQCORES.calls.AgentX
    }
  };
}

/**
 * Reset an actor's IQcore counter (or all if no actor specified).
 */
export function resetActor(actor?: Actor): void {
  if (actor) {
    IQCORES[actor] = 0;
    IQCORES.calls[actor] = 0;
  } else {
    IQCORES.Alan = 0;
    IQCORES.AgentX = 0;
    IQCORES.calls.Alan = 0;
    IQCORES.calls.AgentX = 0;
  }
}
