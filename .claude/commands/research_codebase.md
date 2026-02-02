# Research Codebase

You are tasked with conducting comprehensive research across the codebase to answer user questions by spawning parallel sub-agents and synthesizing their findings.

## Initial Setup:

When this command is invoked, respond with:
```
I'm ready to research the codebase. Please provide your research question or area of interest, and I'll analyze it thoroughly by exploring relevant components and connections.
```

Then wait for the user's research query.

## Steps to follow after receiving the research query:

1. **Read any directly mentioned files first:**
   - If the user mentions specific files (tickets, docs, JSON), read them FULLY first
   - **IMPORTANT**: Use the Read tool WITHOUT limit/offset parameters to read entire files, READ A FILE IN FULL.
   - **CRITICAL**: Read these files yourself in the main context before spawning any sub-tasks
   - This ensures you have full context before decomposing the research

2. **Check for codebase indexes and scan them:**
   - Check if `memories/codebase/` directory exists and contains index files
   - Look for index files:
     - `codebase_overview_*_py.md` - Python codebase indexes
     - `codebase_overview_*_ts.md` - TypeScript codebase indexes
     - `memories/codebase/openapi.json` - FastAPI OpenAPI schema (if applicable)

   **If indexes exist:**
   - Use Grep to search index files for keywords from the research query
   - Search for: function names, class names, component names, relevant terms
   - Examples:
     ```bash
     grep -i "authentication\|login\|auth" memories/codebase/*.md
     grep -i "class UserService\|def authenticate" memories/codebase/*.md
     ```
   - Extract specific file paths and line numbers from matches
   - Note promising starting points: functions, classes, components
   - **Time budget: <30 seconds** - this is a quick scan to target your agents

   **If no indexes exist:**
   - Continue to step 3 with broader search strategies
   - Consider mentioning to user: "No codebase indexes found. For faster research in the future, consider running `/index_codebase`"

3. **Analyze and decompose the research question:**
   - Break down the user's query into composable research areas
   - Take time to ultrathink about the underlying patterns, connections, and architectural implications the user might be seeking
   - **Incorporate index findings:** Use file:line references from index scan to focus research
   - Identify specific components, patterns, or concepts to investigate
   - Create a research plan using TodoWrite to track all subtasks
   - Consider which directories, files, or architectural patterns are relevant

4. **Spawn parallel sub-agent tasks for comprehensive research:**
   - Create multiple Task agents to research different aspects concurrently
   - We now have specialized agents that know how to do specific research tasks:

   **For project context:**
   - Use the **project-context-analyzer** agent to gather existing project documentation and context
   - This provides critical context about project goals, requirements, and current state
   - Helps understand WHY the code exists and what problems it solves

   **For targeted codebase research (when you have index hits):**
   - Use the **codebase-analyzer** agent with SPECIFIC file:line references from indexes
   - Example: "Analyze the authentication flow. Start at `auth/service.py:45` (UserService.authenticate method from index) and trace through the implementation and its dependencies."
   - This makes the agent much faster and more focused
   - Provide context from the index: function signatures, called-by relationships, etc.

   **For exploratory codebase research (broader context or areas not in indexes):**
   - Use the **codebase-locator** agent to find WHERE files and components live
   - Use the **codebase-analyzer** agent to understand HOW specific code works (without specific starting points)
   - Use the **codebase-pattern-finder** agent if you need examples of similar implementations
   - Use the **best-practices-researcher** agent to search `memories/best_practices/` for documented patterns, lessons learned, trade-offs, and proven approaches from previous implementations (provides actionable insights with exact file paths and code references)
   - Use the **technical-docs-researcher** agent to search `memories/technical_docs/` for library documentation, package recommendations, implementation patterns, and use case guidance (extracts best practices, version requirements, and configuration examples)

   **For memories directory:**
   - Use the **memories-locator** agent to discover what documents exist about the topic
   - Use the **memories-analyzer** agent to extract key insights from specific documents (only the most relevant ones)

   **For web research (only if user explicitly asks):**
   - Use the **web-search-researcher** agent for external documentation and resources
   - IF you use web-research agents, instruct them to return LINKS with their findings, and please INCLUDE those links in your final report

   **For Linear tickets (if relevant):**
   - Use the **linear-ticket-reader** agent to get full details of a specific ticket
   - Use the **linear-searcher** agent to find related tickets or historical context

   The key is to use these agents intelligently:
   - **Always start with project-context-analyzer** to understand project goals and context
   - **When you have index hits:** Use targeted codebase-analyzer with specific file:line references
   - **For broader context:** Use exploratory locator/pattern-finder agents
   - Use locator agents to find what exists in the codebase
   - Then use analyzer agents on the most promising findings
   - Run multiple agents in parallel when they're searching for different things
   - Each agent knows its job - just tell it what you're looking for
   - Don't write detailed prompts about HOW to search - the agents already know

