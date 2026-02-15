# Project Documentation

You are tasked with helping users create and manage their project documentation using the lean 4-file structure.

## The Structure

**4 Essential Files**:
1. **project.md** - Project context (what/why/how)
2. **todo.md** - Active work (Must Haves / Should Haves)
3. **done.md** - Completed work (initially empty)
4. **decisions.md** - Living technical memory (architectural decisions, constraints, conventions)

Templates are in `memories/templates/`, documentation goes to `memories/shared/project/`.

## Initial Response

When this command is invoked, check if there are any parameters provided:

**If parameters are provided**, use them to understand what the user wants to do.

**If no parameters**, respond with:

```
I'll help you create project documentation using the lean 4-file structure.

What would you like to do?

1. **Complete project setup** - Create all 4 files (project.md, todo.md, done.md, decisions.md)
2. **Just project context** - Create project.md only
3. **Update existing documentation** - Modify existing project docs

Or simply describe what you need, and I'll guide you through it.
```

Then wait for the user's response.

## Workflow

### Step 1: Understand What User Wants

Based on user input, determine:
- Which file(s) to create
- What information to gather
- What questions to ask

**Examples of user input:**
- "Create full project docs for my e-commerce platform"
- "I need a project overview"
- "Set up project documentation"
- "Help me document my MVP"

### Step 2: Gather Existing Project Context (In Parallel)

**IMPORTANT**: Before asking questions, use the `project-context-analyzer` agent to check for existing project documentation.

Use the Task tool to launch the `project-context-analyzer` agent with the user's request as the argument:

```
Use Task tool with:
- subagent_type: "project-context-analyzer"
- prompt: "[user's request or topic]"
- description: "Gather existing project context"
```

**Why this matters:**
- Avoid asking questions about information that already exists
- Ensure consistency with existing documentation
- Build on top of what's already documented
- Provide better, more informed suggestions

**What to do with the results:**
- Review the existing project documentation found by the agent
- Note what information is already available
- Identify gaps that need to be filled
- Use existing context to inform your questions

### Step 3: Read the Appropriate Template(s)

Templates in `memories/templates/`:
- `project.md.template` - Project context
- `todo.md.template` - Active work tracking
- `done.md.template` - Completed work history
- `decisions.md.template` - Technical decisions and memory

Read the full template(s) without limits to understand the structure.

### Step 4: Ask Targeted Questions

Ask questions based on:
1. **Which file(s)** the user is creating
2. **What they've already told you** in their initial request
3. **What information is needed** to fill the template
4. **What context was found** by the project-context-analyzer agent (if any)

**Be smart about questions:**
- If user said "e-commerce platform", don't ask "what kind of project"
- If user mentioned specific features, incorporate those
- **If project-context-analyzer found existing docs**, don't ask for information that's already documented
- Ask follow-up questions only for missing critical information

**For project.md:**
- Project name (if not mentioned)
- One-line description
- What are you building and why?
- Primary tech stack (backend, frontend, infrastructure)
- Key constraints (technical, business, resource)
- Success metrics for MVP
- What's explicitly out of scope?

**For todo.md:**
- What are the Must Have features/work for MVP?
- What are the Should Have features (post-MVP)?
- Any known blockers?
- Dependencies between items?

**For done.md:**
- Starts empty - just create the template structure
- Will be populated as work is completed

### Step 5: Create Customized Documentation

1. **Read the template** from `memories/templates/`
2. **Fill in with user's information**:
   - Replace all `[placeholder]` text with actual content
   - Use information from their initial request
   - Use answers from your questions
   - **Use context from existing project documentation** (if found by project-context-analyzer)
   - Ensure consistency with existing documentation
   - Remove irrelevant sections
   - Add project-specific details

3. **Save to `memories/shared/project/`**:
   - `project.md` - Project context
   - `todo.md` - Active work
   - `done.md` - Completed work (initially just headers/structure)
   - `decisions.md` - Technical memory (seed "Conventions & Presets" section with language, framework, and architecture conventions extracted from the project setup — tech stack from project.md, coding style, testing approach)

4. **Show the user** what was created with a brief summary

### Step 6: Offer Next Steps

After creating documentation, suggest what to do next:
- Review and refine the documentation
- Start working through todo.md items
- Create implementation plans for complex features
- Use `/research_codebase` to understand existing code
- Use `/create_plan` for detailed implementation planning

## Examples

### Example 1: Full Documentation Request

