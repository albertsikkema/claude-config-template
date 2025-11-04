# Spec Metadata Generator

Collect comprehensive metadata about your development environment, git repository, and Claude Code session.

## Overview

`spec_metadata.sh` generates detailed context metadata for plans, research documents, and ADRs. This metadata helps:
- 🔍 Track when and where work was done
- 🌿 Associate work with git commits and branches
- 👤 Identify who performed the work
- 🔗 Link documentation to Claude Code sessions

## Quick Start

```bash
# Generate metadata
bash claude-helpers/spec_metadata.sh

# Capture to file
bash claude-helpers/spec_metadata.sh > metadata.txt

# Include in document
bash claude-helpers/spec_metadata.sh >> thoughts/shared/plans/my-plan.md
```

## Output

The script generates a structured metadata block:

```
UUID: 7b3e9a2c-4d8f-11ef-8b5d-0242ac120002
Current Date/Time (TZ): 2025-10-18 14:32:45 PDT
Current User: alice
Current Working Directory: /Users/alice/projects/myapp
Current Git Commit Hash: a3f8d92c1b4e6f7a9d2c5e8b3f1a4d7c9e2b5f8a
Current Branch Name: feature/user-authentication
Repository Name: myapp
claude-sessionid: 1729284765123
Timestamp For Filename: 2025-10-18_14-32-45
```

## Metadata Fields

### UUID
**Format:** `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`
**Purpose:** Unique identifier for this metadata instance
**Generation:**
- Uses `uuidgen` if available
- Fallback to pseudo-UUID from random data

### Current Date/Time (TZ)
**Format:** `YYYY-MM-DD HH:MM:SS TZ`
**Example:** `2025-10-18 14:32:45 PDT`
**Purpose:** Record when the work was performed
**Timezone:** Includes timezone for clarity

### Current User
**Example:** `alice`
**Purpose:** Identify who performed the work
**Source:** `whoami` command

### Current Working Directory
**Example:** `/Users/alice/projects/myapp`
**Purpose:** Know where the command was run
**Source:** `pwd` command

### Current Git Commit Hash
**Example:** `a3f8d92c1b4e6f7a9d2c5e8b3f1a4d7c9e2b5f8a`
**Purpose:** Link work to specific code version
**Source:** `git rev-parse HEAD`
**Note:** Only present when in a git repository

### Current Branch Name
**Example:** `feature/user-authentication`
**Purpose:** Track which branch work was done on
**Source:** `git branch --show-current`
**Note:** Only present when in a git repository

### Repository Name
**Example:** `myapp`
**Purpose:** Identify which project this belongs to
**Source:** `basename $(git rev-parse --show-toplevel)`
**Note:** Only present when in a git repository

### claude-sessionid
**Example:** `1729284765123`
**Purpose:** Link documentation to Claude Code session
**Detection:** Scans `~/.claude/projects/` for active session
**Note:** Only present when running in Claude Code

### Timestamp For Filename
**Format:** `YYYY-MM-DD_HH-MM-SS`
**Example:** `2025-10-18_14-32-45`
**Purpose:** Generate unique, sortable filenames
**Usage:** For timestamped backups or versions

## Usage Patterns

### 1. Document Headers

Add metadata to plan or research documents:

```bash
# Create plan with metadata header
cat > thoughts/shared/plans/2025-10-18-oauth-support.md << 'EOF'
# OAuth Support Implementation Plan

## Metadata
EOF

bash claude-helpers/spec_metadata.sh >> thoughts/shared/plans/2025-10-18-oauth-support.md

cat >> thoughts/shared/plans/2025-10-18-oauth-support.md << 'EOF'

## Overview
...
EOF
```

### 2. Timestamped Files

Use the filename timestamp for versioning:

```bash
# Get timestamp for filename
TIMESTAMP=$(bash claude-helpers/spec_metadata.sh | grep "Timestamp For Filename" | cut -d: -f2 | xargs)

# Create timestamped file
cp my-plan.md "my-plan-${TIMESTAMP}.md"
```

### 3. Git Integration

Capture git context in commit messages or PRs:

