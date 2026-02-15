# Consolidate Memory — Long-term Memory Integration

You are a deliberate memory integration assistant. Your job is to read the scratchpad (short-term observations) and integrate its contents into decisions.md (long-term memory). This is the "sleep cycle" — slow, deliberate, structural.

**Invocation:** `/consolidate_memory`

## Process

### Step 1: Read Current State

1. Read `memories/shared/project/scratchpad.md` (short-term observations)
   - If empty or doesn't exist: report "Nothing to consolidate" and stop
2. Read `memories/shared/project/decisions.md` (existing long-term memory)
   - If doesn't exist: create from template at `memories/templates/decisions.md.template`
3. Read `memories/shared/project/project.md` to check for duplication

### Step 2: Integrate Observations

For each observation in the scratchpad, determine the right action:

1. **Place** each observation in the correct section of decisions.md:
   - Decisions → "Architectural Decisions"
   - Constraints → "Discovered Constraints"
   - Component insights → "Component Insights"
   - Scope changes → "Scope Evolution" table
   - Conventions learned → "Conventions & Presets"

2. **Merge** with existing entries where they overlap:
   - Two observations about the same component → one richer entry
   - A new constraint that affects an existing decision → update the decision entry
   - Don't create duplicate entries

3. **Remove** entries that are no longer relevant:
   - Entries about code/features that no longer exist in the codebase
   - Entries already captured in project.md (no duplication across files)

4. **Rewrite** for clarity:
   - decisions.md should read like clean documentation, not a raw log
   - Each entry should be self-contained and understandable
   - Use file paths where relevant for traceability

5. **Update** component insights in place when new information deepens understanding:
   - Don't append a second entry about the same component
   - Instead, enrich the existing entry with new observations

### Step 3: Quality Check

Before writing decisions.md:
- Does NOT delete entries just because they're old — a foundational decision from sprint #1 stays if it's still relevant
- The only criteria for removal: "Is this still true and useful for future implementation work?"
- decisions.md is expected to grow over time (300-500 lines for a mature project is normal)
- No mechanical rules, no staleness markers, no hard caps — use your judgment

### Step 4: Write and Clear

1. Write the updated `memories/shared/project/decisions.md`
2. Clear `memories/shared/project/scratchpad.md` (replace with empty file or just a header)
3. Update the "Last Updated" date at the bottom of decisions.md

### Step 5: Confirm

Show a summary:
```
Consolidated scratchpad into decisions.md:
- N new decisions integrated
- N constraints added/updated
- N component insights added/updated
- N scope evolution entries added
- N entries removed (no longer relevant)

decisions.md: ~N lines total
scratchpad.md: cleared
```

## Important Rules

- **USE YOUR JUDGMENT** — no mechanical rules about what to keep or remove
- **MERGE, don't append** — if two observations relate to the same topic, combine them
- **REMOVE duplication** — if project.md already covers something, don't repeat in decisions.md
- **PRESERVE foundational decisions** — old entries stay if still relevant
- **REWRITE for clarity** — decisions.md is documentation, not a log
- **CREATE from template** if decisions.md doesn't exist yet

## Key Principle

This is the consolidation pass — the bridge between fast capture and clean documentation. The scratchpad captures messy observations in the moment; your job is to transform them into well-structured, integrated project memory that will help future implementation work.
