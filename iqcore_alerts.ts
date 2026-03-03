// iqcore_alerts.ts
//
// IQcore Alerts — Burn-Rate Early Warning System (TypeScript)
// Monitors IQcore burn rates and produces alerts when actors approach exhaustion.
//
// Thresholds:
//   HIGH     — > 70% consumed
//   CRITICAL — > 90% consumed

import { readFileSync, writeFileSync, existsSync } from "fs";
import { getDashboard } from "./iqcore_dashboard";

const ALERT_LOG = "logs/iqcore_alert_log.json";

const THRESHOLD_HIGH = 70;
const THRESHOLD_CRITICAL = 90;

interface Alert {
  timestamp: string;
  actor: string;
  level: "HIGH" | "CRITICAL";
  burn_pct: number;
  current: number;
  limit: number;
  message: string;
}

function writeAlert(alert: Alert): void {
  let data: Alert[] = [];
  try {
    if (existsSync(ALERT_LOG)) {
      data = JSON.parse(readFileSync(ALERT_LOG, "utf8"));
    }
  } catch {
    data = [];
  }

  data.push(alert);

  // Cap to last 500 alerts
  if (data.length > 500) {
    data = data.slice(-500);
  }

  writeFileSync(ALERT_LOG, JSON.stringify(data, null, 2));
}

/**
 * Check all actors' burn rates against thresholds.
 * Returns a list of alerts generated (empty if all clear).
 */
export function checkBurnRates(): Alert[] {
  const dashboard = getDashboard();
  const actors = dashboard.actors;
  const alerts: Alert[] = [];

  for (const actor of Object.keys(actors)) {
    const state = actors[actor];
    if (state.limit <= 0) continue;

    const pct = (state.current / state.limit) * 100;

    if (pct >= THRESHOLD_CRITICAL) {
      const alert: Alert = {
        timestamp: new Date().toISOString(),
        actor,
        level: "CRITICAL",
        burn_pct: Math.round(pct * 10) / 10,
        current: state.current,
        limit: state.limit,
        message: `${actor} at ${pct.toFixed(1)}% IQcore burn — INTERVENTION REQUIRED`
      };
      writeAlert(alert);
      alerts.push(alert);
    } else if (pct >= THRESHOLD_HIGH) {
      const alert: Alert = {
        timestamp: new Date().toISOString(),
        actor,
        level: "HIGH",
        burn_pct: Math.round(pct * 10) / 10,
        current: state.current,
        limit: state.limit,
        message: `${actor} at ${pct.toFixed(1)}% IQcore burn — approaching limit`
      };
      writeAlert(alert);
      alerts.push(alert);
    }
  }

  return alerts;
}

/**
 * Get the most recent alerts from the log.
 */
export function getAlertHistory(limit: number = 50): Alert[] {
  if (!existsSync(ALERT_LOG)) return [];
  try {
    const data: Alert[] = JSON.parse(readFileSync(ALERT_LOG, "utf8"));
    return data.slice(-limit);
  } catch {
    return [];
  }
}

/**
 * Clear the alert log.
 */
export function clearAlerts(): void {
  writeFileSync(ALERT_LOG, "[]");
}
