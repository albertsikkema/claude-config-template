# Project Documentation

You are tasked with helping users create and manage their project documentation using the templates in `thoughts/templates/`.

These are templates that will be customized based on user input and saved to `thoughts/shared/project/`.

## Initial Response

When this command is invoked, check if there are any parameters provided:

**If parameters are provided**, use them to understand what the user wants to do.

**If no parameters**, respond with:

```
I'll help you create project documentation based on the templates.

What would you like to create?

1. **Complete project documentation** - Create all documentation files at once
2. **Specific document** - Create just one type (project overview, features, etc.)
3. **Update existing documentation** - Modify existing project docs

Or simply describe what you need, and I'll guide you through it.
```

Then wait for the user's response.

## Workflow

### Step 1: Understand What User Wants

Based on user input, determine:
- Which template(s) to use
- What information to gather
- What questions to ask

**Examples of user input:**
- "Create full project docs for my e-commerce platform"
- "I need a project overview"
- "Document my must-have features"
- "Help me plan my MVP requirements"
- "Create an epic for authentication"

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

- Templates are in `thoughts/templates/`
- Read the full template(s) without limits
- Understand the structure before asking questions

### Step 4: Ask Targeted Questions

Ask questions based on:
1. **Which template** the user is working with
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
- Brief description (if not clear)
- Primary tech stack
- Current phase (prototype, MVP, production, etc.)
- Team composition
- Target audience

**For musthaves.md:**
- Core features for MVP
- Target users
- Critical requirements
- Non-functional requirements (performance, security, etc.)

**For shouldhaves.md:**
- Post-MVP features
- Future enhancements
- Long-term vision

**For todo.md:**
- Current high-priority tasks
- Known technical debt
- Infrastructure needs
- Pending items

**For epics.md:**
- Major feature areas
- Timeline and priorities
- Dependencies between features
- Success metrics

### Step 5: Create Customized Documentation

1. **Read the template** from `thoughts/templates/`
2. **Fill in with user's information**:
   - Replace all `[placeholder]` text with actual content
   - Use information from their initial request
   - Use answers from your questions
   - **Use context from existing project documentation** (if found by project-context-analyzer)
   - Ensure consistency with existing documentation
   - Remove irrelevant sections
   - Add project-specific details

3. **Save to appropriate location**:

   **For epics**, save to `thoughts/shared/project/epics/`:
   - `epic-[name].md` (e.g., `epic-authentication.md`, `epic-payment-processing.md`)

   **For other documentation**, save to `thoughts/shared/project/`:
   - Use clear filenames like:
     - `project-overview.md` or `project.md`
     - `mvp-requirements.md` or `musthaves.md`
     - `post-mvp-features.md` or `shouldhaves.md`
     - `technical-todos.md` or `todo.md`

4. **Show the user** what was created with a brief summary

### Step 6: Offer Next Steps

After creating documentation, suggest what to do next:
- Create additional documentation types
- Update existing docs
- Use the docs in planning workflows

## Examples

### Example 1: Full Documentation Request

```
User: /project Create full documentation for my SaaS task management app

Claude: I'll help you create documentation for your SaaS task management app.
        Let me first check if there's any existing project documentation...

[Claude uses project-context-analyzer agent in parallel]

Claude: I found some existing project context. Based on what's already documented
        and what's missing, let me ask a few questions:

1. What tech stack are you using?
2. Is this B2B or B2C?
3. Team size?
4. Current development phase?

[After getting answers]

Claude: Perfect\! I'm creating your documentation now...

✅ Created thoughts/shared/project/project.md
✅ Created thoughts/shared/project/musthaves.md
✅ Created thoughts/shared/project/shouldhaves.md
✅ Created thoughts/shared/project/todo.md
✅ Created thoughts/shared/project/epics.md

Your complete project documentation is ready\!
```

### Example 2: Specific Document

```
User: /project I need to document my MVP features

Claude: I'll help you create your MVP requirements document.
        Let me check for existing project documentation first...

[Claude uses project-context-analyzer agent]

Claude: Based on your existing project overview, I can see you're building [details].
        Now tell me about your core features...

[User describes features]

Claude: ✅ Created thoughts/shared/project/mvp-requirements.md
```

### Example 3: With User Input Parameter

```
User: /project Create an epic for user authentication with OAuth support

Claude: I'll create an authentication epic for you.
        Let me gather context from your existing project docs...

[Claude uses project-context-analyzer agent]

Claude: I see from your project docs that you're using [tech stack] and targeting [audience].
        A few questions about the authentication epic:

1. Which OAuth providers? (Google, GitHub, etc.)
2. Timeline for this epic?
3. Any dependencies on other features?

[After getting answers]

Claude: ✅ Created thoughts/shared/project/epics/epic-authentication.md
```

## Guidelines

- **ALWAYS use project-context-analyzer first** - Check for existing documentation before asking questions
- **Always read templates** before asking questions
- **Be conversational** - understand context from user input
- **Use existing context** - Build on what's already documented
- **Fill in placeholders** - no [brackets] in final output
- **Ensure consistency** - Match tone and style of existing docs
- **Save to thoughts/shared/project/** - correct location
- **Use descriptive filenames** - help users find docs easily
- **Update dates** in "Last Updated" fields
- **Remove irrelevant sections** from templates
- **Add project-specific content** beyond just filling blanks

## Important Notes

- **CRITICAL**: Always use `project-context-analyzer` agent at the start to gather existing context
- Templates are in `thoughts/templates/` (without .template extension after install)
- **Epics** go to `thoughts/shared/project/epics/`
- **Other docs** go to `thoughts/shared/project/`
- The project-context-analyzer will search `thoughts/shared/project/` for existing documentation
- Never delete or modify the original templates
- Always create new files in the appropriate project directory
- Keep documentation updated as the project evolves
- Use existing documentation context to maintain consistency across all project docs
