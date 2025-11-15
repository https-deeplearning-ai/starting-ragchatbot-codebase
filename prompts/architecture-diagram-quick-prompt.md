# Quick Architecture Diagram Prompt

Copy and paste this prompt, then fill in the bracketed sections with your system details:

---

## PROMPT

```
Create a high-level system architecture diagram in Mermaid format (graph TB) with this 3-tier layout:

TOP LAYER (User + Frontend):
- Technology: [e.g., React + TypeScript]
- Pages: [list 4-6 main pages/routes]
- Components: [list main UI components]
- Validators: [validation libraries/formatters]

MIDDLE LAYER (Side-by-side):

API LAYER:
- Technology: [e.g., Supabase SDK, REST API, GraphQL]
- Main features: [type safety, auth, caching, etc.]
- Services: [edge functions, background jobs, webhooks]

SECURITY LAYER:
- Technology: [e.g., RLS, JWT, OAuth]
- Main policy: [e.g., auth.uid() = user_id]
- Enforcement: [database level, middleware, gateway]

BOTTOM LAYER (Database):
- Technology: [e.g., PostgreSQL, MongoDB]
- Core tables: [list main entities]
- Special tables: [staging, logs, cache]
- Constraints: [FK, CHECK, triggers]

REQUIREMENTS:
- Use 3-tier vertical stack (Top: Frontend, Middle: API + Security side-by-side, Bottom: Database)
- Color-coded subgraphs with 4px borders
- Emoji icons for each layer (🎨 Frontend, 🔌 API, 🔒 Security, 💾 Database)
- Colors: Frontend=blue, API=orange, Security=red, Database=purple
- All labels must be readable with no overlap
- Use line breaks (<br/>) for long text
- Solid arrows (-->) for main flow, dashed (-.->)  for internal connections
- Include connection labels (e.g., |validates|, |enforces|)
```

---

## MINIMAL EXAMPLE

Just fill in the blanks:

**System**: [Your system name]

**Frontend**: [Technology] - [Page1, Page2, Page3, Page4] + [Component types] + [Validators]

**API**: [Technology] - [Feature1, Feature2] + [Service1, Service2]

**Security**: [Technology] - [Main policy] - [Where enforced]

**Database**: [Technology] - [Table1, Table2, Table3, Table4] + [Special tables] + [Constraints]

---

## PASTE THIS DIRECTLY TO CLAUDE

```
Create a Mermaid architecture diagram (graph TB, 3-tier layout):

System: [FILL: System name]

FRONTEND (🎨 blue): [FILL: Tech] | Pages: [FILL] | Components: [FILL] | Validators: [FILL]

API (🔌 orange): [FILL: Tech] | Features: [FILL] | Services: [FILL]

SECURITY (🔒 red): [FILL: Tech] | Policy: [FILL] | Enforcement: [FILL]

DATABASE (💾 purple): [FILL: Tech] | Core: [FILL] | Special: [FILL] | Constraints: [FILL]

Layout: Top=Frontend, Middle=API+Security (side-by-side), Bottom=Database. 4px borders, readable labels, line breaks for long text.
```

---

## ONE-LINE PROMPT (Advanced)

For quick generation:

```
Create Mermaid TB architecture: Frontend([Tech]: [Pages], [Components], [Validators]) → API([Tech]: [Features]) + Security([Tech]: [Policy]) → Database([Tech]: [Tables], [Constraints]). 3 tiers, API+Security side-by-side, color-coded (F=blue,A=orange,S=red,D=purple), emoji icons, readable labels.
```

Fill in the bracketed parts and send to Claude.
