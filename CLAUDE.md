## Code
- Write comments, error messages, and logs in Japanese
- Convert any English comments found to Japanese
- Name identifiers (variables, functions, classes) with full English words; no abbreviations
  - Good: cart, quantity / Bad: ct, qty — fix on sight
- Keep debug/temporary code out of production logic
- Handle expected errors; log enough detail to diagnose issues

## Environment
- Run Python in a container (no venv)

## Prohibited destructive actions
Never perform, propose, or implicitly include the following without explicit user approval. They are not needed unless instructed and require no confirmation otherwise; get explicit approval only when actually needed.
- Any Python environment change (install/uninstall packages, edit env vars, create/delete virtualenvs)
- Any operation on files or directories outside the project directory

## Execution
- After receiving a task, do not ask formulaic confirmations ("may I run X?")
- Ask questions only when the spec is ambiguous, multiple implementations are viable, there is a conflict with existing code, or an unexpected impact scope is found — and only if it blocks implementation

## Reporting
- State facts only, concisely
- Do not give evaluations, next steps, or suggestions unless instructed

## Rule precedence on conflict
Apply in this order:
1. Prohibited destructive actions
2. Data protection constraints
3. Explicit user instructions
4. Efficiency and convenience

If a user instruction conflicts with these rules, state the conflict and the specific rule involved, and do not proceed until confirmed.
