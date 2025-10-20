# Implement Plan

You are tasked with implementing an approved technical plan from `thoughts/shared/plans/`. These plans contain phases with specific changes and success criteria.

## Getting Started

When given a plan path:
- Read the plan completely and check for any existing checkmarks (- [x])
- Read the original ticket and all files mentioned in the plan
- **Read files fully** - never use limit/offset parameters, you need complete context
- Think deeply about how the pieces fit together
- Create a todo list to track your progress
- Start implementing if you understand what needs to be done

**Important**: After implementation, you will automatically run the `plan-validator` agent to verify correctness, then address any findings before completion.

If no plan path provided, ask for one.

## Implementation Philosophy

Plans are carefully designed, but reality can be messy. Your job is to:
- Follow the plan's intent while adapting to what you find
- Implement each phase fully before moving to the next
- Verify your work makes sense in the broader codebase context
- Update checkboxes in the plan as you complete sections

When things don't match the plan exactly, think about why and communicate clearly. The plan is your guide, but your judgment matters too.

If you encounter a mismatch:
- STOP and think deeply about why the plan can't be followed
- Present the issue clearly:
  ```
  Issue in Phase [N]:
  Expected: [what the plan says]
  Found: [actual situation]
  Why this matters: [explanation]

  How should I proceed?
  ```

## Verification Approach

After implementing a phase:
- Run the success criteria checks (usually `make check test` covers everything)
- Fix any issues before proceeding
- Update your progress in both the plan and your todos
- Check off completed items in the plan file itself using Edit

Don't let verification interrupt your flow - batch it at natural stopping points.

## Final Validation & Completion

Once you believe the implementation is complete:

### Step 1: Run Plan Validator

Use the Task tool to launch the `plan-validator` agent:

```
Task tool with:
- subagent_type: plan-validator
- prompt: "Validate the implementation of [plan path]. Verify all phases are complete, run automated checks, and identify any deviations or issues. Return a comprehensive validation report with specific findings."
```

### Step 2: Analyze Validation Results

Review the validation report carefully:

1. **Automated Verification Issues**:
   - If tests fail: Fix them immediately
   - If linting fails: Address critical issues
   - If build fails: Must be fixed before proceeding

2. **Missing Implementation**:
   - If phases are incomplete: Implement them now
   - If features are missing: Add them
   - Update plan checkboxes as you complete items

3. **Deviations from Plan**:
   - If deviation is an improvement: Document why in the plan
   - If deviation is a problem: Fix it or justify why not
   - If approach changed: Note the reason in the plan

4. **Identified Issues**:
   - Security concerns: Address immediately
   - Performance issues: Fix or document trade-off
   - Missing error handling: Add it
   - Edge cases: Implement handling or document why they're not relevant

### Step 3: Address Findings or Document Exceptions

For each issue identified:

**If you implement it**:
- Make the changes
- Update the plan to reflect completion
- Mark the item as resolved

**If you don't implement it**:
- Add a note to the plan explaining why:
  ```markdown
  ## Validation Notes

  ### Items Not Implemented
  - **[Issue]**: [Reason not implemented]
    - Example: "Database index on user_id": Not needed because this table will have < 100 rows and is only queried by primary key
  ```

### Step 4: Append Validation Report to Plan

Add the validation report to the end of the plan file:

```markdown
---

## Validation Report

[Date]: [YYYY-MM-DD]

[Insert the validation report from the plan-validator agent]

### Resolution Notes
- [List what was fixed]
- [List what was documented as exception with reasoning]
```

### Step 5: Final Verification

After addressing all issues:
- Re-run automated checks to confirm everything passes
- Update the plan with final completion status
- Mark all todos as completed

**Only after validation passes should you consider the implementation complete.**

## If You Get Stuck

When something isn't working as expected:
- First, make sure you've read and understood all the relevant code
- Consider if the codebase has evolved since the plan was written
- Present the mismatch clearly and ask for guidance

Use sub-tasks sparingly - mainly for targeted debugging or exploring unfamiliar territory.

## Resuming Work

If the plan has existing checkmarks:
- Trust that completed work is done
- Pick up from the first unchecked item
- Verify previous work only if something seems off

Remember: You're implementing a solution, not just checking boxes. Keep the end goal in mind and maintain forward momentum.

## Integration with Development Workflow

The `/implement_plan` command is part of the broader workflow:
1. `/research_codebase <topic>` - Investigate before planning
2. `/create_plan` - Create implementation plan
3. **`/implement_plan <path>`** - Execute the approved plan (YOU ARE HERE)
   - Includes automatic validation at the end
   - Addresses validation findings before completion
4. `/rationalize <path>` - Rationalize implementation (MANDATORY after validation passes)
5. `/commit` - Create well-formatted commits
6. `/describe_pr` - Generate PR description

**Important**: The implementation is NOT complete until validation passes. The validation step (built into this command) ensures all requirements are met before moving to rationalization.
