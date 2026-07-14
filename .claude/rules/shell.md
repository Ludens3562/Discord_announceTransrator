---
paths:
  - "**/*.sh"
  - "**/*.bash"
---

# Shell Script Rules

## Basics
- Declare `set -euo pipefail` at the top
- Comply with shellcheck and shfmt; resolve all warnings
- Write comments and user-facing output (info, error messages, etc.) in Japanese

## Naming
- Name variables and functions in lower snake_case
- Name environment variables and constants in UPPER_SNAKE_CASE
- Name identifiers in English; no abbreviations

## Variables and expansion
- Always quote variable references with braces: `"${variable_name}"`
- Use `$(...)` for command substitution, not backticks
- Use `[[ ]]` and arithmetic evaluation for numeric comparisons; avoid `[ ]`
- Avoid unset references; use `"${variable_name:-default}"` when a default is needed

## Functions and structure
- Split logic into functions and call them from a `main` function
- Run `main "$@"` at the end of the script
- When using a global variable, add a comment explaining why
- Define magic numbers and magic strings as constants at the top of the script

## Error handling
- Detect external command failures; send error messages to stderr
- Clean up temporary files and resources reliably with `trap`
- Set exit codes intentionally (0 on success, non-zero on failure)

## Prohibited
- Do not use `eval`
- Do not use unquoted command substitution
- Do not swallow pipe failures (rely on `pipefail` to detect them)