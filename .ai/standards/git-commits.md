# Git Commit Standards

## Format
```
<type>: <subject>

<body>
```

## Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Formatting (no code change)
- `refactor`: Code restructuring
- `test`: Test changes
- `chore`: Build/tooling

## Examples
```
feat: add user authentication

fix: resolve database connection timeout

docs: update API endpoint documentation

refactor: extract validation into separate module
```

## Rules
- Subject line: 50 chars max, imperative mood
- Body: Wrap at 72 chars, explain why not what
- Reference issues: "Closes #123"
