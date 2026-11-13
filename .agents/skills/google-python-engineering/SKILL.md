---
name: google-python-engineering
description: Apply SciScope Python style, typing, documentation, test-first, and quality checks whenever creating, changing, testing, or reviewing Python code.
---

# Google Python engineering

Use this skill for every SciScope Python change or review. It supplements Spec Kit's
specification and implementation skills; it does not grant implementation approval.
Read the approved spec and plan before implementation. Invoke `$solution-research` before
new feature tests, then write pytest behavior tests first and observe a meaningful failure.

Follow the [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html).
Use four spaces, descriptive `snake_case` functions and variables, `PascalCase` classes,
and `UPPER_CASE` constants. Annotate public interfaces and nontrivial internals. Use
Google-style docstrings for public or non-obvious functions and classes. Include `Args`,
`Returns`, and `Raises` when they clarify the interface; do not add empty sections.

Keep each function focused and modules maintainable. Organize imports, handle expected
exceptions explicitly, avoid duplicated business logic, and add dependencies only when
justified. Write all code, comments, identifiers, and docstrings in English. Respect
existing shared contracts and owner decisions.

Example:

```python
def normalize_title(title: str) -> str:
    """Normalize whitespace in a research title.

    Args:
        title: Source title to normalize.

    Returns:
        A title with surrounding and repeated whitespace removed.
    """
    return " ".join(title.split())
```

Run `ruff check .`, `ruff format --check .`, `pytest`, and `mypy .` when those tools and
relevant code are available. Use the repository's `pyproject.toml` settings. Report
unavailable, failed, or skipped checks accurately; human verification is a separate gate.
