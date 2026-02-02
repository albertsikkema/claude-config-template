# Build C4 Architecture Documentation

You are tasked with creating comprehensive C4 architecture documentation for the codebase, including PlantUML diagrams with enhanced visual aesthetics.

## Initial Setup:

When this command is invoked, respond with:
```
I'm ready to build C4 architecture documentation. I'll create diagrams at three levels (System Context, Container, Component) in both Mermaid and PlantUML formats.

Please provide:
1. Any specific focus areas or components to highlight (optional)
2. Target audience considerations (optional)
```

Then wait for the user's input or proceed with default comprehensive documentation if no specific requirements.

## Steps to follow:

### 1. Fetch C4 Model Documentation (if needed)

- Check if `memories/technical_docs/c4-model.md` exists
- If not, run: `/fetch_technical_docs c4-model`
- This provides the C4 reference for creating proper diagrams

### 2. Index the Codebase

- Check if `memories/codebase/codebase_overview_root_py.md` and `memories/codebase/openapi.json` exist
- If not, run: `/index_codebase`
- This generates:
  - Python codebase index with file structure and function signatures
  - OpenAPI schema from the FastAPI server (if applicable)

### 3. Research and Create C4 Architecture Overview

Use the `/research_codebase` command with this query:
```
Create a comprehensive C4 architecture overview with three levels:
1. System Context - showing the system and its external dependencies
2. Container - showing applications, databases, and services
3. Component - showing internal code structure (routers, services, managers, models)

Use the C4 model documentation (memories/technical_docs/c4-model.md) and codebase analysis (openapi.json + codebase index) as references.
```

This will spawn parallel research agents to analyze:
- Project context and goals
- Authentication architecture
- Core business logic (e.g., chat system, API endpoints)
- Database architecture and models
- External system integrations

### 4. Structure the Research Document

The research document should be created at:
`memories/shared/research/YYYY-MM-DD-c4-model-architecture-overview.md`

With the following structure:

```markdown
---
date: [ISO timestamp]
file-id: [UUID]
researcher: [Name]
git_commit: [commit hash]
branch: [branch name]
repository: [repo name]
topic: "C4 Architecture Documentation"
tags: [research, architecture, c4-model, documentation]
status: complete
---

# C4 Architecture Documentation - [Project Name]

## Project Context
[Project goals, technology stack, current status]

## C4 Architecture - Three-Level Hierarchy

### 🔍 Hierarchical Navigation
[ASCII art showing zoom levels]

### Hierarchy at a Glance
[Comparison table of three levels]

### 🎨 Diagram Formats
Each diagram level includes **two versions**:
1. **Mermaid** - Native GitHub rendering
2. **C4-PlantUML** - Enhanced visual aesthetics

**Standalone PlantUML files** in [`memories/shared/research/c4-diagrams-plantuml/`](c4-diagrams-plantuml/)

---

## 📍 Level 1: System Context

### System Context Diagram (Mermaid)
[Mermaid C4Context diagram]

### System Context Diagram - C4-PlantUML Version
[PlantUML code block with enhanced layout]

**Key visual improvements**:
- ✅ Better spacing with explicit positioning
- ✅ Professional styling
- ✅ Multi-line labels

**Rendered diagram:**

![System Context Diagram](c4-diagrams-plantuml/system-context-diagram.svg)

[📄 View PlantUML source](c4-diagrams-plantuml/system-context-diagram.puml)

### External Actors
[Descriptions of users and personas]

### External Systems
[Descriptions of external dependencies]

---

## 🔍 Level 2: Container

### Container Diagram - Mermaid Version
[Mermaid C4Container diagram]

### Container Diagram - C4-PlantUML Version
[PlantUML code block with enhanced layout]

**Key visual improvements**:
- ✅ Better spacing with explicit positioning
- ✅ Icon sprites for technologies
- ✅ Professional styling
- ✅ Multi-line labels

### Container Details
[Detailed descriptions of each container with file:line references]

---

## 🔬 Level 3: Component

### Component Diagram - Mermaid Version
[Mermaid C4Component diagram with explicit layers]

### Component Diagram - C4-PlantUML Version
[PlantUML code with LAYOUT_LEFT_RIGHT for layer visualization]

**Key visual improvements**:
- ✅ Horizontal layout showing layer progression
- ✅ Explicit layer boundaries
- ✅ Directional relationships

### Component Details
[Detailed descriptions of layers and components with file:line references]

---

## Architecture Insights
[Design patterns, security considerations, performance notes]

## Code References
[Organized list of key files and line numbers]
```

