// iqcore_dashboard.ts
//
// IQcore Dashboard — TypeScript
// Unified cognitive ledger for the Agent X organism.
// Reads/writes iqcore_dashboard_state.json.

import { readFileSync, writeFileSync, existsSync } from "fs";

const DASHBOARD_PATH = "iqcore_dashboard_state.json";

interface BurnEntry {
  timestamp: string;
  function: string;
  cost: number;
}

interface ActorState {
  limit: number;
  current: number;
  burn_log: BurnEntry[];
}

interface DashboardState {
  version: string;
  updated_at: string;
  actors: Record<string, ActorState>;
}

function defaultState(): DashboardState {
  return {
    version: "1.0.0",
    updated_at: "",
    actors: {
      Alan: { limit: 60, current: 0, burn_log: [] },
      AgentX: { limit: 40, current: 0, burn_log: [] },
      RegimeEngine: { limit: 0, current: 0, burn_log: [] }
    }
  };
}

function load(): DashboardState {
  if (!existsSync(DASHBOARD_PATH)) {
    return defaultState();
  }
  try {
    const raw = readFileSync(DASHBOARD_PATH, "utf8");
    return JSON.parse(raw);
  } catch {
    return defaultState();
  }
}

function save(state: DashboardState): void {
  state.updated_at = new Date().toISOString();
  writeFileSync(DASHBOARD_PATH, JSON.stringify(state, null, 2));
}

/**
 * Log a cognitive burn event for an actor.
 * Called by the IQcore enforcer decorator after each decorated function runs.
 */
export function logBurn(actor: string, cost: number, functionName: string): void {
  const state = load();

  if (!state.actors[actor]) {
    state.actors[actor] = { limit: 0, current: 0, burn_log: [] };
  }

  const entry: BurnEntry = {
    timestamp: new Date().toISOString(),
    function: functionName,
    cost
  };

  state.actors[actor].current += cost;
  state.actors[actor].burn_log.push(entry);

  // Cap burn log size
  if (state.actors[actor].burn_log.length > 200) {
    state.actors[actor].burn_log = state.actors[actor].burn_log.slice(-200);
  }

  save(state);
}

/**
 * Reset an actor's burn state to zero.
 */
export function resetActor(actor: string): void {
  const state = load();
  if (state.actors[actor]) {
    state.actors[actor].current = 0;
    state.actors[actor].burn_log = [];
    save(state);
  }
}

/**
 * Reset all actors' burn state to zero.
 */
export function resetAll(): void {
  const state = load();
  for (const actor of Object.keys(state.actors)) {
    state.actors[actor].current = 0;
    state.actors[actor].burn_log = [];
  }
  save(state);
}

/**
 * Get the full dashboard state.
 */
export function getDashboard(): DashboardState {
  return load();
}
