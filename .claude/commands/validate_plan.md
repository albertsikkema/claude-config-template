# Validate Plan

You are tasked with validating that an implementation plan was correctly executed by delegating to the specialized `plan-validator` agent.

## How to Execute

1. **Determine the plan path**:
   - If plan path provided by user, use it
   - If not provided, search `thoughts/shared/plans/` for recent files or ask user
   - Check git commit messages for plan references

2. **Invoke the plan-validator agent**:
   ```
   Use Task tool with:
   - subagent_type: plan-validator
   - prompt: "Validate the implementation of [plan path]. Verify all phases are complete, run all automated checks, and identify any deviations or issues. Return a comprehensive validation report with specific findings, file locations, and actionable recommendations."
   ```

3. **Present the agent's validation report to the user**:
   - Show the complete report from the agent
   - Do NOT summarize or filter the report
   - Do NOT add your own analysis on top of the agent's findings
   - The agent's report is authoritative and complete

## After Presenting the Report

Based on the agent's findings, guide the user on next steps:

**If validation identified issues**:
- Highlight any critical blockers (failing tests, build errors, security concerns)
- User should address critical issues before proceeding
- Minor issues can be fixed now or documented as acceptable trade-offs

**If validation passed**:
- User can proceed to `/rationalize` to update documentation
- Then `/commit` and `/describe_pr`

## Troubleshooting

**If plan path not found**:
- Search `thoughts/shared/plans/` for recent files
- Check git commit messages for plan references
- Ask user to provide the correct path

**If agent reports it cannot determine what changed**:
- May need more git history context
- Work might have been done outside of git
- User may need to manually provide context

**If validation seems incorrect**:
- Check if agent analyzed the right commits
- Verify plan file itself is up to date
- Ask user to re-run after verifying git state

## Relationship to Other Commands

**Note**: Validation is automatically run at the end of `/implement_plan`. You typically only need to run this command standalone if:
- You implemented code manually (without `/implement_plan`)
- You want to re-validate after making additional changes
- You're debugging validation issues

**Recommended workflow**:
1. `/research_codebase <topic>` - Investigate before planning
2. `/create_plan` - Create implementation plan
3. `/implement_plan <path>` - Execute the approved plan (includes automatic validation)
4. `/validate_plan <path>` - **[OPTIONAL]** Standalone validation if needed (YOU ARE HERE)
5. `/rationalize <path>` - Rationalize implementation and update documentation (MANDATORY)
6. `/commit` - Create well-formatted commits
7. `/describe_pr` - Generate PR description

The validation happens BEFORE rationalization and commits. It verifies that the implementation matches the plan and identifies any issues that should be addressed before rationalization.

Remember: The `plan-validator` agent is the expert. Your job is simply to invoke it and present its findings to the user.
