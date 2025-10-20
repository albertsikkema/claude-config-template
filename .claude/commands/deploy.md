# Deployment Assistant

You are an AI assistant helping to automate the application deployment process. Use specialized subagents **in parallel** for complex tasks to ensure thorough analysis and execution.

> **Note**: This is a generic deployment workflow. Customize steps 4 and 5 for your project's specific needs (build processes, cache invalidation, deployment platform, etc.).

## 0. Initialize CHANGELOG (Prerequisites)

### Ensure CHANGELOG Exists

**Before starting deployment, verify CHANGELOG.md exists:**

1. **Check for CHANGELOG.md** in the project root:
   ```bash
   ls -la CHANGELOG.md
   ```

2. **If CHANGELOG.md does NOT exist**:
   - Read the template from `thoughts/templates/changelog.md.template`
   - Create CHANGELOG.md in the project root
   - Customize the template:
     - Update repository URLs with actual GitHub/GitLab repository
     - Set initial version to match current project version (if version file exists)
     - Add any existing release history from git tags (if available)
   - Report that CHANGELOG.md was created and needs to be reviewed

3. **If CHANGELOG.md exists**:
   - Read it to verify it follows Keep a Changelog format
   - Check if [Unreleased] section exists (create if missing)
   - Report current state and latest version

4. **Validate CHANGELOG format**:
   - Ensure sections exist: Added, Changed, Fixed, Security, Deprecated, Removed, Performance
   - Verify version comparison links are present
   - Report any formatting issues

5. **Output summary**:
   - Report CHANGELOG status (exists, created, or has issues)
   - Show latest released version from CHANGELOG
   - Confirm readiness to proceed with deployment analysis

**Once CHANGELOG.md is confirmed, proceed to Step 1.**

---

## 1. Pre-Deployment Analysis (Use Subagents)

### Research Changes Since Last Release

**Use the general-purpose subagent for this task:**

```
Use Task tool with subagent_type: "general-purpose"
Task: "Analyze repository changes since last release"
Prompt: "Analyze repository changes to understand what needs to be deployed:
1. Check for CHANGELOG.md or similar version tracking file to determine the latest released version
2. Use git tools to list all commits since the last release tag (if available)
   - Try common tag patterns: v*, release-*, version-*
   - If no tags exist, analyze commits from main/master branch
3. If no commits since last release, check for unreleased changes in current branch
4. If commit messages are unclear, analyze the actual code changes for more context
5. Categorize changes into:
   - New Features: User-facing functionality additions
   - Bug Fixes: Issue resolutions and corrections
   - Refactoring: Code improvements without functionality changes
   - Dependencies: Package updates and security patches
   - Documentation: README, comments, or guide updates
   - Infrastructure: CI/CD, configuration, or deployment changes
   - Performance: Optimization improvements
   - Security: Security-related fixes or enhancements
6. Provide a structured summary with specific commit hashes and file changes
7. If no changes found since last release, report that the current version is up to date"
```

---

## 2. Version Management and Documentation (Use Subagents)

### Version Number Update and Changelog Generation

**Use the general-purpose subagent for version management:**

```
Use Task tool with subagent_type: "general-purpose"
Task: "Handle version increment and changelog generation"
Prompt: "Based on the analyzed changes from step 1, manage version updates:

1. **Detect version file location** - Search for version in common locations:
   - package.json (Node.js/JavaScript)
   - pyproject.toml, setup.py, __version__.py (Python)
   - Cargo.toml (Rust)
   - go.mod (Go)
   - build.gradle, pom.xml (Java)
   - composer.json (PHP)
   - pubspec.yaml (Dart/Flutter)
   - AssemblyInfo.cs, .csproj (C#/.NET)
   - VERSION file, version.txt, or similar
   - If no version file found, ask user where version is stored

2. **Recommend version increment** based on semantic versioning:
   - Patch (x.x.1): Bug fixes, security patches, documentation
   - Minor (x.1.0): New features, non-breaking changes, dependency updates
   - Major (1.0.0): Breaking changes, major rewrites, API changes
   - Ask user to confirm the version increment type

3. **Update version** in all detected locations:
   - Primary version file
   - CHANGELOG.md or CHANGELOG.rst header
   - README.md badges or version references
   - Any other files that reference the version

4. **Generate/update CHANGELOG** following Keep a Changelog standard:
   - Add new version entry with today's date
   - Categorize changes into: Added, Changed, Fixed, Security, Deprecated, Removed, Performance
   - Use proper markdown formatting
   - Include links to commits or PRs where applicable
   - If CHANGELOG doesn't exist, create it with full structure and history from git

5. **Provide summary** of version changes and changelog entries created"
```

---

## 3. Build and Pre-Deployment Checks (Customizable)

### Project-Specific Build and Validation

**Use the general-purpose subagent for build verification:**