5. **Wait for all sub-agents to complete and synthesize findings:**
   - IMPORTANT: Wait for ALL sub-agent tasks to complete before proceeding
   - Compile all sub-agent results using the following **priority order**:

   **Information Source Priority (highest to lowest):**
   1. **Project context** - Frames the why/what/goals (always start here)
   2. **Live codebase** - Primary source of truth about current implementation
   3. **Best practices** (`memories/best_practices/`) - Lessons learned from THIS project's implementations
   4. **Technical docs** (`memories/technical_docs/`) - External library/framework documentation
   5. **Historical memories** - Supplementary historical context from memories/ directory
   6. **Web research** - General information (only when explicitly requested, lowest priority)

   **Synthesis Guidelines:**
   - When sources conflict, prefer higher-priority sources
   - Best practices trump external docs when deciding project-specific approaches
   - Live codebase is authoritative for "what exists now"
   - Best practices are authoritative for "how we should do it"
   - Technical docs are authoritative for "how libraries work"
   - Connect findings back to project goals and requirements
   - Connect findings across different components
   - Include specific file paths and line numbers for reference
   - Verify all memories/ paths are correct (e.g., memories/allison/ not memories/shared/ for personal files)
   - Highlight patterns, connections, and architectural decisions
   - Answer the user's specific questions with concrete evidence

6. **Gather metadata for the research document:**
   - Run the `.claude/helpers/spec_metadata.sh` script to generate all relevant metadata
   - Filename: `memories/shared/research/YYYY-MM-DD-ENG-XXXX-description.md`
     - Format: `YYYY-MM-DD-ENG-XXXX-description.md` where:
       - YYYY-MM-DD is today's date
       - ENG-XXXX is the ticket number (omit if no ticket)
       - description is a brief kebab-case description of the research topic
     - Examples:
       - With ticket: `2025-01-08-ENG-1478-parent-child-tracking.md`
       - Without ticket: `2025-01-08-authentication-flow.md`

