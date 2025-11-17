# Understanding Claude Code Configuration Files

## **1. CLAUDE.md** 
- **What is it:** This is your project's main file
- **When is it created:** When you run the `/init` command
- **Who can see it:** You commit this file to Git, so your **entire team** can see it
- **Where is it located:** In your project folder
- **Example:** If you're working with a team, everyone will have access to this file

---

## **2. CLAUDE.local.md** 
- **What is it:** This is your **personal file**
- **Who can see it:** Only **you** - no other engineers
- **What's it for:** You write your personal instructions and customizations for Claude here
- **Where is it located:** In your project folder
- **Example:** If you want Claude to work in a specific way just for you

---

## **3. ~/.claude/CLAUDE.md** 
- **What is it:** This is your **global settings** file
- **Where does it work:** In **every project** on your machine
- **What's it for:** Contains instructions you want Claude to follow in **all projects**
- **Where is it located:** Inside the `.claude` folder in your home directory (~)
- **Example:** If you want Claude to always write code in the same style, in every project

---

**In simple words:**
- **CLAUDE.md** = For the team
- **CLAUDE.local.md** = Just for you (in that project)
- **~/.claude/CLAUDE.md** = For all your projects


