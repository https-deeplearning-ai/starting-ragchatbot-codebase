---
name: log
description: Logs the most recent explanation or answer from the conversation into notes.md
disable-model-invocation: true
---

Look at the most recent explanation or answer you gave in this conversation. Extract the topic and key points, then append a new entry to `notes.md` in the repo root using this format:

## <topic title>
<concise explanation of what was discovered, in plain language>

If `notes.md` does not exist, create it with a `# Notes` heading first. Do not overwrite or modify any existing entries.
