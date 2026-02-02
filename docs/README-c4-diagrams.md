# C4 Architecture Diagrams

Generate visual architecture diagrams from PlantUML C4 model definitions using PlantUML or Docker.

## Overview

The `build_c4_diagrams.py` script converts C4 PlantUML diagram definitions (`.puml` files) into visual formats:

- **PNG** - Raster images for documentation and presentations
- **SVG** - Vector graphics for web and scalable displays

**Primary Usage:** This script is typically invoked via the `/build_c4_docs` slash command in Claude Code, which automatically handles diagram building as part of the C4 documentation workflow. Direct script usage is available for manual builds or automation.

**Key Features:**
- ✅ Automatic discovery of all `.puml` files in a directory
- ✅ Local PlantUML or Docker fallback (no manual setup needed)
- ✅ Multiple output formats (PNG, SVG, or both)
- ✅ In-place rendering (outputs alongside source files)

## Quick Start

### Use via Claude Code (Recommended)

```bash
/build_c4_docs
```

Claude will automatically:
1. Locate C4 PlantUML files in your project
2. Build diagrams to the appropriate format
3. Handle PlantUML/Docker detection automatically

### Manual Usage

For direct script invocation or automation:

```bash
# Build all diagrams in default directory to SVG
python .claude/helpers/build_c4_diagrams.py

# Build to PNG format
python .claude/helpers/build_c4_diagrams.py --format png

# Build to both PNG and SVG
python .claude/helpers/build_c4_diagrams.py --format both
```

### Custom Directory

```bash
# Build diagrams from a specific directory
python .claude/helpers/build_c4_diagrams.py --dir path/to/diagrams

# Example: Custom architecture docs location
python .claude/helpers/build_c4_diagrams.py --dir docs/architecture
```

### Force Docker Usage

```bash
# Use Docker even if plantuml is installed locally
python .claude/helpers/build_c4_diagrams.py --docker
```

## How It Works

1. **Discovery** - Scans the target directory for all `.puml` files
2. **Validation** - Checks for PlantUML installation or Docker availability
3. **Rendering** - Converts each `.puml` file to the specified format(s)
4. **Output** - Places generated images alongside source files

**Example Directory Before:**
```
memories/shared/research/c4-diagrams-plantuml/
├── context-diagram.puml
├── container-diagram.puml
└── component-diagram.puml
```

**Example Directory After:**
```
memories/shared/research/c4-diagrams-plantuml/
├── context-diagram.puml
├── context-diagram.svg        ← Generated
├── container-diagram.puml
├── container-diagram.svg      ← Generated
├── component-diagram.puml
└── component-diagram.svg      ← Generated
```

## Command-Line Options

```bash
python .claude/helpers/build_c4_diagrams.py [OPTIONS]

Options:
  --format FORMAT    Output format: png, svg, or both
                    Default: svg

  --dir PATH        Directory containing .puml files
                    Default: memories/shared/research/c4-diagrams-plantuml

  --docker          Force use of Docker instead of local plantuml
                    Useful if local installation has issues

  --help            Show help message and exit
```

## Prerequisites

You need **one** of the following:

### Option 1: Local PlantUML (Recommended)

**macOS:**
```bash
brew install plantuml
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install plantuml
```

**Linux (Fedora/RHEL):**
```bash
sudo dnf install plantuml
```

**Verify Installation:**
```bash
plantuml -version
# Should output PlantUML version info
```

### Option 2: Docker

If you don't want to install PlantUML locally, the script can use Docker:

