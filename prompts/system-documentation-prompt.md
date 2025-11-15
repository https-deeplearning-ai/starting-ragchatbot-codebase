# System Documentation & Architecture Diagram Generator - Prompt Template

**Purpose**: Generate comprehensive system documentation with interactive architecture and sequence diagrams for any codebase.

**Objective**: Gain a complete system overview through:
1. Detailed architecture exploration
2. Visual layered architecture diagram
3. Core user flow sequence diagram
4. Interactive tabbed HTML documentation

---

## MASTER PROMPT

```
Based on the architecture diagram prompt guidelines in this repository, explore the codebase at the root directory and create comprehensive system documentation with the following deliverables:

1. **ARCHITECTURE DIAGRAM** (Mermaid format)
   - Follow a top-to-bottom 4-layer approach
   - Layer 1 (Top): Frontend/UI Layer
   - Layer 2: API/Application Layer
   - Layer 3: Business Logic/Processing Layer (e.g., RAG, Services)
   - Layer 4 (Bottom): Database/Storage Layer
   - Use appropriate emojis and color coding
   - Ensure all layers are stacked vertically
   - Include internal component flows within each layer

2. **SEQUENCE DIAGRAM** (Mermaid format)
   - Document the core user flow (main use case)
   - Use auto-numbering for steps
   - Include all major system participants
   - Show request and response flows
   - Add notes for key phases
   - Keep labels concise and readable

3. **INTERACTIVE HTML DOCUMENTATION**
   - Create a tabbed interface with:
     - Tab 1: Architecture Overview (with component legend ABOVE diagram)
     - Tab 2: User Flow Sequence (with flow breakdown ABOVE diagram)
   - Include system metadata (tech stack, architecture pattern, etc.)
   - Use Mermaid CDN for diagram rendering
   - Professional styling with responsive design
   - Color-coded sections matching diagram layers

**REQUIREMENTS**:
- Explore the codebase thoroughly before creating diagrams
- Identify the actual technology stack, design patterns, and architecture
- Make diagrams specific to this codebase (not generic)
- Ensure text readability in all diagrams
- Follow the 3-tier layout pattern from architecture-diagram-prompt-template.md
- Place overview/legend sections ABOVE diagrams for better UX
- Test that vertical layer stacking works (User → Layer1 → Layer2 → Layer3 → Layer4)

**OUTPUT FILES**:
1. `architecture-diagram.mermaid` - Standalone architecture diagram
2. `sequence-diagram.mermaid` - Standalone sequence diagram
3. `architecture-diagram.html` - Complete interactive documentation

**KEY SUCCESS CRITERIA**:
✓ All 4 layers clearly visible in top-to-bottom stack
✓ No overlapping text in diagrams
✓ Component overview appears before diagrams
✓ Diagrams reflect actual codebase architecture
✓ Tabs work correctly with smooth transitions
✓ HTML renders properly in all modern browsers
```

---

## STEP-BY-STEP EXECUTION GUIDE

### Phase 1: Codebase Exploration (CRITICAL)

**Instruction to AI**:
```
Before creating any diagrams, explore the codebase thoroughly to understand:

1. **Project Structure**
   - Root directory contents
   - Main application folders (frontend, backend, services, etc.)
   - Configuration files (package.json, requirements.txt, pyproject.toml, etc.)

2. **Technology Stack**
   - Programming languages
   - Frameworks and libraries
   - Database systems
   - External services/APIs

3. **Architecture Pattern**
   - Monolithic vs Microservices vs Serverless
   - Layered architecture components
   - Design patterns in use

4. **Key Components**
   - Entry points (main.py, index.js, app.py)
   - API endpoints/routes
   - Data models
   - Business logic modules
   - Storage/database interactions

5. **Data Flow**
   - How requests flow through the system
   - Main user journeys
   - Integration points

Use the Task tool with subagent_type=Plan to explore thoroughly.
Provide a detailed summary before proceeding to diagram creation.
```

### Phase 2: Architecture Diagram Creation

