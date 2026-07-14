---
paths:
  - "**/tests/*.py"
---

# Test Rules

- Use pytest
- Always include abnormal-case (failure) tests
- One verification purpose per test function; test names in snake_case that describe the content
- Use pytest.mark.parametrize for multiple cases and pytest.raises for exception checks
- Mock external dependencies (files, network, DB); do not use real-time sleep
- Consolidate common setup into fixtures
- Verify logs with caplog and stdout with capsys
- Integrate with existing tests when possible