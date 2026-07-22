# How Context Works in Claude Code

This is the core concept of Lesson 1. Before we touch any buttons, let's understand what Claude Code actually "sees" when it starts a session.

## The context hierarchy

When you open Claude Code in a project directory, it builds context from multiple sources — in this order:

```
1. System prompt        (built into Claude Code — you don't control this)
2. CLAUDE.md            (your project-level instructions — Claude reads this first)
3. Conversation history (everything you've said and Claude has replied)
4. Tool results         (file contents, command output, search results)
```

Everything Claude does in a session is shaped by this context. No magic — just text it can see.

## CLAUDE.md = your project's briefing document

Think of `CLAUDE.md` as the instructions you'd give a new teammate on day one. It is the broader understanding of the project:
- What are we building?
- What are the major rules?
- What should they NOT do?

Claude reads this file automatically at the start of **every session**. You don't need to paste it into chat.

**Key insight:** A good CLAUDE.md prevents 80% of the "Claude did something weird" moments. If you don't tell it the constraints, it'll invent its own.

## Task files = what to do right now

A task file (like `task.md`) is different from CLAUDE.md:
- **CLAUDE.md** = project-level rules that apply to every session
- **task.md** = a specific piece of work to do right now, this is limited to the session in hand

You reference the task file in your prompt:
```
Read task.md and do what it says
```

Claude will read the file, understand the steps, and work through them.

## Why this matters

Without context files:
- You end up repeating yourself every session
- Claude makes assumptions you didn't want
- You spend more time correcting than building

With context files:
- Claude starts every session already knowing the rules
- You can hand it a task and let it work
- Your instructions are version-controlled alongside your code