**Instruction to AI**:
```
Create a 4-layer vertical architecture diagram with these specifications:

**LAYOUT RULES** (CRITICAL):
- Use `graph TB` for top-to-bottom orientation
- Define layers as: User → Layer1 → Layer2 → Layer3 → Layer4
- Each layer uses `direction LR` internally for horizontal component layout
- Force vertical stacking with explicit connections: Layer1 --> Layer2 --> Layer3 --> Layer4

**LAYER DEFINITIONS**:

Layer 1 - FRONTEND/UI LAYER (🎨 Blue #e3f2fd):
- Technology: [Framework name]
- Components: Pages, UI Components, Client-side utilities
- Use bullet points (•) for clarity

Layer 2 - API/APPLICATION LAYER (🔌 Orange #fff3e0):
- Technology: [API framework]
- Components: Endpoints, Middleware, Session management
- Show request handling flow

Layer 3 - BUSINESS LOGIC LAYER (🤖 Green #e8f5e9 or appropriate):
- Technology: [Core processing technology]
- Components: Main business logic, orchestration, integrations
- Show internal processing flow

Layer 4 - DATABASE/STORAGE LAYER (💾 Purple #f3e5f5):
- Technology: [Database system]
- Components: Data stores, processors, file systems
- Show data operations

**STYLING**:
- 4px stroke width for all layers
- Dashed arrows (-.->)  for internal layer connections
- Solid arrows (-->) for cross-layer connections
- Use emojis consistently

**VALIDATION**:
- Ensure no text overlaps
- Test that diagram renders vertically
- Verify all components are visible
```

### Phase 3: Sequence Diagram Creation

**Instruction to AI**:
```
Create a sequence diagram for the CORE user flow with these requirements:

**STRUCTURE**:
- Use `sequenceDiagram` with `autonumber`
- Define all system participants (User, Frontend, API, Services, Database, etc.)
- Use short, clear participant names (avoid multi-line names)

**FLOW DOCUMENTATION**:
1. Start with user action
2. Show request flow down through layers
3. Show processing at each layer
4. Show response flow back up
5. End with user-visible result

**LABEL GUIDELINES**:
- Keep arrow labels SHORT and readable
- Avoid multi-line labels (use single line or abbreviations)
- Use solid arrows (->>) for requests
- Use dashed arrows (--> or -->>)  for responses
- Add self-references (A->>A) for internal processing

**ANNOTATIONS**:
- Add `Note over` for major phase transitions
- Group related steps with comments (%%)
- Use activation boxes (+/-) to show lifetimes

**TEXT READABILITY**:
- NO line breaks (<br/>) in participant names
- Short labels: "POST /api/query" NOT "POST /api/query with session_id and message"
- Abbreviations: "Session Mgr" NOT "Session Manager"
```

### Phase 4: HTML Documentation Creation

**Instruction to AI**:
```
Create an interactive HTML file with tabbed interface:

**STRUCTURE**:
1. Header with system title and description
2. Metadata bar with tech stack summary
3. Tab navigation (Architecture Overview | User Flow Sequence)
4. Tab content areas
5. Footer with credits

**TAB 1 - ARCHITECTURE OVERVIEW**:
Order:
1. Legend/Component Overview (FIRST - above diagram)
   - 4 sections matching the 4 layers
   - Color-coded borders
   - Technology details and key features
2. Architecture Diagram (SECOND - below overview)

**TAB 2 - USER FLOW SEQUENCE**:
Order:
1. Flow Breakdown (FIRST - above diagram)
   - Step-by-step explanation
   - Grouped by phases (e.g., 1-3: User Interaction, 4-6: API Processing)
   - Color-coded sections
2. Sequence Diagram (SECOND - below breakdown)

**STYLING REQUIREMENTS**:
- Responsive design (mobile-friendly)
- Smooth tab transitions (CSS)
- Professional color scheme
- Readable fonts (system font stack)
- Proper spacing and padding
- Border colors matching diagram layers

**JAVASCRIPT**:
- Include switchTab() function
- Handle active state for tabs and content
- No external dependencies (vanilla JS only)

**MERMAID INTEGRATION**:
- Use Mermaid CDN (v10+)
- Initialize on load
- Both diagrams embedded directly in HTML
```

---

## QUALITY CHECKLIST

Before considering the documentation complete, verify:

### Architecture Diagram
- [ ] All 4 layers visible and stacked vertically (not side-by-side)
- [ ] User node at the very top
- [ ] Database/Storage layer at the very bottom
- [ ] Internal components flow left-to-right within each layer
- [ ] No overlapping text or labels
- [ ] Color coding applied correctly
- [ ] All technology names are accurate

### Sequence Diagram
- [ ] All participant names are single-line (no <br/>)
- [ ] Arrow labels are concise and readable
- [ ] Steps are numbered sequentially
- [ ] Flow shows complete user journey
- [ ] No text overlaps with boxes or arrows
- [ ] Proper use of activation boxes

