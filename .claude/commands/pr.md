# Generate PR Description

You are tasked with generating a comprehensive pull request description following the repository's standard template.

## Steps to follow:

1. **Read the PR description template:**
   - First, check if `thoughts/templates/pr_description.md.template` exists
   - If it doesn't exist, inform the user that their template setup is incomplete and they need to create a PR description template at `thoughts/templates/pr_description.md.template`
   - Read the template carefully to understand all sections and requirements

2. **Identify the PR to describe:**
   - Check if the current branch has an associated PR: `gh pr view --json url,number,title,state 2>/dev/null`
   - If no PR exists for the current branch, or if on main/master, list open PRs: `gh pr list --limit 10 --json number,title,headRefName,author`
   - Ask the user which PR they want to describe

3. **Check for existing PR:**
   - Determine if a PR already exists for this branch/number
   - Note whether you'll be creating a new PR or updating an existing one

4. **Gather comprehensive PR information:**
   - Get the full PR diff: `gh pr diff {number}`
   - If you get an error about no default remote repository, instruct the user to run `gh repo set-default` and select the appropriate repository
   - Get commit history: `gh pr view {number} --json commits`
   - Review the base branch: `gh pr view {number} --json baseRefName`
   - Get PR metadata: `gh pr view {number} --json url,title,number,state`

5. **Analyze the changes thoroughly:** (ultrathink about the code changes, their architectural implications, and potential impacts)
   - Read through the entire diff carefully
   - For context, read any files that are referenced but not shown in the diff
   - Understand the purpose and impact of each change
   - Identify user-facing changes vs internal implementation details
   - Look for breaking changes or migration requirements

6. **Handle verification requirements:**
   - Look for any checklist items in the "How to verify it" section of the template
   - For each verification step:
     - If it's a command you can run (like `make check test`, `npm test`, etc.), run it
     - If it passes, mark the checkbox as checked: `- [x]`
     - If it fails, keep it unchecked and note what failed: `- [ ]` with explanation
     - If it requires manual testing (UI interactions, external services), leave unchecked and note for user
   - Document any verification steps you couldn't complete

7. **Generate the description:**
   - Fill out each section from the template thoroughly:
     - Answer each question/section based on your analysis
     - Be specific about problems solved and changes made
     - Focus on user impact where relevant
     - Include technical details in appropriate sections
     - Write a concise changelog entry
   - Ensure all checklist items are addressed (checked or explained)

8. **Show the description to the user:**
   - Display the complete generated PR description
   - Check if a PR already exists for this branch/number
   - Ask the user whether to:
     - Create a new PR (if no PR exists yet)
     - Update the existing PR (if PR already exists)
     - Cancel (if they want to make changes first)

9. **Create or update the PR (upon user confirmation):**
   - If creating a new PR:
     - Use `gh pr create --title "[PR title]" --body "[generated description]"`
     - Confirm the PR was created successfully
   - If updating an existing PR:
     - First save the description to a temporary file
     - Use `gh pr edit {number} --body-file [temp_file]`
     - Clean up the temporary file
     - Confirm the update was successful
   - Optionally save the description to `thoughts/shared/prs/{number}_description.md` for reference
   - If any verification steps remain unchecked, remind the user to complete them before merging

## Important notes:
- This command works across different repositories - always read the local template
- Be thorough but concise - descriptions should be scannable
- Focus on the "why" as much as the "what"
- Include any breaking changes or migration notes prominently
- If the PR touches multiple components, organize the description accordingly
- Always attempt to run verification commands when possible
- Clearly communicate which verification steps need manual testing
