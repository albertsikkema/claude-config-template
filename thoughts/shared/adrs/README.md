# Architecture Decision Records (ADRs)

This directory contains Architecture Decision Records (ADRs) - documents that capture important architectural and technical decisions made during development.

## What are ADRs?

ADRs document significant decisions about:
- Architecture and design patterns
- Technology choices
- Implementation approaches
- Trade-offs and alternatives considered

## Format

Each ADR follows the template in `thoughts/templates/adr.md.template` and includes:
- **Context**: What problem led to this decision
- **Decision**: What was chosen
- **Rationale**: Why this approach
- **Consequences**: What becomes easier/harder
- **Alternatives**: What else was considered and why it was rejected

## Naming Convention

ADRs use sequential numbering:
```
001-decision-title.md
002-another-decision.md
003-third-decision.md
```

## Status

ADRs can have the following statuses:
- **Accepted**: This is the current decision
- **Superseded**: Replaced by a newer ADR
- **Deprecated**: No longer applicable

## Creating ADRs

ADRs are typically created during the `/rationalize` workflow after implementation, when the rationale and trade-offs are clearly understood.

You can also create them manually using the template at `thoughts/templates/adr.md.template`.

## Index

<!-- This section is automatically updated by the /rationalize command -->
<!-- List ADRs in reverse chronological order (newest first) -->

No ADRs yet. Use `/rationalize` after implementation to document decisions.