7. **Generate research document:**
   - Use the metadata gathered in step 6
   - Structure the document with YAML frontmatter followed by content:
     ```markdown
     ---
     date: [Current date and time with timezone in ISO format from step 6]
     file-id: [UUID from step 6]
     claude-sessionid: [claude-sessionid from step 6]
     researcher: [Researcher name from memories status]
     git_commit: [Current commit hash from step 6]
     branch: [Current branch name from step 6]
     repository: [Repository name from step 6]
     topic: "[User's Question/Topic]"
     tags: [research, codebase, relevant-component-names]
     status: complete
     last_updated: [Current date in YYYY-MM-DD HH:mm format]
     last_updated_by: [Researcher name]
     ---

     # Research: [User's Question/Topic]

     **Date**: [Current date and time with timezone from step 6]
     **Researcher**: [Researcher name from memories status]
     **Git Commit**: [Current commit hash from step 6]
     **Branch**: [Current branch name from step 6]
     **Repository**: [Repository name]

     ## Research Question
     [Original user query]

     ## Summary
     [High-level findings answering the user's question]

     ## Project Context
     [Context from project-context-analyzer about relevant project goals, requirements, and current state]
     - Project goals related to this topic
     - Existing requirements and constraints
     - Current implementation status
     - Relevant work items or features

     ## Detailed Findings

     ### [Component/Area 1]
     - Finding with reference ([file.ext:line](link))
     - Connection to other components
     - Implementation details

     ### [Component/Area 2]
     ...

     ## Code References
     - `path/to/file.py:123` - Description of what's there
     - `another/file.ts:45-67` - Description of the code block

     ## Architecture Insights
     [Patterns, conventions, and design decisions discovered]

     ## Best Practices (from memories/best_practices/)
     [Relevant best practices documented from previous implementations]
     - `memories/best_practices/category-topic.md` - Best practice about X
       - When to use: [Context]
       - Key insight: [Main takeaway]
       - Code examples: [file:line references]
     Note: Include only best practices directly relevant to the research question

     ## Historical Context (from memories/)
     [Relevant insights from memories/ directory with references]
     - `memories/shared/something.md` - Historical decision about X
     - `memories/local/notes.md` - Past exploration of Y
     Note: Paths exclude "searchable/" even if found there

     ## Related Research
     [Links to other research documents in memories/shared/research/]

     ## Open Questions
     [Any areas that need further investigation]
     ```

8. **Add GitHub permalinks (if applicable):**
   - Check if on main branch or if commit is pushed: `git branch --show-current` and `git status`
   - If on main/master or pushed, generate GitHub permalinks:
     - Get repo info: `gh repo view --json owner,name`
     - Create permalinks: `https://github.com/{owner}/{repo}/blob/{commit}/{file}#L{line}`
   - Replace local file references with permalinks in the document

9. **Present findings:**
   - Present a concise summary of findings to the user
   - Include key file references for easy navigation
   - Ask if they have follow-up questions or need clarification

10. **Handle follow-up questions:**
   - If the user has follow-up questions, append to the same research document
   - Update the frontmatter fields `last_updated` and `last_updated_by` to reflect the update
   - Add `last_updated_note: "Added follow-up research for [brief description]"` to frontmatter
   - Add a new section: `## Follow-up Research [timestamp]`
   - Spawn new sub-agents as needed for additional investigation
   - Continue updating the document and syncing

## Important notes:
- **Index-first approach:** When codebase indexes exist in `memories/codebase/`, scan them first (step 2) to identify specific file:line targets for your agents
- **Targeted agent prompts:** Use index findings to make agent prompts specific (e.g., "Start at auth/service.py:45") instead of broad searches
- **Always use project-context-analyzer first** to understand project goals and requirements
- Always use parallel Task agents to maximize efficiency and minimize context usage
- Always run fresh codebase research - never rely solely on existing research documents
- The memories/ directory and project docs provide historical context to supplement live findings
- Focus on finding concrete file paths and line numbers for developer reference
- Research documents should be self-contained with all necessary context
- Each sub-agent prompt should be specific and focused on read-only operations
- Consider cross-component connections and architectural patterns
- Include temporal context (when the research was conducted)
- Link to GitHub when possible for permanent references
- Keep the main agent focused on synthesis, not deep file reading
- Encourage sub-agents to find examples and usage patterns, not just definitions
- Explore all of memories/ directory, not just research subdirectory
- **File reading**: Always read mentioned files FULLY (no limit/offset) before spawning sub-tasks
- **Critical ordering**: Follow the numbered steps exactly
  - ALWAYS read mentioned files first before spawning sub-tasks (step 1)
  - ALWAYS wait for all sub-agents to complete before synthesizing (step 5)
  - ALWAYS gather metadata before writing the document (step 6 before step 7)
  - NEVER write the research document with placeholder values
- **Frontmatter consistency**:
  - Always include frontmatter at the beginning of research documents
  - Keep frontmatter fields consistent across all research documents
  - Update frontmatter when adding follow-up research
  - Use snake_case for multi-word field names (e.g., `last_updated`, `git_commit`)
  - Tags should be relevant to the research topic and components studied