### 5. Create Standalone PlantUML Files

Create directory: `memories/shared/research/c4-diagrams-plantuml/`

**Create these files:**

1. **`system-context-diagram.puml`**:
   ```plantuml
   @startuml C4_System_Context_[ProjectName]
   !include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Context.puml

   LAYOUT_TOP_DOWN()

   title Level 1: System Context Diagram - [Project Name]

   Person(user, "Primary User", "User description")

   System_Boundary(system, "System Name") {
       System(main_system, "Main System", "System description")
   }

   System_Ext(external1, "External System 1", "Description")
   System_Ext(external2, "External System 2", "Description")

   ' Explicit positioning
   Lay_D(user, main_system)
   Lay_R(main_system, external1)

   ' Relationships with multi-line labels
   Rel(user, main_system, "Uses", "HTTPS\nProtocol")
   Rel_U(main_system, external1, "Calls", "HTTPS\nAPI")
   Rel(main_system, external2, "Integrates", "Protocol")

   SHOW_LEGEND()
   @enduml
   ```

2. **`container-diagram.puml`**:
   ```plantuml
   @startuml C4_Container_[ProjectName]
   !include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Container.puml

   LAYOUT_TOP_DOWN()
   !define DEVICONS https://raw.githubusercontent.com/tupadr3/plantuml-icon-font-sprites/master/devicons
   !include DEVICONS/python.puml
   !include DEVICONS/postgresql.puml

   title Level 2: Container Diagram - [Project Name]

   Person(user, "Primary User", "Description")

   System_Boundary(system, "System Name") {
       Container(app, "Application", "Tech Stack", "Description", $sprite="python")
       ContainerDb(db, "Database", "Tech", "Description", $sprite="postgresql")
   }

   System_Ext(external, "External System", "Description")

   ' Explicit positioning
   Lay_D(user, app)
   Lay_R(app, db)

   ' Relationships with multi-line labels
   Rel(user, app, "Uses", "Protocol\nDetails")
   Rel_R(app, db, "Reads/writes", "Protocol")

   SHOW_LEGEND()
   @enduml
   ```

3. **`component-diagram.puml`**:
   ```plantuml
   @startuml C4_Component_[ProjectName]
   !include https://raw.githubusercontent.com/plantuml-stdlib/C4-PlantUML/master/C4_Component.puml

   LAYOUT_LEFT_RIGHT()

   title Level 3: Component Diagram - Internal Structure

   Container_Boundary(app, "Application Container") {
       Boundary(layer1, "Layer 1: API/Presentation") {
           Component(comp1, "Component", "Type", "Description")
       }

       Boundary(layer2, "Layer 2: Business Logic") {
           Component(comp2, "Service", "Type", "Description")
       }
   }

   Rel_D(comp1, comp2, "Uses", "Method")

   SHOW_LEGEND()
   @enduml
   ```

4. **`README.md`**:
   ```markdown
   # C4 PlantUML Diagrams - [Project Name]

   ## 📁 Files
   - `system-context-diagram.puml` - Level 1: System Context showing system in its environment
   - `container-diagram.puml` - Level 2: Container diagram showing apps and databases
   - `component-diagram.puml` - Level 3: Component diagram showing internal structure

   ## 🖼️ How to Render

   ### Option 1: VS Code
   1. Install extension: **PlantUML** by jebbs
   2. Press `Option+D` (Mac) or `Alt+D` (Windows/Linux)

   ### Option 2: Command Line
   ```bash
   # Generate SVG (default - all diagrams)
   python .claude/helpers/build_c4_diagrams.py

   # Generate PNG instead
   python .claude/helpers/build_c4_diagrams.py --format png

   # Generate both PNG and SVG
   python .claude/helpers/build_c4_diagrams.py --format both

   # Or use plantuml directly
   plantuml -tsvg *.puml
   ```

   ### Option 3: Docker
   ```bash
   docker run --rm -v $(pwd):/data plantuml/plantuml -tsvg *.puml
   ```

   ## 🎨 PlantUML Advantages
   - ✅ Explicit positioning (`Lay_D()`, `Lay_R()`, etc.)
   - ✅ Icon sprites (200+ options)
   - ✅ Professional styling
   - ✅ Multi-line labels
   - ✅ Automatic legends

   ## References
   - [C4-PlantUML GitHub](https://github.com/plantuml-stdlib/C4-PlantUML)
   - [Layout Options](https://github.com/plantuml-stdlib/C4-PlantUML/blob/master/LayoutOptions.md)
   ```

