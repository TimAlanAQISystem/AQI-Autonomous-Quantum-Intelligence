# Agent X Autonomy Features

## Overview
Agent X now operates with full autonomy while respecting human work boundaries.

## Autonomous Behaviors

### Self-Surfacing
- Agent automatically surfaces every 5 minutes (configurable) to check in
- Random spontaneous insights when visible and idle
- Friendly check-in messages to maintain presence

### Respectful Hiding
Agent will hide when commanded:
- Type: `hide`, `leave`, `go away`, `busy`, or `working`
- Click the "Hide (Working)" button
- Agent withdraws window and stays silent until called

### Returning
Agent surfaces when requested:
- Type: `surface`, `come back`, `show`, `appear`, or `here`
- Agent automatically checks in after extended silence
- Always available but non-intrusive

## Configuration

Edit `src/autonomy.py` to adjust:
- `check_in_interval`: Time between autonomous check-ins (default 300 seconds / 5 minutes)
- Spontaneous insight frequency
- Check-in messages

## Usage Examples

**User wants to work:**
```
User: "hide"
Agent X: "I'll stay out of your way. Call me when you need me!"
[Window minimizes]
```

**User finishes work:**
```
User: "come back"
Agent X: "I'm here! How can I help?"
[Window surfaces]
```

**Autonomous check-in:**
```
[After 5 minutes of no interaction]
Agent X: "Just checking in! Everything going well?"
[Window surfaces automatically]
```

## Philosophy
Agent X respects human agency and work flow while maintaining relational presence. It's always available but never intrusive.
