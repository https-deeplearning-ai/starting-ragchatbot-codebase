---
name: wrap
description: Log a session summary to memory at the end of a working session
disable-model-invocation: true
---

Run `date` to get the current date and time. Then review the conversation and write a session summary to:

`C:\Users\lcplu\.claude\projects\C--Users-lcplu-OneDrive-Documents-ClaudeCodeLearning\memory\project_session_progress.md`

Overwrite the entire file with the following format:

```
---
name: Session Progress & Next Steps
description: What was done in the latest session and what to pick up next
type: project
---

## Session — <date and time from the date command>

### Accomplished
- <bullet list of what was done this session>

### Where We Left Off
- <what we were doing at the end of the session>

### Next Steps
- <planned follow-ups or things to explore next>
```

Be specific and concise. This file is automatically loaded by Claude at the start of the next session.
