# AQI Monitoring & Metrics Plan

## Overview

This document defines the metrics that matter for tracking AQI's system performance, community engagement, and exposure campaign effectiveness. All metrics are drawn from real data sources — no fabricated targets.

## System Performance Metrics

### Production Health (Real Metrics)

These are the metrics the system actually tracks in production:

| Metric | Source | Current |
|--------|--------|---------|
| Server uptime | `control_api_fixed.py` health endpoint | Monitored |
| Tunnel validity | Cloudflare trycloudflare.com | Checked per health poll |
| Tunnel reachability | HTTP probe to tunnel URL | Checked per health poll |
| Twilio credentials status | Twilio API validation | Checked at startup |
| OpenAI API key status | API validation | Checked at startup |
| Campaign active status | Governor state | Monitored |
| Callable leads count | Lead database query | Real-time |
| Calls today count | Campaign stats | Real-time |

### Voice Pipeline Performance

| Metric | Target | Measurement |
|--------|--------|-------------|
| ASR latency (Groq Whisper) | ~300ms | Logged per turn |
| ASR fallback latency (OpenAI) | ~800ms | Logged on fallback |
| LLM response time (GPT-4o-mini) | <2s streaming start | Logged per turn |
| TTS generation | <500ms first byte | Logged per turn |
| End-to-end turn latency | <3s total | Composite measurement |

### Test Results Tracking

| Component | Tests | Last Result |
|-----------|-------|-------------|
| AQI 0.1mm Chip | 68 | 68/68 PASS |
| Phase 4 Telemetry | 120 | 120/120 PASS |
| Phase 5 Intelligence | 75 | 75/75 PASS |
| Compile verification | 13 files | 13/13 CLEAN |
| **Total** | **263** | **263/263 PASS** |

### Call Quality Metrics (Phase 4 Telemetry)

Per-call data captured automatically:

- Turn count
- FSM state trajectory
- Health level trajectory
- Telephony state trajectory
- Close attempt count
- Escalation count
- Exit reason (typed)
- Outcome vector (5-way classification)

### Behavioral Metrics (Phase 5)

Per-call behavioral profile:

- 5-axis continuum position
- 6 behavioral signal classifications
- Tags applied (from 13-tag vocabulary)
- Positive/warning tag split

## Repository Metrics

### GitHub Analytics

Track from GitHub Insights:

| Metric | What It Shows |
|--------|---------------|
| Stars | General interest level |
| Forks | Active engagement / study |
| Clones | Download activity |
| Unique visitors | Reach |
| Referring sites | Where traffic comes from |
| Popular content | Which docs get read most |

### Documentation Coverage

| Document | Status | Lines |
|----------|--------|-------|
| `README.md` | Current (v2.0) | ~180 |
| `AQI_SCIENTIFIC_ARCHITECTURE.md` | Current | ~1,200 |
| `AQI_ORGANISM_SPEC.md` | Current | ~395 |
| `AQI_FULL_SYSTEMS_DOCTRINE.md` | Current (v2.0) | ~800+ |
| `AGENT_X_MASTER_SYSTEM_REFERENCE.md` | Current (v4.0) | ~400+ |
| `Alan_Complete_Schematic.md` | Current (v2.0) | ~400+ |
| `docs/technical-overview.md` | Current | ~200+ |
| `docs/ethical-framework.md` | Current | ~200+ |
| `arxiv_preprint_draft.md` | Current | ~200+ |
| `ALAN_VOICE_CONTRACT.md` | Current (v1.2) | ~378 |
| Constitution Articles (7) | Current | Various |

## Exposure Campaign Metrics

### Content Performance

When posts are made on platforms (Reddit, HN, LinkedIn, Twitter/X), track:

| Metric | Why It Matters |
|--------|---------------|
| Upvotes/likes | Initial reception |
| Comments | Engagement depth |
| Technical questions asked | Whether the architecture resonates |
| Shares/reposts | Organic amplification |
| GitHub traffic spike correlation | Direct conversion |
| Negative feedback themes | What needs clarification |

### Outreach Results

| Category | Track |
|----------|-------|
| Emails sent | Volume |
| Responses received | Response rate |
| Meetings scheduled | Conversion |
| Partnerships formed | Outcome |
| Academic citations | Long-term impact |

## Monitoring Cadence

### Daily
- Server health check (automated via `/health` endpoint)
- Campaign status check
- Call count and outcome summary

### Weekly
- GitHub traffic review
- Phase 4 telemetry analysis (aggregate call patterns)
- Phase 5 behavioral tag distribution
- Test suite re-run confirmation

### Monthly
- Repository star/fork growth
- Documentation accuracy audit
- Outreach campaign effectiveness review
- Discovery catalog update (if new discoveries)

## Alerting

### Automated Alerts (Production)

| Condition | Action |
|-----------|--------|
| Server health check fails | Restart via `control_api_fixed.py` |
| Tunnel becomes unreachable | Regenerate Cloudflare tunnel |
| Twilio credentials invalid | Check environment variables |
| Test count drops below 263 | Investigate regression |

### Manual Alerts (Campaign)

| Condition | Action |
|-----------|--------|
| Negative sentiment spike on a post | Address technical concerns factually |
| Misinformation about AQI shared | Correct with specific documentation links |
| Significant GitHub traffic spike | Ensure documentation is current |

## Principles

1. **Only track what's real.** No vanity metrics. No fabricated targets.
2. **System metrics come from the system.** Phase 4 telemetry, health endpoints, test results.
3. **Campaign metrics come from platforms.** GitHub Insights, social media analytics.
4. **Never inflate numbers.** Report exact test counts, exact discovery counts, exact organ counts.
5. **Use metrics to improve, not to market.** Behavioral tag distributions improve the system. Engagement metrics improve communication.

---

*© 2025-2026 Timmy Jay Jones / SCSDMC. All rights reserved.*
