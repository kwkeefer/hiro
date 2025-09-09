# AI Assistant Instructions

This directory contains documentation specifically designed to help AI assistants (like Claude Code, GitHub Copilot, etc.) understand and work with this codebase effectively.

## Files in this Directory

- **`project-context.md`** - Overview of the project, its structure, and current state
- **`coding-standards.md`** - Code style guidelines and conventions to follow
- **`architecture-decisions.md`** - Index of architectural decisions (ADRs)
- **`adrs/`** - Individual ADR documents with detailed decisions
- **`claude-code-instructions.md`** - Specific instructions for working with Claude Code

## How to Use These Files

### For Developers
When working with AI assistants:
1. Point the assistant to relevant files in this directory
2. Reference these files when asking for help with the codebase
3. Keep these files updated as the project evolves

### For AI Assistants
When working on this project:
1. Start by reading `project-context.md` for an overview
2. Consult `coding-standards.md` before writing code
3. Check `architecture-decisions.md` for ADR index, then read specific ADRs in `adrs/`
4. Follow specific instructions in `claude-code-instructions.md`

## Maintaining These Documents

### When to Update
- **Project Context**: When adding major features or changing structure
- **Coding Standards**: When adopting new conventions or tools
- **Architecture Decisions**: When making significant design choices
- **Claude Code Instructions**: When discovering useful patterns or gotchas

### Update Checklist
- [ ] Is the information still accurate?
- [ ] Are code examples up to date?
- [ ] Do file paths still exist?
- [ ] Are commands still valid?
- [ ] Is the project state current?

## Best Practices

1. **Keep it Current**: Outdated documentation is worse than no documentation
2. **Be Specific**: Include exact file paths and command examples
3. **Show Patterns**: Include code snippets that demonstrate conventions
4. **Explain Why**: Document not just what, but why decisions were made
5. **Stay Concise**: AI assistants work better with focused, clear instructions

## Example Usage with Claude Code

```bash
# When starting a session
"Please read the files in .ai/ directory to understand this project"

# When implementing a feature
"Following the patterns in .ai/coding-standards.md, implement..."

# When making architectural changes
"Create a new ADR in .ai/adrs/ and update the index in architecture-decisions.md"
```

## Contributing

When contributing to this project:
1. Review these AI instruction files
2. Update them if you make significant changes
3. Test that AI assistants can still understand the instructions
4. Add project-specific notes as you discover them

---

*These files are living documents. Update them as the project evolves to maintain their usefulness for AI-assisted development.*