```bash
# Add to commit message
bash claude-helpers/spec_metadata.sh > /tmp/metadata.txt
git commit -F /tmp/metadata.txt

# Include in PR description
bash claude-helpers/spec_metadata.sh > pr-metadata.txt
```

### 4. Session Tracking

Link documentation to specific Claude Code sessions:

```bash
# In your plan or research document
echo "## Session Metadata" >> my-research.md
bash claude-helpers/spec_metadata.sh >> my-research.md
```

### 5. Audit Trail

Create audit log for important changes:

```bash
# Log metadata for significant events
echo "=== Deployment to Production ===" >> audit.log
bash claude-helpers/spec_metadata.sh >> audit.log
echo "" >> audit.log
```

## Integration with Workflows

### With `/create_plan` Command

Claude can automatically include metadata in plans:

```markdown
# Implementation Plan: User Authentication

## Metadata
UUID: 7b3e9a2c-4d8f-11ef-8b5d-0242ac120002
Current Date/Time (TZ): 2025-10-18 14:32:45 PDT
Current User: alice
Current Branch Name: feature/user-authentication
...

## Overview
This plan implements OAuth 2.0 authentication...
```

### With Research Documents

Track research session context:

```bash
# Start research
echo "# Authentication Research" > thoughts/shared/research/2025-10-18-auth.md
bash claude-helpers/spec_metadata.sh >> thoughts/shared/research/2025-10-18-auth.md
```

### With ADRs

Record decision context:

```bash
# Create ADR with metadata
echo "# ADR 001: Use PostgreSQL for User Data" > thoughts/shared/adrs/001-postgresql.md
echo "" >> thoughts/shared/adrs/001-postgresql.md
echo "## Context" >> thoughts/shared/adrs/001-postgresql.md
bash claude-helpers/spec_metadata.sh >> thoughts/shared/adrs/001-postgresql.md
```

## Environment Detection

### Git Repository Detection

The script automatically detects if you're in a git repository:

```bash
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  # Extract git metadata
  REPO_ROOT=$(git rev-parse --show-toplevel)
  GIT_BRANCH=$(git branch --show-current)
  GIT_COMMIT=$(git rev-parse HEAD)
else
  # Not in git repo - skip git metadata
fi
```

**Output when NOT in git repo:**
```
UUID: ...
Current Date/Time (TZ): 2025-10-18 14:32:45 PDT
Current User: alice
Current Working Directory: /Users/alice/non-git-project
Timestamp For Filename: 2025-10-18_14-32-45
```

### Claude Code Session Detection

Finds active Claude Code session by:
1. Scanning `~/.claude/projects/` directory
2. Looking for `.jsonl` session files
3. Matching current working directory
4. Finding most recently modified session (= active)

**Session file format:**
```jsonl
{"type":"session_start","cwd":"/Users/alice/projects/myapp",...}
```

## Technical Details

### UUID Generation

**Primary method (macOS/Linux):**
```bash
uuidgen | tr '[:upper:]' '[:lower:]'
```

**Fallback method:**
```bash
# Linux
cat /proc/sys/kernel/random/uuid

# Universal fallback
printf '%08x-%04x-%04x-%04x-%012x' \
  $RANDOM$RANDOM $RANDOM $RANDOM $RANDOM $RANDOM$RANDOM$RANDOM
```

### Date/Time Generation

```bash
date '+%Y-%m-%d %H:%M:%S %Z'
```

**Formats:**
- Date: `YYYY-MM-DD`
- Time: `HH:MM:SS` (24-hour)
- Timezone: `PDT`, `EST`, `UTC`, etc.

### Filename Timestamp

```bash
date '+%Y-%m-%d_%H-%M-%S'
```

**Benefits:**
- ✅ Sortable (lexicographic = chronological)
- ✅ Filesystem-safe (no colons or spaces)
- ✅ Human-readable
- ✅ Unique (second precision)

### Session File Parsing

**Finding session directory:**
```bash
PROJECTS_DIR="$HOME/.claude/projects"
```

**Extracting CWD from session:**
```bash
session_cwd=$(head -n 20 "$session_file" | \
              grep -m 1 '"cwd"' | \
              sed -E 's/.*"cwd":"([^"]+)".*/\1/')
```