**Install Docker:**
- macOS/Windows: [Docker Desktop](https://www.docker.com/products/docker-desktop)
- Linux: [Docker Engine](https://docs.docker.com/engine/install/)

**Verify Installation:**
```bash
docker --version
# Should output Docker version info
```

**The script will:**
1. Try local `plantuml` first
2. Fall back to Docker automatically if `plantuml` not found
3. Show clear error if neither is available

## Rendering PlantUML Files

### Method 1: Via Build Script (Recommended)

```bash
# Build all diagrams
python .claude/helpers/build_c4_diagrams.py

# Or via slash command
/build_c4_docs
```

### Method 2: VS Code Extension

1. Install extension: **PlantUML** by jebbs
2. Open any `.puml` file
3. Press `Alt+D` (Windows/Linux) or `Option+D` (Mac) to preview
4. Right-click → "Export Current Diagram" for PNG/SVG

### Method 3: Command Line (Direct)

```bash
# Generate SVG (recommended)
plantuml -tsvg context-diagram.puml

# Generate PNG
plantuml -tpng context-diagram.puml

# Generate all diagrams in directory
plantuml -tsvg *.puml

# Generate PDF (for printing)
plantuml -tpdf context-diagram.puml
```

### Method 4: Online Editor

Visit: https://www.plantuml.com/plantuml/uml/

Paste the entire `.puml` file content and click "Submit"

### Method 5: Docker (Direct)

```bash
docker run --rm -v $(pwd):/data plantuml/plantuml -tsvg container-diagram.puml
```

### Method 6: CI/CD Integration

Add to GitHub Actions:

```yaml
- name: Generate C4 Diagrams
  uses: cloudbees/plantuml-github-action@master
  with:
    args: -tsvg -o output memories/shared/research/c4-diagrams-plantuml/*.puml
```

## Output Formats

### PNG (Raster)

**Best for:**
- 📄 Documentation (Word, Google Docs, Notion)
- 📊 Presentations (PowerPoint, Keynote)
- 💬 Chat/Slack sharing
- 📧 Email attachments

**Characteristics:**
- Fixed resolution
- Larger file sizes
- Universal compatibility

**Example:**
```bash
python .claude/helpers/build_c4_diagrams.py --format png
```

### SVG (Vector)

**Best for:**
- 🌐 Web pages and wikis
- 📱 Responsive documentation
- 🔍 Zoomable diagrams
- 🎨 Further editing in design tools

**Characteristics:**
- Scalable (no quality loss)
- Smaller file sizes
- Editable in Illustrator/Inkscape

**Example:**
```bash
python .claude/helpers/build_c4_diagrams.py --format svg
```

### PDF

**Best for:**
- 📃 Printing
- 📋 Formal documentation
- 📚 Archival purposes

**Example:**
```bash
plantuml -tpdf *.puml
```

### Both PNG and SVG

**Best for:**
- 🎯 Maximum flexibility
- 📦 Complete documentation packages
- 🔄 Different use cases

**Example:**
```bash
python .claude/helpers/build_c4_diagrams.py --format both
```

## PlantUML Layout and Styling

### Layout Direction

```plantuml
LAYOUT_TOP_DOWN()      ' Default: vertical hierarchy
LAYOUT_LEFT_RIGHT()    ' Horizontal: better for showing layers
```

**When to use:**
- **TOP_DOWN**: System Context, Container diagrams
- **LEFT_RIGHT**: Component diagrams showing layer progression

### Manual Positioning

Control exact placement of elements:

```plantuml
Lay_U(element1, element2)  ' element2 UP from element1
Lay_D(element1, element2)  ' element2 DOWN from element1
Lay_L(element1, element2)  ' element2 LEFT of element1
Lay_R(element1, element2)  ' element2 RIGHT of element1
```

**Example:**
```plantuml
Lay_D(user, app)      ' Place app below user
Lay_R(app, database)  ' Place database to right of app
```

### Relationship Directions

```plantuml
Rel(from, to, "label", "tech")      ' Auto-direction
Rel_U(from, to, "label", "tech")    ' Upward arrow
Rel_D(from, to, "label", "tech")    ' Downward arrow
Rel_L(from, to, "label", "tech")    ' Leftward arrow
Rel_R(from, to, "label", "tech")    ' Rightward arrow
```

### Add Icons/Sprites

```plantuml
!define DEVICONS https://raw.githubusercontent.com/tupadr3/plantuml-icon-font-sprites/master/devicons
!include DEVICONS/python.puml
!include DEVICONS/postgresql.puml
!include DEVICONS/react.puml

Container(app, "Backend API", "Python", "FastAPI service", $sprite="python")
ContainerDb(db, "Database", "PostgreSQL", "User data", $sprite="postgresql")
Container(web, "Frontend", "React", "Web UI", $sprite="react")
```

**Available icon sets:**
- devicons - Development tools (Python, PostgreSQL, React, etc.)
- devicons2 - Extended development icons
- font-awesome - General purpose icons
- material - Material Design icons

[Browse all sprites](https://github.com/tupadr3/plantuml-icon-font-sprites)

### Multi-line Labels

```plantuml
' Single-line (compact)
Rel(app, db, "Reads/writes", "asyncpg")

' Multi-line (more detail)
Rel(app, db, "Reads/writes", "asyncpg\n(async queries)\nwith pooling")
```

### Grouping with Boundaries

```plantuml
System_Boundary(boundary_name, "Boundary Label") {
    Container(app1, "App 1", "Tech", "Description")
    Container(app2, "App 2", "Tech", "Description")
}

Boundary(layer_name, "Layer Name") {
    Component(comp1, "Component", "Type", "Description")
}
```

**Example:**
```plantuml
System_Boundary(cloud, "Azure Infrastructure") {
    Container(api, "API", "Python", "Backend API")
    ContainerDb(db, "DB", "PostgreSQL", "Database")
}
```

### Hide/Show Person Sprites

```plantuml
HIDE_PERSON_SPRITE()   ' Remove person icon
SHOW_PERSON_SPRITE()   ' Show person icon (default)
```

### Show Legend

```plantuml
SHOW_LEGEND()   ' Automatic legend generation
```

Always include at the end of your diagram for automatic documentation of element types.

## Examples

### Build Default Location

```bash
# Build all diagrams in memories/shared/research/c4-diagrams-plantuml/
python .claude/helpers/build_c4_diagrams.py
```

**Output:**
```
Found 3 PlantUML file(s):
  - context-diagram.puml
  - container-diagram.puml
  - component-diagram.puml

Building context-diagram.puml to SVG...
  ✅ context-diagram.svg
Building container-diagram.puml to SVG...
  ✅ container-diagram.svg
Building component-diagram.puml to SVG...
  ✅ component-diagram.svg

✅ Successfully built 3 diagram(s) to SVG

Output directory: /path/to/memories/shared/research/c4-diagrams-plantuml
```

### Custom Architecture Documentation

```bash
# Build diagrams from docs/architecture/
python .claude/helpers/build_c4_diagrams.py \
  --dir docs/architecture \
  --format both
```

### Using Docker Explicitly

```bash
# Force Docker usage (useful for CI/CD or containerized environments)
python .claude/helpers/build_c4_diagrams.py --docker --format png
```

**Output:**
```
⚠️  plantuml not found locally, checking for Docker...
✅ Docker found, using Docker method

Found 3 PlantUML file(s):
  - context-diagram.puml
  - container-diagram.puml
  - component-diagram.puml

Building context-diagram.puml to PNG (Docker)...
  ✅ context-diagram.png
...
```

## Integration with C4 Workflow

This script is part of the C4 architecture documentation workflow, primarily accessed through the `/build_c4_docs` slash command:

### 1. Create C4 PlantUML Definitions

Use Claude Code to generate `.puml` files:

```bash
# Ask Claude to create C4 diagrams
"Create C4 architecture diagrams for the authentication system"
```

Claude will create files like:
- `context-diagram.puml` - System context
- `container-diagram.puml` - Container view
- `component-diagram.puml` - Component details

### 2. Build Visual Diagrams

**Via slash command (recommended):**
```bash
/build_c4_docs
```

**Or manually:**
```bash
python .claude/helpers/build_c4_diagrams.py
```

### 3. Include in Documentation

Reference the generated images in your documentation:

```markdown
## System Architecture

### Context Diagram
![Context Diagram](./memories/shared/research/c4-diagrams-plantuml/context-diagram.svg)

### Container Diagram
![Container Diagram](./memories/shared/research/c4-diagrams-plantuml/container-diagram.svg)
```

### 4. Version Control

**Recommended `.gitignore` entries:**
```gitignore
# Include source definitions
# !*.puml

# Exclude generated images (optional - depends on team preference)
*.png
*.svg

# OR include images for easy viewing
# (no .gitignore entry needed)
```

**Team Preference A - Source Only:**
- Commit `.puml` files only
- Generate images locally as needed
- Keeps repository smaller

**Team Preference B - Include Images:**
- Commit both `.puml` and generated images
- Images viewable directly in GitHub/GitLab
- No build step for reviewers

## Mermaid vs PlantUML

| Feature | Mermaid | PlantUML |
|---------|---------|----------|
| **Layout Control** | Order-based only | ✅ Explicit positioning |
| **Icons** | ❌ No | ✅ 200+ icon sets |
| **Styling** | Limited | ✅ Extensive (shadows, gradients) |
| **Legend** | Manual | ✅ Automatic |
| **Multi-line labels** | ❌ No | ✅ Yes (`\n`) |
| **Boundaries/Grouping** | Basic | ✅ Advanced |
| **GitHub rendering** | ✅ Native | ⚠️ Requires image |
| **Best for** | Simple diagrams | Complex architectures |

### When to Use Each

**Use Mermaid when:**
- ✅ Diagrams are simple (< 10 elements)
- ✅ Need native GitHub/Markdown rendering
- ✅ Quick documentation in README files
- ✅ Rapid iteration without build step

**Use PlantUML when:**
- ✅ Diagrams are complex (> 10 elements)
- ✅ Visual aesthetics matter (presentations, documentation)
- ✅ Need precise layout control
- ✅ Want icons and advanced styling
- ✅ Building comprehensive architecture documentation
- ✅ Creating diagrams for formal deliverables

**Best Practice:** Use both!
- Include Mermaid in research documents for quick GitHub viewing
- Create PlantUML versions for enhanced visuals and exports
- The `/build_c4_docs` command creates both automatically

## Troubleshooting

### "Neither plantuml nor Docker found"

**Cause:** No rendering engine available

**Solution:**
```bash
# Install PlantUML (recommended)
brew install plantuml

# OR install Docker
# https://www.docker.com/products/docker-desktop
```

### "No .puml files found"

**Cause:** Wrong directory or no PlantUML files

**Solution:**
```bash
# Check for .puml files
ls memories/shared/research/c4-diagrams-plantuml/*.puml

# Specify correct directory
python .claude/helpers/build_c4_diagrams.py --dir /path/to/diagrams
```

### "Error building diagrams"

**Cause:** Syntax error in `.puml` file

**Solution:**
1. Open the `.puml` file and check for syntax errors
2. Test individual file:
   ```bash
   plantuml your-diagram.puml
   ```
3. Common issues:
   - Missing `@startuml` / `@enduml` tags
   - Invalid C4 syntax
   - Unclosed quotes or brackets
   - Missing `!include` statements

### Docker is slow

**Cause:** Docker pulls PlantUML image on first run

**Solution:**
```bash
# Pre-pull the image
docker pull plantuml/plantuml

# OR install PlantUML locally for better performance
brew install plantuml
```

### Permission denied (Docker)

**Cause:** Docker doesn't have permission to mount directory

**Solution:**
```bash
# On macOS: Add directory to Docker Desktop file sharing
# Docker Desktop → Preferences → Resources → File Sharing

# On Linux: Check Docker group membership
sudo usermod -aG docker $USER
# Log out and back in for changes to take effect
```

### PlantUML preview not working in VS Code

**Cause:** Extension not installed or Java missing

**Solution:**
1. Install VS Code extension: **PlantUML** by jebbs
2. Ensure Java is installed:
   ```bash
   java -version
   # If not installed: brew install openjdk
   ```
3. Restart VS Code

## Best Practices

### Directory Organization

**Recommended structure:**
```
memories/shared/research/
├── c4-diagrams-plantuml/      # Source .puml files
│   ├── system-context-diagram.puml
│   ├── container-diagram.puml
│   ├── component-diagram.puml
│   ├── README.md              # Rendering instructions
│   ├── system-context-diagram.svg    # Generated images
│   ├── container-diagram.svg
│   └── component-diagram.svg
└── 2025-10-20-system-architecture.md  # Research doc referencing diagrams
```

### File Naming

**Use descriptive names:**
```
✅ Good:
- auth-context-diagram.puml
- payment-container-diagram.puml
- user-service-component-diagram.puml

❌ Avoid:
- diagram1.puml
- temp.puml
- new-diagram-final-v2.puml
```

### Format Selection

**Choose based on use case:**
```bash
# Documentation only → SVG (smaller, scalable)
python .claude/helpers/build_c4_diagrams.py --format svg

# Presentations only → PNG (universal compatibility)
python .claude/helpers/build_c4_diagrams.py --format png

# Mixed usage → Both formats
python .claude/helpers/build_c4_diagrams.py --format both

# Printing → PDF
plantuml -tpdf *.puml
```

### Layout Strategy

**System Context (Level 1):**
```plantuml
LAYOUT_TOP_DOWN()     ' Users at top, system in middle, externals around
```

**Container (Level 2):**
```plantuml
LAYOUT_TOP_DOWN()     ' User → Frontend → Backend → Database
```

**Component (Level 3):**
```plantuml
LAYOUT_LEFT_RIGHT()   ' Show layer progression: API → Business → Data
```

### Regeneration

**Rebuild when diagrams change:**
```bash
# After updating .puml files
python .claude/helpers/build_c4_diagrams.py

# Automate with file watcher (optional)
# fswatch -o memories/shared/research/c4-diagrams-plantuml/*.puml | \
#   xargs -n1 -I{} python .claude/helpers/build_c4_diagrams.py
```

## Performance

**Typical build times:**
- Local PlantUML: ~1-2 seconds per diagram
- Docker: ~3-5 seconds per diagram (first run slower due to image pull)

**Large diagram sets:**
- 10 diagrams (local): ~15 seconds
- 10 diagrams (Docker): ~40 seconds

**Optimization tips:**
- Use local PlantUML for faster builds
- Build to single format if you don't need both
- Consider caching in CI/CD pipelines
- Pre-pull Docker image for consistent performance

## Technical Details

### PlantUML Command

**Local execution:**
```bash
plantuml -tsvg context-diagram.puml
# Generates: context-diagram.svg
```

**Docker execution:**
```bash
docker run --rm \
  -v /path/to/diagrams:/data \
  plantuml/plantuml \
  -tsvg /data/context-diagram.puml
# Generates: /path/to/diagrams/context-diagram.svg
```

### Supported PlantUML Features

The script works with all PlantUML syntax, including:
- ✅ C4 models (context, container, component, code)
- ✅ Standard UML diagrams (class, sequence, activity)
- ✅ Sequence diagrams
- ✅ Class diagrams
- ✅ Entity-relationship diagrams
- ✅ Custom styling and themes
- ✅ Icon sprites and includes

### C4-PlantUML Includes

```plantuml
!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Context.puml
!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Container.puml
!include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Component.puml
```

## Why Use This Script?

**Instead of manual PlantUML:**
- 🚀 Batch processing (all diagrams at once)
- 🔄 Automatic Docker fallback (no setup hassles)
- 📁 Organized output (same directory as source)
- ✅ Clear error messages and progress
- 🎯 Integrated with Claude Code workflow

**For Architecture Documentation:**
- 📊 Visual communication of system design
- 🗂️ Versioned alongside code (`.puml` files in git)
- 🔍 Easy to review in PRs
- 📚 Integrated with research/planning workflow
- 🎨 Professional aesthetics for presentations

## Related Commands

- `/build_c4_docs` - **Primary command** that uses this script to build C4 diagrams
- `/research_codebase` - Research that can generate C4 diagrams
- `/create_plan` - Plans that reference architecture diagrams
- `/project` - Project documentation that includes architecture

## See Also

- [C4 Model Documentation](https://c4model.com/) - Official C4 model guide
- [PlantUML C4](https://github.com/plantuml-stdlib/C4-PlantUML) - C4 PlantUML library
- [PlantUML Official](https://plantuml.com/) - PlantUML documentation
- [Icon Sprites](https://github.com/tupadr3/plantuml-icon-font-sprites) - Available icon sets
- [Layout Options](https://github.com/plantuml-stdlib/C4-PlantUML/blob/master/LayoutOptions.md) - C4 layout guide
- [WORKFLOW.md](../WORKFLOW.md) - Complete development workflow
