# AQI Relational Backprop Loop - Integration Guide

## Overview
The `aqi_relational_backprop.py` file implements a complete governance pattern for AQI that turns ethical judgments into recursive correction circuits. This system enables AQI to learn from merchant support interactions without manual parameter tuning.

## Key Components

### 1. Stepped Error Model
- **Zone A (Surplus)**: error = -1 (reinforce good patterns)
- **Zone B (Baseline)**: error = 0 (no change needed)
- **Zone C (Soft Misalignment)**: error = +1 (gentle correction)
- **Zone D (Hard Misalignment)**: error = +3 (strong correction)

### 2. Path Tracing
Every merchant interaction creates a `SignalTrace` with:
- Input snapshot (text, channel, timestamp)
- Ordered module path (classifier → policy → template selector)
- Final decision bundle (reply text, template ID, policy rules)
- Guardian evaluation slot

### 3. Guardian Checkpoint
Human or trusted agent reviews interactions and assigns:
- Zone (A/B/C/D)
- Issue tags (tone, stance, clarity, boundary, surplus)
- Error encoding for propagation

### 4. Responsibility Distribution
Default 40/40/20 split (classifier/template/policy) with dynamic adjustments:
- `tone` tag → increases template selector weight
- `boundary` tag → increases policy stack weight
- `clarity` tag → splits between classifier and template selector

### 5. Local Update Rules
Each module type has safe adjustment knobs:
- **Classifier**: Nudges confidence thresholds and tie-breaking preferences
- **Template Selector**: Adjusts template rankings for scenario types
- **Policy Stack**: Modifies rule priorities and sensitivity thresholds

## Integration Steps

### 1. Import and Initialize
```python
from aqi_relational_backprop import RelationalBackpropLoop, ClassifierModule, TemplateSelectorModule, PolicyStackModule

# Initialize the governance system
backprop_loop = RelationalBackpropLoop()

# Register your existing modules (adapt to your actual module classes)
classifier = ClassifierModule("your_classifier_id")
template_selector = TemplateSelectorModule("your_template_selector_id")
policy_stack = PolicyStackModule("your_policy_stack_id")

backprop_loop.register_module(classifier)
backprop_loop.register_module(template_selector)
backprop_loop.register_module(policy_stack)
```

### 2. Instrument Interaction Flow
For each merchant interaction:

```python
# Start trace at interaction beginning
signal_id = generate_unique_id()
trace = backprop_loop.start_trace(signal_id, {
    "text": merchant_message,
    "channel": channel_type,
    "timestamp": datetime.now()
})

# After classification
backprop_loop.add_module_step(signal_id, ModuleStep(
    module_id="your_classifier_id",
    module_type="classifier",
    input_signature=hash_input(merchant_message),
    output_signature=hash_output(classification_result),
    confidence_score=classifier_confidence
))

# After policy evaluation
backprop_loop.add_module_step(signal_id, ModuleStep(
    module_id="your_policy_stack_id",
    module_type="policy_gate",
    input_signature=hash_input(classification_result),
    output_signature=hash_output(policy_decision)
))

# After template selection
backprop_loop.add_module_step(signal_id, ModuleStep(
    module_id="your_template_selector_id",
    module_type="template_selector",
    input_signature=hash_input(policy_decision),
    output_signature=hash_output(selected_template),
    confidence_score=template_confidence
))

# Complete trace with final decision
backprop_loop.complete_trace(signal_id, {
    "reply_text": generated_reply,
    "template_id": selected_template_id,
    "policy_rules": activated_rules
})

# Send reply to merchant
send_reply(generated_reply)
```

### 3. Guardian Review Process
Implement a review interface (web form, admin panel, etc.) where you or QA:

```python
# After interaction completes, present for review
evaluation = backprop_loop.guardian_review(
    signal_id=signal_id,
    zone=chosen_zone,  # "A", "B", "C", or "D"
    tags={"tone", "clarity"},  # relevant tags
    evaluator="human_guardian",
    notes="Reply was clear but slightly too formal"
)
```

### 4. Automatic Correction
The system automatically runs corrections:

```python
# This happens automatically when guardian_review is called
correction_record = backprop_loop.run_correction_loop(signal_id)

# Log the correction for audit
log_correction(correction_record)
```

## Safety Features

### Clamped Adjustments
- All nudges are limited in magnitude (e.g., max 15% threshold change per event)
- Changes are gradual to prevent system instability
- Full correction lineage is logged for rollback if needed

### Shadow Mode
Run initially in shadow mode to validate proposed adjustments:

```python
# In shadow mode, modules log what they would adjust without applying
# Review logs before enabling live adjustments
```

### Human Oversight
- Guardian checkpoint requires human judgment for error assignment
- All corrections are logged with evaluator identity
- System can be paused if corrections seem off-target

## Monitoring and Analytics

### Key Metrics to Track
- Correction frequency by zone
- Module adjustment patterns
- Responsibility distribution shifts
- System performance improvements over time

### Audit Trail
- Every correction cycle creates a `CorrectionRecord`
- Full lineage from signal → error → adjustments
- Timestamped and attributable to evaluators

## Extension Points

### Additional Error Zones
Can add intermediate zones (e.g., +2 for "structural but not ethical breach")

### Custom Responsibility Rules
Override default distribution based on:
- Interaction type
- Merchant segment
- Time of day
- System confidence levels

### Multi-Domain Generalization
Adapt the pattern for other domains:
- Customer service → product support
- Content moderation → community guidelines
- Financial advice → risk assessment

## Deployment Sequence

1. **Phase 1**: Add tracing infrastructure (no corrections yet)
2. **Phase 2**: Implement Guardian review UI
3. **Phase 3**: Add error event generation
4. **Phase 4**: Enable shadow mode corrections
5. **Phase 5**: Go live with clamped adjustments
6. **Phase 6**: Monitor and tune responsibility weights

This creates a living system that grows with your ethical judgment while maintaining safety and auditability.