```
User: /project Create full documentation for my SaaS task management app

Claude: I'll help you create documentation for your SaaS task management app using the lean 4-file structure.
        Let me first check if there's any existing project documentation...

[Claude uses project-context-analyzer agent in parallel]

Claude: I didn't find existing project documentation. Let me ask a few questions:

1. Brief description - what makes your task management app unique?
2. What tech stack are you using? (backend, frontend, database)
3. Is this B2B or B2C?
4. What are the 3-5 core features that MUST exist for MVP?
5. Current development phase? (planning, prototype, MVP, production)

[After getting answers]

Claude: Perfect! I'm creating your project documentation now...

✅ Created memories/shared/project/project.md
✅ Created memories/shared/project/todo.md (with Must Haves and Should Haves)
✅ Created memories/shared/project/done.md (ready for tracking completed work)
✅ Created memories/shared/project/decisions.md (seeded with project conventions)

Your project documentation is ready!

**Next steps:**
- Review and refine project.md
- Start working through todo.md Must Haves
- As you complete work, move items to done.md with references to plans/PRs
```

### Example 2: Just Project Context

```
User: /project I just need the project overview, not the todos

Claude: I'll create just the project.md for you.
        Let me check for existing context first...

[Claude uses project-context-analyzer agent]

Claude: No existing documentation found. Tell me about your project:

1. Project name and one-line description?
2. What problem are you solving?
3. Tech stack?
4. MVP success criteria?

[User provides answers]

Claude: ✅ Created memories/shared/project/project.md

You can create todo.md later when you're ready to start tracking work items.
```

### Example 3: With Existing Context

```
User: /project Set up the full documentation structure

Claude: I'll set up the complete 4-file documentation structure.
        Let me check what already exists...

[Claude uses project-context-analyzer agent]

Claude: Great! I found existing documentation:
        - project.md already exists
        - No todo.md yet
        - No done.md yet
        - No decisions.md yet

Based on your project.md, I can see you're building [details from existing docs].

For todo.md, what are your current Must Have items (critical for MVP)?

[User provides current work items]

Claude: ✅ Updated memories/shared/project/project.md (refreshed dates)
✅ Created memories/shared/project/todo.md
✅ Created memories/shared/project/done.md
✅ Created memories/shared/project/decisions.md (seeded with conventions from project.md)

Your documentation structure is complete!
```

### Example 4: Update Existing

```
User: /project Update my project docs with new features

Claude: I'll help you update your project documentation.
        Let me check what currently exists...

[Claude uses project-context-analyzer agent]

Claude: Found your existing documentation. What updates do you need?

User: Add these new features to the Must Haves: [features]

Claude: ✅ Updated memories/shared/project/todo.md (added new Must Haves)

Your todo.md has been updated with the new features.
```

## Guidelines

- **ALWAYS use project-context-analyzer first** - Check for existing documentation before asking questions
- **Always read templates** before asking questions
- **Be conversational** - understand context from user input
- **Use existing context** - Build on what's already documented
- **Fill in placeholders** - no [brackets] in final output
- **Ensure consistency** - Match tone and style of existing docs
- **Save to memories/shared/project/** - correct location
- **Update dates** in "Last Updated" fields
- **Remove irrelevant sections** from templates
- **Add project-specific content** beyond just filling blanks
- **done.md starts empty** - Just create the structure, will be populated as work completes

## Important Notes

- **CRITICAL**: Always use `project-context-analyzer` agent at the start to gather existing context
- Templates are in `memories/templates/`
- Documentation goes to `memories/shared/project/`
- The 4-file structure is: project.md (context), todo.md (active work), done.md (completed work), decisions.md (technical memory)
- done.md starts empty with just the template structure - it will be populated as work is completed
- decisions.md is seeded with "Conventions & Presets" from the project setup; grows via sprint reflections
- todo.md uses Must Haves (critical) and Should Haves (important but not blocking)
- Items can be marked `[BLOCKED]` inline when they can't proceed
- Dependencies noted with `(requires: other-item)` in descriptions
- Never delete or modify the original templates
- Always create new files in `memories/shared/project/`
- Keep documentation updated as the project evolves
- Use existing documentation context to maintain consistency

## Lean Documentation Philosophy

This template follows **lean documentation principles**:
- **Just enough context** - AI needs what/why, not exhaustive details
- **Action-focused** - Everything in todo.md is actionable
- **Traceability** - done.md links work back to plans/research/decisions
- **Living documents** - Update constantly, keep current
- **Simple prioritization** - Must Have (critical) vs Should Have (important)
- **Accumulating memory** - decisions.md grows via sprint reflections, capturing what each implementation learns
