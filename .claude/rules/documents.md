---
paths:
  - "**/*.md"
  - "**/docs/*"
---

# Documentation Rules

- Follow the Google documentation style guide, especially capitalization:
  https://google.github.io/styleguide/docguide/style.html#capitalization
- Japanese, plain (常体) form. Exclude speculative and subjective expressions; state only facts, specs, and procedures
- Write complete procedures a third party can follow alone; do not omit assumed prerequisites
- Spell out abbreviations in full on first use; state target versions for version-dependent content
- No emojis; limit emphasis (bold, italic, etc.) to important parts
- Do not skip heading levels; no blank line directly under a heading
- For commands, state the working directory and required environment variables, and use code blocks with a language tag
- Use numbered lists when order matters
- Use concrete values (e.g. "an integer from 0 to 100" instead of "an appropriate value")
- For troubleshooting, pair an example error message with its cause and its fix