# Claude Flow Board Frontend Changes - 2026-01-06

## Overview

The claude-flow-board frontend (AIAD Board - "Albert's Workflow") has been updated from commit `575cefc` to `b7bc47f`. These changes add 4 major new features that require corresponding backend API implementations.

**Design Context:** The board is a modern, minimal Kanban application inspired by Linear and Notion, with clean sans-serif typography, subtle card shadows, and distinct color accents for each workflow stage.

## Commits Included

| Commit | Description |
|--------|-------------|
| `b7bc47f` | Add settings UI for git flow |
| `ad0d8b7` | Changes |
| `d594bf9` | Add security check UI and API |
| `2e36a76` | Changes |
| `1353915` | Add tech docs and index features |
| `93289ad` | Changes |

## Files Changed

- `src/api/tasks.ts` - 84 lines added (new API functions)
- `src/components/Board.tsx` - 121 lines changed (UI integration)
- `src/components/SecurityCheckPanel.tsx` - 443 lines (new file)
- `src/components/SettingsDialog.tsx` - 285 lines (new file)
- `src/components/TaskModal.tsx` - 6 lines changed
- `src/components/TechnicalDocsDialog.tsx` - 95 lines (new file)
- `src/hooks/useSettings.ts` - 65 lines (new file)
- `src/types/index.ts` - 2 lines changed

---

## 1. Technical Docs Fetching Feature

### Purpose
Fetch technical documentation for packages/libraries from **Context7**. This is a "fire-and-forget" operation - progress tracking is not required.

### Frontend Components
- `TechnicalDocsDialog.tsx` - Dialog for entering comma-separated package names

### API Endpoint Required

```typescript
POST /api/docs/fetch
```

**Request Body:**
```json
{
  "packages": ["react", "typescript", "@tanstack/react-query"]
}
```

**Response:**
```json
{
  "status": "string",
  "message": "string"
}
```

### Frontend API Function

```typescript
export async function fetchTechnicalDocs(packages: string[]): Promise<{ status: string; message: string }> {
  const response = await fetch(`${API_BASE}/api/docs/fetch`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ packages }),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to fetch technical docs');
  }
  return response.json();
}
```

### Implementation Notes
- The dialog allows comma-separated package names (e.g., "react, typescript, @tanstack/react-query")
- **Must integrate with Context7** to fetch documentation
- Should trigger the `/fetch_technical_docs` slash command or equivalent
- Fire-and-forget: returns immediately with status, no progress tracking needed
- Documentation saved to `thoughts/technical_docs/`

---

## 2. Codebase Indexing Feature

### Purpose
Index the codebase to generate overview files. This is a "fire-and-forget" operation that runs in the background.

### API Endpoint Required

```typescript
POST /api/codebase/index
```

**Request Body:** None

**Response:**
```json
{
  "status": "string",
  "message": "string"
}
```

### Frontend API Function

```typescript
export async function indexCodebase(): Promise<{ status: string; message: string }> {
  const response = await fetch(`${API_BASE}/api/codebase/index`, {
    method: 'POST',
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to index codebase');
  }
  return response.json();
}
```

### Implementation Notes
- Button in header shows loading state while request is being made
- **Fire-and-forget**: returns immediately, indexing runs in background
- Should trigger the `/index_codebase` slash command
- Generates codebase overview files in `thoughts/codebase/`

---

## 3. Security Check Feature

### Purpose
Run security analysis on the codebase, similar to how task execution works. The user should be able to:
- See live output as the check runs
- View the generated report file
- List and open previous security reviews

### Design Note
This feature reuses concepts from the task details panel - a script is started and the user can monitor output in real-time.

### Frontend Components
- `SecurityCheckPanel.tsx` - Full-featured slide-in panel with:
  - Sidebar listing previous security checks with status and timestamp
  - "Run New Check" button to start new security check
  - Live output streaming with auto-scroll (polls every 2 seconds)
  - Report tab to view generated markdown report
  - Full-screen modal for reading complete report

### Data Types

```typescript
export interface SecurityCheck {
  id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  started_at: string;      // ISO timestamp
  completed_at?: string;   // ISO timestamp
  output?: string;
  error?: string;
  report_path?: string;
}
```

### API Endpoints Required

#### 3.1 Start Security Check
```typescript
POST /api/security/check
```

**Response:** `SecurityCheck` object

#### 3.2 Get Security Check Status
```typescript
GET /api/security/check/{id}
```

**Response:** `SecurityCheck` object

#### 3.3 Get Security Check Output (for streaming)
```typescript
GET /api/security/check/{id}/output
```

