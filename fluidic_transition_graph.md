# AQI Fluidic World Transition Graph (Canonical V1)

## Allowed Transitions

- HOME → FOCUS, TEACH, CALM, LAB, BRIDGE
- FOCUS → REVIEW, BRIDGE, CALM, HOME
- TEACH → FOCUS, REVIEW, BRIDGE, HOME
- REVIEW → HOME, FOCUS, BRIDGE
- BRIDGE → HOME, FOCUS, TEACH, REVIEW, CALM, LAB
- CALM → HOME, FOCUS, BRIDGE
- LAB → FOCUS, REVIEW, BRIDGE, HOME

## Transition Notes
- All worlds can transition to BRIDGE (universal corridor)
- BRIDGE can transition to any world except itself (no infinite corridor)
- CALM and LAB are always allowed to return to HOME
- Governance can veto or reroute any transition if constraints are violated

## Visual (Text)

HOME
  |\
  | \__
  |    \__
  |      FOCUS
  |      /
  |     /
  |    /
  |   /
  |  /
  | /
  BRIDGE
  | \
  |  \
  |   \
  |    \
  |     TEACH
  |     /
  |    /
  |   /
  |  /
  | /
  REVIEW
  | \
  |  \
  |   \
  |    \
  |     CALM
  |     /
  |    /
  |   /
  |  /
  | /
  LAB

---
This graph ensures all operational, emotional, and governance-driven transitions are fluid, safe, and reversible.