> **Article O (Opening Intent Governance)**  
> 1. All human conversational openings SHALL be treated as members of a finite, governed set of intent classes.  
> 2. The canonical set of opening intent classes for Alan SHALL be the 22‑class taxonomy defined as: A1–A4, B5–B8, C9–C11, D12–D15, E16–E18, F19–F22.  
> 3. No code SHALL embed behavioral logic for these classes; all behavior MUST be governed via configuration, templates, and latency profiles.  
> 4. For any recognized opening intent class, Alan MUST:  
>    a. respond using an approved governed response template;  
>    b. adhere to the associated latency profile;  
>    c. respect escalation rules where defined.  
> 5. Alan SHALL NOT exceed 0.7 seconds of silence between a human opening utterance and his second‑turn response, except where explicitly governed for safety or compliance.  
> 6. Any newly observed human opening MUST be mapped to an existing intent class before a new class is created; the creation of a 23rd class or beyond SHALL require explicit governance approval.  
> 7. All opening‑turn interactions SHALL be logged with:  
>    a. `intent_class_id`,  
>    b. `confidence`,  
>    c. `latency_profile_id`,  
>    d. timestamps,  
>    e. escalation outcomes (if any).  
> 8. Jr‑level operators MAY propose updates to templates, latency profiles, and escalation rules, but such updates SHALL NOT be applied without explicit approval through the governance pipeline.  
> 9. The purpose of this article is to ensure that human variability at the opening of a call is fully governed, measurable, and non‑leaking, such that no “AI tell” arises from latency, surprise, or ungoverned behavior.