**Response:**
```json
{
  "output": "string | null",
  "error": "string | null"
}
```

#### 3.4 Get Security Check Report
```typescript
GET /api/security/check/{id}/report
```

**Response:**
```json
{
  "content": "string",  // Markdown content of the report
  "path": "string"      // File path where report is saved
}
```

**Error:** 404 if no report available

#### 3.5 List All Security Checks
```typescript
GET /api/security/checks
```

**Response:** `SecurityCheck[]` (sorted by most recent first)

### Frontend API Functions

```typescript
export async function startSecurityCheck(): Promise<SecurityCheck> {
  const response = await fetch(`${API_BASE}/api/security/check`, {
    method: 'POST',
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to start security check');
  }
  return response.json();
}

export async function getSecurityCheck(id: string): Promise<SecurityCheck> {
  const response = await fetch(`${API_BASE}/api/security/check/${id}`);
  if (!response.ok) {
    throw new Error('Failed to get security check');
  }
  return response.json();
}

export async function getSecurityCheckOutput(id: string): Promise<{ output: string | null; error: string | null }> {
  const response = await fetch(`${API_BASE}/api/security/check/${id}/output`);
  if (!response.ok) {
    throw new Error('Failed to get security check output');
  }
  return response.json();
}

export async function getSecurityCheckReport(id: string): Promise<{ content: string; path: string }> {
  const response = await fetch(`${API_BASE}/api/security/check/${id}/report`);
  if (!response.ok) {
    if (response.status === 404) {
      throw new Error('No report available');
    }
    throw new Error('Failed to get security check report');
  }
  return response.json();
}

export async function listSecurityChecks(): Promise<SecurityCheck[]> {
  const response = await fetch(`${API_BASE}/api/security/checks`);
  if (!response.ok) {
    throw new Error('Failed to list security checks');
  }
  return response.json();
}
```

### Implementation Notes
- **Works similar to task execution** - script starts, output visible, file created as result
- Security check should run the `/security` slash command
- Output should be captured incrementally for live streaming
- Report is typically saved to `thoughts/shared/reviews/security-analysis-YYYY-MM-DD.md`
- Frontend strips YAML frontmatter from reports before displaying
- Frontend polls every 2 seconds while check is running
- Should persist security checks so users can view history

---

## 4. Settings Feature

### Purpose
Configure git workflow method and other preferences. **The git workflow setting affects backend behavior significantly.**

### Frontend Components
- `SettingsDialog.tsx` - Modal with 3 tabs: Workflow, Defaults, Appearance
- `useSettings.ts` - React hook for settings management with localStorage persistence

### Settings Interface

```typescript
export type GitWorkflow = 'branch-pr' | 'worktree-merge';
export type ThemeMode = 'light' | 'dark' | 'system';

export interface AppSettings {
  gitWorkflow: GitWorkflow;         // Git integration method
  theme: ThemeMode;                 // Color scheme
  defaultModel: 'sonnet' | 'opus' | 'haiku';
  defaultComplexity: 'simple' | 'complete';
  autoRefreshInterval: number;      // In seconds (2, 5, 10, or 30)
  showCompletedTasks: boolean;
  confirmBeforeDelete: boolean;
}
```

### Default Values

```typescript
const DEFAULT_SETTINGS: AppSettings = {
  gitWorkflow: 'branch-pr',
  theme: 'system',
  defaultModel: 'sonnet',
  defaultComplexity: 'complete',
  autoRefreshInterval: 5,
  showCompletedTasks: true,
  confirmBeforeDelete: true,
};
```

### Git Workflow Modes - Backend Impact

#### Mode 1: `branch-pr` (Branch + Pull Request)
- **Column Label:** "Merge" stage displays as "Pull Request"
- **Backend Behavior:**
  - Create new branch for each feature
  - Generate PR description when task reaches PR stage
  - Create actual PR in GitHub/GitLab
  - Handle PR merge flow

#### Mode 2: `worktree-merge` (Worktree + Merge)
- **Column Label:** "Merge" stage displays as "Merge"
- **Backend Behavior:**
  - Use git worktrees for feature development
  - Direct merge to main branch
  - No PR creation needed

### Storage
- Currently stored in `localStorage` with key `aiad-settings`
- **Future consideration:** Backend sync if settings need to persist across devices or affect backend behavior

### Backend API Considerations

The `gitWorkflow` setting needs to be passed to the backend when tasks reach the merge/PR stage:

```typescript
// When task moves to 'merge' stage, backend needs to know workflow mode
// Option 1: Include in request header
// Option 2: Store settings in backend
// Option 3: Include in task update payload
```

---

