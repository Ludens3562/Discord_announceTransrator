---
paths:
  - "**/*.py"
---

# Python Rules

- Type hints required: on all function arguments, return values, and class attributes
- Docstrings in Japanese, Google style. Add local variable type hints when:
  - the type is not obvious
  - the return type is a compound type such as Union or Optional
- Use the standard `logging` module; messages in Japanese; debug output at DEBUG level
- Specify the exception type in `except` (no bare `except`); define custom exceptions when needed
- Group imports as standard library / third-party / local modules, with a group-name comment at the top of each group and no blank lines between groups
- Name configurable constants in UPPER_SNAKE_CASE
- When using a global variable, add the `global` keyword and a comment explaining why