### 6. Build PlantUML Diagrams

Run the build script to generate SVG images:
```bash
python .claude/helpers/build_c4_diagrams.py
```

This will:
- Find all .puml files in `memories/shared/research/c4-diagrams-plantuml/`
- Render them to SVG format (default)
- Place output files in the same directory

To generate PNG or both formats:
```bash
python .claude/helpers/build_c4_diagrams.py --format png
python .claude/helpers/build_c4_diagrams.py --format both
```

### 7. Update Main Document with Image Links

Add image embeds to the main research document after each PlantUML code block:

```markdown
### Container Diagram - C4-PlantUML Version

```plantuml
[PlantUML code]
```

**Rendered diagram:**

![Container Diagram](c4-diagrams-plantuml/container-diagram.svg)

[📄 View PlantUML source](c4-diagrams-plantuml/container-diagram.puml)
```

### 8. Final Verification

Check that:
- ✅ All three C4 levels are documented (System Context, Container, Component)
- ✅ Both Mermaid and PlantUML versions exist for all three levels
- ✅ Standalone `.puml` files are in `c4-diagrams-plantuml/` directory:
  - `system-context-diagram.puml`
  - `container-diagram.puml`
  - `component-diagram.puml`
- ✅ README.md with rendering instructions exists
- ✅ PlantUML diagrams are built to SVG (if plantuml/docker available)
- ✅ Relative links to diagrams work correctly
- ✅ All file:line references are accurate
- ✅ Hierarchical navigation is clear with ASCII art and icons

### 9. Present Summary

Present to the user:
```
✅ C4 Architecture Documentation Complete!

**Created:**
- Main documentation: `memories/shared/research/YYYY-MM-DD-c4-model-architecture-overview.md`
- PlantUML diagrams: `memories/shared/research/c4-diagrams-plantuml/`
  - system-context-diagram.puml (with SVG)
  - container-diagram.puml (with SVG)
  - component-diagram.puml (with SVG)
  - README.md

**C4 Levels Documented:**
1. 📍 System Context - High-level view with external systems (Level 1)
2. 🔍 Container - Technical building blocks (apps, databases) (Level 2)
3. 🔬 Component - Internal code structure (layers and components) (Level 3)

**Diagram Formats:**
- Mermaid (native GitHub rendering) - All 3 levels
- PlantUML SVG (enhanced visual aesthetics with icons, layouts, and styling) - All 3 levels

**Next Steps:**
- View diagrams in VS Code with PlantUML extension (Option+D)
- Rebuild diagrams: `python .claude/helpers/build_c4_diagrams.py`
- Generate PNG instead: `python .claude/helpers/build_c4_diagrams.py --format png`
- Update diagrams as the architecture evolves
```

## Important Notes:

- **PlantUML Layout Control**: Use `Lay_D()`, `Lay_R()`, `Lay_U()`, `Lay_L()` for explicit positioning
- **Icon Sprites**: Include relevant technology icons from devicons or other sprite libraries
- **Multi-line Labels**: Use `\n` in relationship labels for better readability
- **Boundaries**: Use `System_Boundary()` and `Boundary()` to group related elements
- **Legends**: Always include `SHOW_LEGEND()` for automatic legend generation
- **Relative Paths**: All links should be relative to the main document location
- **File References**: Include file:line references from codebase analysis
- **Hierarchical Clarity**: Use ASCII art, icons (📍 🔍 🔬), and comparison tables
- **Both Formats**: Maintain both Mermaid (for GitHub) and PlantUML (for aesthetics)
- **Build Automation**: The Python script handles rendering with local plantuml or Docker fallback

## Dependencies:

The `build_c4_diagrams.py` script automatically handles rendering with one of these options:

**Option 1: PlantUML (Recommended)**
- macOS: `brew install plantuml` (automatically includes Java and Graphviz dependencies)
- Linux (Ubuntu/Debian): `sudo apt-get install plantuml`
- Linux (Fedora/RHEL): `sudo dnf install plantuml`

**Option 2: Docker (Fallback)**
- Install Docker Desktop (macOS/Windows) or Docker Engine (Linux)
- The script will automatically use Docker if plantuml is not found locally
- No manual image pull needed - script handles it automatically

**No dependencies needed:**
- If neither is available, the script will show installation instructions
- Python 3.6+ is required (standard in most environments)

