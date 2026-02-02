---
description: Intelligently fetch documentation for project packages from context7.com
---

You will help fetch documentation for the project's core frameworks and packages from context7.com. This is an LLM-driven workflow where you make intelligent decisions about which documentation to fetch.

## Workflow

Follow these steps for each package:

### Step 1: Discover Packages

Run the discover command to find all packages in the project:

```bash
python3 .claude/helpers/fetch-docs.py discover
```

This will return JSON with all packages from:
- `frontend/package.json` (JavaScript/TypeScript)
- `go.mod` (Go)
- `pyproject.toml` (Python)

**Your task**: Analyze the packages and identify the core frameworks/libraries that would benefit from having documentation. Focus on:
- Major frameworks (Svelte, React, Vue, etc.)
- Build tools (Vite, Webpack, etc.)
- Backend frameworks (Wails, Express, FastAPI, etc.)
- Core libraries (Zod, TypeScript, etc.)

**Skip** small utilities like:
- CSS utilities (clsx, tailwind-merge)
- Icon libraries
- Small helper packages
- ESLint/Prettier plugins

### Step 2: Search for Each Package

For each core package you identified, search context7:

```bash
python3 .claude/helpers/fetch-docs.py search <package-name>
```

This returns the top 5 results as JSON with:
- `rank`: Position (1-5)
- `project`: Context7 project path
- `title`: Project title
- `description`: Description
- `stars`: GitHub stars (-1 if N/A)
- `trustScore`: Trust score 0-10 (-1 if N/A)
- `vip`: Whether it's an official/VIP project
- `type`: repo, website, or llmstxt
- `url`: Direct URL to llms.txt

**Your task**: Analyze the top 5 results and select the BEST one based on:

1. **VIP status** - Prefer `vip: true` (official repos)
2. **Type** - Prefer `type: "repo"` over `type: "website"` or `type: "llmstxt"`
3. **Trust score** - Higher is better (0-10 scale)
4. **Stars** - More stars generally means more popular/maintained
5. **Project path** - Prefer official organizations:
   - `/sveltejs/` for Svelte packages
   - `/tailwindlabs/` for Tailwind
   - `/vitejs/` for Vite
   - `/wailsapp/` for Wails
   - `/golang/` for Go
   - etc.
6. **Description** - Should match the package you're looking for

**Example decision process**:
```json
{
  "results": [
    {
      "rank": 1,
      "project": "/sveltejs/svelte",
      "vip": true,
      "type": "repo",
      "trustScore": 8.1,
      "stars": 82465
    },
    {
      "rank": 2,
      "project": "/websites/v4_svelte_dev",
      "vip": false,
      "type": "website",
      "trustScore": 7.5,
      "stars": -1
    }
  ]
}
```
**Decision**: Choose rank 1 (`/sveltejs/svelte`) because:
- ✅ VIP status (official)
- ✅ Repository type (not website)
- ✅ Higher trust score
- ✅ Massive GitHub stars
- ✅ Official organization

### Step 3: Fetch Documentation

Once you've selected the best result, fetch it:

```bash
python3 .claude/helpers/fetch-docs.py get <project-path> <package-name>
```

Example:
```bash
python3 .claude/helpers/fetch-docs.py get /sveltejs/svelte svelte
```

This will:
- Download the llms.txt documentation
- Save to `memories/technical_docs/<package-name>.md`
- Return JSON confirming success

**If file already exists**: Use `--overwrite` flag to replace:
```bash
python3 .claude/helpers/fetch-docs.py get /sveltejs/svelte svelte --overwrite
```

### Step 4: Repeat

Continue with the next package until you've fetched documentation for all core frameworks.

## Example Complete Workflow

```
User: /fetch_technical_docs
```

**You should do:**

1. **Discover packages**:
```bash
python3 .claude/helpers/fetch-docs.py discover
```

2. **Analyze output** and identify core packages (example):
   - svelte (version ^5.0.0)
   - kit (SvelteKit, version ^2.22.0)
   - tailwindcss (version ^4.0.0)
   - vite (version ^7.0.4)
   - wails (from go.mod, version v2.10.2)
   - zod (version ^4.1.11)

3. **Search for first package** (svelte):
```bash
python3 .claude/helpers/fetch-docs.py search svelte
```

4. **Analyze results** and choose best match:
   - Result 1: `/sveltejs/svelte` (VIP, repo, 82k stars, trust 8.1) ✅ **BEST**
   - Result 2: `/websites/v4_svelte_dev` (website, no stars, trust 7.5)
   - ...

5. **Fetch documentation**:
```bash
python3 .claude/helpers/fetch-docs.py get /sveltejs/svelte svelte
```

6. **Confirm success** and move to next package

7. **Search for SvelteKit**:
```bash
python3 .claude/helpers/fetch-docs.py search sveltekit
```

8. **Continue** until all core packages are done

9. **Report summary**:
```
✅ Documentation fetched successfully!

Downloaded:
- svelte (/sveltejs/svelte)
- sveltekit (/sveltejs/kit)
- tailwindcss (/tailwindlabs/tailwindcss.com)
- vite (/vitejs/vite)
- wails (/wailsapp/wails)
- zod (/colinhacks/zod)

All documentation saved to: memories/technical_docs/
```

## Tips for Making Good Decisions

### Prefer Official Sources
- Look for official organization names in project path
- VIP badge is a strong indicator
- Higher trust scores are more reliable

### Consider the Type
1. **repo** - Source code repository (usually best)
2. **website** - Documentation website (good alternative)
3. **llmstxt** - Custom llms.txt file (may be incomplete)

### Trust Score Guide
- **8.0-10.0**: Excellent, very trustworthy
- **6.0-7.9**: Good, generally reliable
- **4.0-5.9**: Moderate, verify quality
- **< 4.0**: Low, consider alternatives
- **-1**: Not scored

### Watch Out For
- Unofficial forks or mirrors
- Outdated project paths
- Projects with very low stars (< 100)
- Misleading names (e.g., "svelte-headless" when you want "svelte")

## Error Handling

If a package search returns no results or poor matches:
- Try a different search term (e.g., "sveltekit" vs "svelte-kit")
- Try the original package name from package.json
- Skip if it's not critical
- Inform the user that documentation wasn't found

If fetch fails:
- The llms.txt file might not exist for that project
- Try the next best result from search
- Report the failure to the user

## Output

Be conversational and informative. For each package:
1. State what you're searching for
2. Show the top 2-3 candidates briefly
3. Explain why you chose the best one
4. Confirm successful fetch

Keep the user informed of progress!