## 5. Minor Changes

### JobStatus Type Extension
The `JobStatus` type now includes `'cancelled'` status:

```typescript
// Before
export type JobStatus = 'pending' | 'running' | 'completed' | 'failed';

// After
export type JobStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
```

This requires updating the backend `JobStatus` enum to include the `cancelled` value.

---

## Backend Implementation Checklist

### Priority 1 - Core Features

- [ ] **Security Check System**
  - [ ] Create `SecurityCheck` model (id, status, started_at, completed_at, output, error, report_path)
  - [ ] Implement `POST /api/security/check` - Start new security check
  - [ ] Implement `GET /api/security/check/{id}` - Get check status
  - [ ] Implement `GET /api/security/check/{id}/output` - Get live output
  - [ ] Implement `GET /api/security/check/{id}/report` - Get final report
  - [ ] Implement `GET /api/security/checks` - List all checks
  - [ ] Add background task execution for running `/security` command
  - [ ] Capture stdout/stderr for live streaming
  - [ ] Persist security check history (database or file-based)

### Priority 2 - Documentation Features

- [ ] **Technical Docs Fetch**
  - [ ] Implement `POST /api/docs/fetch` endpoint
  - [ ] Integrate with Context7 for documentation fetching
  - [ ] Trigger `/fetch_technical_docs` command in background
  - [ ] Fire-and-forget: return immediate status response

- [ ] **Codebase Indexing**
  - [ ] Implement `POST /api/codebase/index` endpoint
  - [ ] Trigger `/index_codebase` command in background
  - [ ] Fire-and-forget: return immediate status response

### Priority 3 - Git Workflow Integration

- [ ] **Branch + PR Workflow**
  - [ ] Implement branch creation for new tasks
  - [ ] Generate PR descriptions when task reaches merge stage
  - [ ] Create actual PRs via GitHub/GitLab API
  - [ ] Handle merge completion

- [ ] **Worktree + Merge Workflow**
  - [ ] Implement git worktree creation for tasks
  - [ ] Handle direct merge to main branch
  - [ ] Clean up worktrees after completion

### Priority 4 - Type Updates

- [ ] Add `cancelled` to `JobStatus` enum in backend models

---

## Architecture Recommendations

### Security Check Implementation

```
┌─────────────────────────────────────────────────────────────┐
│ SecurityCheck Model                                         │
├─────────────────────────────────────────────────────────────┤
│ id: UUID (primary key)                                      │
│ status: enum('pending', 'running', 'completed', 'failed')  │
│ started_at: datetime                                        │
│ completed_at: datetime (nullable)                           │
│ output: text (nullable) - accumulated stdout                │
│ error: text (nullable) - accumulated stderr                 │
│ report_path: string (nullable) - path to generated report   │
└─────────────────────────────────────────────────────────────┘
```

### Background Task Pattern

1. Start security check → Create record with `pending` status → Return ID
2. Background task picks up → Update to `running` status
3. Execute `/security` command → Stream output to `output` field periodically
4. On completion → Update to `completed`, set `report_path`
5. On failure → Update to `failed`, set `error`

### Output Streaming

- Buffer output in database or Redis
- Frontend polls every 2 seconds
- Return incremental output on each poll
- Auto-scroll in UI for live monitoring

### Git Workflow Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Task reaches 'merge' stage                                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐        ┌─────────────────┐           │
│  │  branch-pr      │        │  worktree-merge │           │
│  │  workflow       │        │  workflow       │           │
│  └────────┬────────┘        └────────┬────────┘           │
│           │                          │                     │
│           ▼                          ▼                     │
│  1. Generate PR description   1. Merge worktree           │
│  2. Create GitHub PR          2. Push to main             │
│  3. Wait for merge            3. Cleanup worktree         │
│  4. Move to 'done'            4. Move to 'done'           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Original Lovable Conversation Context

For reference, the frontend was built through iterative conversations with the following key requirements:

1. **7 workflow columns** mapping to Claude Code stages:
   - Backlog → Research → Planning → Implementation → Testing → Cleanup → Merge/PR → Done

2. **Task properties:**
   - Model selection (sonnet, opus, haiku)
   - Complexity (simple vs complete workflow)
   - Priority levels
   - Ticket IDs and tags

3. **Task panel** opens on right half of screen showing:
   - Current stage indicator
   - Workflow timeline with completed/current/future stages
   - Full editing form
   - Restart button for failed tasks

4. **Design principles:**
   - Linear/Notion-inspired minimal design
   - Subtle shadows that lift on hover
   - Smooth @dnd-kit drag-and-drop animations
   - Auto-centering when task details open