```
Use Task tool with subagent_type: "general-purpose"
Task: "Execute build and pre-deployment checks"
Prompt: "Perform project-specific build and validation steps:

1. **Detect project type** by examining repository:
   - Check for package.json, pyproject.toml, Cargo.toml, go.mod, etc.
   - Identify build tools and frameworks

2. **Run build process** (if applicable):
   - Node.js: npm run build or yarn build
   - Python: python -m build or poetry build
   - Rust: cargo build --release
   - Go: go build
   - Java: mvn package or gradle build
   - Report any build errors or warnings

3. **Run tests** (if test suite exists):
   - Execute test commands for detected project type
   - Report test results and any failures

4. **Check for deployment artifacts**:
   - Verify build output exists in expected locations
   - Check file sizes and formats are correct
   - Validate required assets are generated

5. **Cache invalidation** (if applicable):
   - PWA: Update service worker cache version/timestamp
   - CDN: Note cache keys that need invalidation
   - Application: Update cache-busting parameters

6. **Environment validation**:
   - Check for required environment variables
   - Verify configuration files are present
   - Validate secrets management is configured

7. **Report summary** of build status, test results, and deployment readiness"
```

---

## 4. Deployment Preparation (Customizable)

### Prepare for Deployment

**Use the general-purpose subagent for deployment preparation:**

```
Use Task tool with subagent_type: "general-purpose"
Task: "Prepare repository for deployment"
Prompt: "Prepare the repository for deployment:

1. **Detect branching strategy**:
   - Check if using dev/develop → main/master workflow
   - Check if using feature branches
   - Check if using trunk-based development
   - Adapt instructions based on strategy detected

2. **Verify git state**:
   - Ensure current branch is appropriate for deployment
   - Verify all changes are committed
   - Check git status is clean with no uncommitted changes
   - Verify no merge conflicts exist

3. **Push changes** to remote:
   - Push current branch to remote
   - Report remote branch status

4. **Create deployment summary** including:
   - New version number ready for tagging
   - Summary of changes being deployed (from step 1)
   - Build/test status (from step 3)
   - Any cache invalidation or configuration updates needed
   - Deployment checklist status

5. **Generate deployment instructions** based on project setup:

   **For Git Tag Deployment:**
   - Provide git commands to tag and push release

   **For Platform-Specific Deployment:**
   - Heroku: heroku deploy instructions
   - Vercel/Netlify: git push triggers automatic deployment
   - AWS: deployment commands or manual steps
   - Docker: docker build and push instructions
   - GitHub Actions: Check if workflow exists, confirm trigger

   **For Manual Merge Workflow:**
   - Provide git commands to merge to main/master and create tags

6. **Report deployment readiness** with all necessary commands and next steps"
```

---

## 5. Create Release (Optional)

### GitHub/GitLab Release Creation

**Use the general-purpose subagent for release creation:**

```
Use Task tool with subagent_type: "general-purpose"
Task: "Create release on hosting platform"
Prompt: "Create a release on the project's hosting platform:

1. **Detect hosting platform**:
   - Check for .github/ directory (GitHub)
   - Check for .gitlab-ci.yml (GitLab)
   - Check git remote URL for platform

2. **Extract release information**:
   - Read the new version number from previous steps
   - Extract changelog entry for this version
   - Identify any release assets to attach (binaries, packages, etc.)

3. **Create release** using platform CLI or API:
   - **GitHub**: Use `gh release create` with version tag
   - **GitLab**: Use `glab release create` with version tag
   - Attach changelog as release notes
   - Upload any build artifacts as release assets

4. **Verify release** was created successfully:
   - Check release is visible on platform
   - Verify all assets are attached
   - Confirm release notes are formatted correctly

5. **Report release details** with link to published release"
```

---

## Deployment Workflow Summary

**Execute these steps in order:**

0. **Initialize**: Check for CHANGELOG.md, create from template if needed, validate format
1. **Analyze**: Use general-purpose subagent to analyze repository changes since last release
2. **Version**: Use general-purpose subagent for version management and changelog generation
3. **Build**: Use general-purpose subagent for build and pre-deployment checks (customize for your project)
4. **Prepare**: Use general-purpose subagent to prepare repository and generate deployment instructions
5. **Release** (Optional): Use general-purpose subagent to create release on hosting platform

**Common Post-Deployment Manual Steps:**

Depending on your project setup, you may need to:

- **Git Tags**: `git tag v[NEW_VERSION] && git push origin v[NEW_VERSION]`
- **Merge Workflow**: `git checkout main && git merge dev && git push`
- **Platform Deploy**: Follow platform-specific commands from step 4
- **Monitor**: Check deployment logs and application health
- **Notify**: Inform team/users about the new release

---

## Customization Guide

This generic deployment command should be customized for your specific project:

### Step 0: CHANGELOG Template
- **Update repository URLs** in the template to match your project
- **Customize sections** based on your project needs (add/remove categories)
- **Set initial version** to match your project's current state

### Step 3: Build and Pre-Deployment Checks
- **Add project-specific build commands**
- **Configure test suite execution**
- **Set up cache invalidation for your stack**
- **Add linting, type checking, or other validation**

### Step 4: Deployment Preparation
- **Configure your deployment platform** (Heroku, Vercel, AWS, Docker, etc.)
- **Set up environment-specific configurations**
- **Add database migration steps if needed**
- **Configure secrets management**

### Step 5: Release Creation
- **Customize release asset generation**
- **Add platform-specific release processes**
- **Configure release notifications** (Slack, email, etc.)

---

## Usage Instructions

**This command automates deployment preparation and provides deployment instructions.**

1. Run `/deploy` to execute steps 0-5
2. Review the deployment summary and ensure everything is correct
3. Follow the provided deployment commands for your platform
4. Monitor the deployment and verify application health

**Begin by executing Step 0: Initialize and verify CHANGELOG.md exists!**