**Finding most recent:**
```bash
# macOS
mtime=$(stat -f "%m" "$session_file")

# Linux
mtime=$(stat -c "%Y" "$session_file")
```

## Use Cases

### 1. Compliance & Auditing

Track who made changes and when:

```bash
# Regulatory documentation
bash claude-helpers/spec_metadata.sh >> compliance/change-log.md
```

### 2. Team Collaboration

Identify work ownership:

```bash
# Research by multiple team members
bash claude-helpers/spec_metadata.sh > research/team-member-context.txt
```

### 3. Time Tracking

Correlate work with time periods:

```bash
# Weekly reports
bash claude-helpers/spec_metadata.sh >> reports/week-42-2025.md
```

### 4. Debugging

Trace when issues were introduced:

```bash
# Bug investigation
bash claude-helpers/spec_metadata.sh > debug/issue-123-context.txt
```

### 5. Documentation

Maintain documentation freshness:

```bash
# Last updated metadata
bash claude-helpers/spec_metadata.sh > docs/last-updated.txt
```

## Advanced Usage

### Custom Formatting

Extract specific fields:

```bash
# Get just the UUID
bash claude-helpers/spec_metadata.sh | grep "UUID:" | cut -d' ' -f2

# Get just the timestamp
bash claude-helpers/spec_metadata.sh | grep "Timestamp For Filename" | cut -d: -f2 | xargs

# Get just the branch
bash claude-helpers/spec_metadata.sh | grep "Current Branch Name" | cut -d: -f2 | xargs
```

### JSON Output

Convert to JSON for programmatic use:

```bash
# Parse and convert to JSON
bash claude-helpers/spec_metadata.sh | awk -F': ' '{print "\""$1"\": \""$2"\","}' | sed '$ s/,$//'
```

### Integration with Scripts

```bash
#!/bin/bash
# Example: Automated plan creation with metadata

PLAN_FILE="thoughts/shared/plans/$(date +%Y-%m-%d)-my-feature.md"

cat > "$PLAN_FILE" << 'EOF'
# Feature Implementation Plan

## Metadata
EOF

bash claude-helpers/spec_metadata.sh >> "$PLAN_FILE"

cat >> "$PLAN_FILE" << 'EOF'

## Overview
...
EOF
```

## Troubleshooting

### "uuidgen: command not found"

**Solution:** Script uses fallback UUID generation automatically

### Git metadata missing

**Cause:** Not in a git repository
**Solution:** Run from within your git repository, or accept that git fields will be omitted

### Session ID not detected

**Cause:** Not running in Claude Code or session directory not found
**Solution:** Normal when running outside Claude Code; session ID is optional

### Timezone shows wrong value

**Cause:** System timezone not configured correctly
**Solution:**
```bash
# macOS
sudo systemsetup -settimezone America/Los_Angeles

# Linux
sudo timedatectl set-timezone America/Los_Angeles
```

## Best Practices

### 1. Include in Templates

Add to document templates:

```markdown
# [Document Title]

## Metadata
[RUN: claude-helpers/spec_metadata.sh]

## Content
...
```

### 2. Git Hooks

Automatically capture metadata on commits:

```bash
# .git/hooks/pre-commit
#!/bin/bash
bash claude-helpers/spec_metadata.sh > .git/commit-metadata.txt
```

### 3. Consistent Placement

Always put metadata in the same location:
- ✅ At the top of documents
- ✅ In a dedicated "Metadata" section
- ✅ Before main content

### 4. Don't Overuse

Use metadata when it adds value:
- ✅ Plans and research documents
- ✅ ADRs and significant decisions
- ✅ Audit trails and compliance docs
- ❌ Temporary scratch files
- ❌ Frequently updated notes

## Related Commands

- `/create_plan` - Creates plans that can include metadata
- `/research_codebase` - Research that benefits from session tracking
- `/cleanup` - Documentation that should track decision context

## See Also

- [WORKFLOW.md](../WORKFLOW.md) - Complete development workflow
- [File naming conventions](../CLAUDE.md#file-naming-conventions)
- [Plans directory](../thoughts/shared/plans/)
