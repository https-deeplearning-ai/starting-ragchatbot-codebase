# RAG Chatbot Documentation Structure

## Generated Files

### Standalone Mermaid Diagrams
1. **architecture-diagram.mermaid** - 4-layer system architecture (high-level)
2. **sequence-diagram.mermaid** - 21-step end-to-end user flow
3. **rag-deep-dive.mermaid** - RAG & Storage component architecture
4. **rag-mid-level-sequence.mermaid** - 17-step RAG processing flow with decision branching

### Interactive HTML Documentation
**architecture-diagram.html** - Complete 4-tab interactive documentation

## Tab Organization

### Tab 1: System Architecture (High-Level)
- **Purpose**: Overall system structure
- **Diagram**: 4-layer vertical architecture
  - Layer 1: Frontend (Vanilla HTML/CSS/JS)
  - Layer 2: API (FastAPI)
  - Layer 3: RAG/AI (Claude + Tools)
  - Layer 4: Database/Storage (ChromaDB)
- **Overview**: Component descriptions for each layer

### Tab 2: System User Flow (High-Level)
- **Purpose**: End-to-end user journey
- **Diagram**: 21-step sequence diagram
  - Steps 1-3: User interaction
  - Steps 4-6: Session & context
  - Steps 7-16: RAG processing
  - Steps 17-21: Response & display
- **Overview**: Flow breakdown by phase

### Tab 3: RAG Components (Deep Dive)
- **Purpose**: Internal RAG & Storage architecture
- **Diagram**: Component architecture
  - RAG/AI Layer: 5 components (RAG System, AI Generator, Tool Manager, Search Tool, Session Manager)
  - Storage Layer: 6 components (ChromaDB, 2 Collections, Document Processor, Chunking, Files)
  - Shows data flows and cross-layer connections
- **Overview**: Component descriptions and internal data flows

### Tab 4: RAG Processing Flow (Deep Dive)
- **Purpose**: Detailed RAG internal processing
- **Diagram**: 17-step mid-level sequence with decision branching
  - Steps 1-4: Request & context loading
  - Steps 5-6: AI decision point (search vs. direct response)
  - Steps 7-13: Conditional search path
  - Steps 14-17: Response & session management
- **Overview**: 
  - Flow breakdown by phase
  - Search mechanics
  - Data structures
  - Processing pipeline
  - Configuration details

## Key Features

### Diagram Characteristics
- **Vertical stacking**: Forced top-to-bottom layout using explicit layer connections
- **Color coding**: Consistent across all diagrams
  - Blue (#e3f2fd): Frontend
  - Orange (#fff3e0): API
  - Green (#e8f5e9): RAG/AI
  - Purple (#f3e5f5): Database/Storage
- **Readable text**: Single-line labels, no overlapping
- **Emojis**: Consistent visual markers for each component type

### UX Design
- **Overview-first layout**: Legend/breakdown appears ABOVE diagrams in all tabs
- **Tabbed interface**: Smooth transitions between perspectives
- **Responsive design**: Mobile-friendly layout
- **Interactive navigation**: Easy switching between high-level and deep-dive views

## Abstraction Levels

### Level 1: System Overview (Tabs 1 & 2)
- **Audience**: Stakeholders, product managers, new team members
- **Focus**: What the system does and how users interact with it
- **Diagrams**: 4-layer architecture + 21-step user flow

### Level 2: RAG Deep Dive (Tabs 3 & 4)
- **Audience**: Developers, architects, AI engineers
- **Focus**: How RAG and storage layers work internally
- **Diagrams**: Component architecture + 17-step processing flow with decision logic

## Documentation Prompt Template

**prompts/system-documentation-prompt.md** - Reusable template for future projects

Contains:
- Master prompt
- Step-by-step execution guide
- Quality checklist
- Common pitfalls
- Usage examples
- Version history

## Usage

### View Documentation
```bash
# Open in browser
open architecture-diagram.html
```

### Test Diagrams
1. Visit https://mermaid.live/
2. Paste contents of any .mermaid file
3. Verify rendering

### Reuse for Other Projects
1. Read prompts/system-documentation-prompt.md
2. Adapt master prompt to your codebase
3. Follow 4-phase workflow:
   - Phase 1: Codebase exploration
   - Phase 2: Architecture diagram
   - Phase 3: Sequence diagram
   - Phase 4: HTML documentation

## Success Criteria Met

✅ All 4 layers visible in top-to-bottom stack  
✅ No overlapping text in diagrams  
✅ Component overview appears before diagrams  
✅ Diagrams reflect actual codebase architecture  
✅ Tabs work correctly with smooth transitions  
✅ HTML renders properly in all modern browsers  
✅ Mid-level abstraction provides balance between overview and details  
✅ Decision points (AI search logic) clearly visible  

---

**Generated**: 2025-11-09  
**Tool**: Claude Code + Mermaid.js  
**Pattern**: 4-layer vertical architecture with RAG
