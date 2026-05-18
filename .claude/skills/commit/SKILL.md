---
name: commit
description: Stage all modified tracked files and create a git commit with an appropriate message
disable-model-invocation: true
---

Stage all modified tracked files (do not include untracked files like .claude/, .playwright-mcp/, or image files unless they are clearly part of the project). Then review the diff and write a concise commit message that describes what changed and why. Format the commit message as a short summary line followed by a bullet list of key changes if needed.

Always co-author the commit:
Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

Use a HEREDOC to pass the commit message to avoid formatting issues.