### HTML Documentation
- [ ] Tabs switch correctly when clicked
- [ ] Overview/legend appears ABOVE diagram in both tabs
- [ ] Diagrams render without errors
- [ ] All text is readable
- [ ] Responsive on different screen sizes
- [ ] Color scheme is consistent
- [ ] Footer credits are present

### Content Accuracy
- [ ] Technology stack matches actual codebase
- [ ] Architecture pattern correctly identified
- [ ] Component descriptions are accurate
- [ ] Sequence flow matches actual system behavior
- [ ] File paths and references are correct

---

## EXAMPLE USAGE

### For a React + Node.js App:
```
Based on the architecture diagram prompt guidelines, explore this React + Node.js codebase and create comprehensive documentation following the 4-layer approach: Frontend (React), API (Express), Business Logic (Services), Database (PostgreSQL).
```

### For a Python FastAPI App:
```
Using the architecture documentation template, analyze this FastAPI application and generate diagrams showing the layered architecture: Frontend (Static HTML), API (FastAPI), Processing (Business Logic), Storage (Database + Files).
```

### For a Full-Stack App:
```
Following the system documentation prompt, explore this full-stack application and create interactive documentation with architecture and sequence diagrams showing all layers from UI to database.
```

---

## COMMON PITFALLS TO AVOID

### ❌ DON'T:
1. Create diagrams before thoroughly exploring the codebase
2. Use generic placeholder text instead of actual technology names
3. Put overview/legend BELOW diagrams
4. Use multi-line participant names in sequence diagrams
5. Let diagram layers render side-by-side instead of vertically
6. Use complex multi-line arrow labels
7. Skip the metadata section in HTML
8. Forget to test tab switching functionality

### ✅ DO:
1. Explore codebase first using Task tool
2. Use actual framework/library names from package files
3. Place overview sections ABOVE diagrams
4. Keep all participant names single-line
5. Force vertical stacking with explicit Layer→Layer connections
6. Use concise, single-line arrow labels
7. Include comprehensive system metadata
8. Test all interactive features

---

## PROMPT VARIATIONS

### Quick Version (Faster, Less Detail):
```
Create architecture and sequence diagrams for this codebase following the 4-layer vertical approach. Include an HTML page with tabs for both diagrams.
```

### Comprehensive Version (More Detail):
```
Perform a thorough codebase analysis and create comprehensive system documentation including:
1. 4-layer architecture diagram (vertical stack)
2. Core user flow sequence diagram
3. Interactive HTML with tabbed interface
4. Component legends above each diagram
5. System metadata and tech stack summary

Follow the architecture-diagram-prompt-template.md guidelines strictly.
```

### Specific Use Case:
```
Document the [SPECIFIC FEATURE] flow in this system:
1. Create sequence diagram showing the complete user journey for [FEATURE]
2. Update architecture diagram to highlight components involved in [FEATURE]
3. Generate HTML documentation with both diagrams and detailed breakdown
```

---

## TIPS FOR BEST RESULTS

1. **Always start with codebase exploration** - Don't skip this step
2. **Use the Plan subagent** - It's better at thorough exploration
3. **Be specific about tech stack** - Generic diagrams are less useful
4. **Test diagram rendering** - Paste into https://mermaid.live/ to verify
5. **Prioritize readability** - Simple, clear diagrams > complex, cluttered ones
6. **Iterate on feedback** - If layers don't stack vertically, explicitly fix the flow
7. **Keep labels short** - Abbreviate when necessary for clarity
8. **Color consistency** - Match legend colors to diagram colors exactly

---

## FILE NAMING CONVENTIONS

For multiple projects, use consistent naming:
- `[project-name]-architecture.mermaid`
- `[project-name]-sequence.mermaid`
- `[project-name]-documentation.html`

Or keep generic for single-project documentation:
- `architecture-diagram.mermaid`
- `sequence-diagram.mermaid`
- `architecture-diagram.html`

---

## VERSION HISTORY

**v1.0** - 2025-11-09
- Initial template based on RAG Chatbot documentation session
- 4-layer vertical architecture approach
- Tabbed HTML interface with overview-first layout
- Comprehensive codebase exploration workflow

---

## LICENSE & CREDITS

This prompt template is based on the successful documentation session for the RAG Chatbot system (2025-11-09).

**Key Success Factors**:
- Thorough codebase exploration before diagram creation
- Strict 4-layer vertical stacking
- Overview sections positioned above diagrams
- Clean, readable text without overlaps
- Interactive tabbed interface for better UX

Feel free to adapt and customize for your specific projects and use cases.

**Generated with**: Claude Code + Mermaid.js
**Template Created**: 2025-11-09
