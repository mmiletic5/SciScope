# SciScope development setup (Part 1)

The preferred Codex coding model is `gpt-6-luna`. The repository sets this as a
default in `.codex/config.toml`; Codex reads project configuration only after the
project is trusted. Confirm the active model in the Codex model picker or session
status. If another model is active, select GPT-6 Luna in the available model control
or start the CLI with `codex --model gpt-6-luna`. A local default does not change an
already running session. This coding model is separate from SciScope's AI provider.

Install Python 3.12, Git, Node.js, uv, Docker, Codex, and the official GitHub Spec Kit
CLI as needed. Spec Kit 1.4.0 was used to initialize this repository with the
`codex` integration and PowerShell scripts. Its commands run as Codex skills:
`$speckit-constitution`, `$speckit-specify`, `$speckit-plan`,
`$speckit-tasks`, and `$speckit-implement`. Invoke `$solution-research`
before feature specifications and feature tests. Invoke
`$google-python-engineering` whenever working with Python. Read the constitution
and get approval of the specification and plan before feature implementation.

Create a local configuration in PowerShell:

```powershell
Copy-Item .env.example .env
git check-ignore -v .env
```

The default `AI_PROVIDER=fake` needs no key. Never place credentials in the
committed example, logs, evidence, or screenshots. A live provider requires explicit
selection and a valid key; selecting one without a valid key must fail safely.
Development tests must prohibit paid external AI calls. Provider behavior is a
requirement for later implementation and is not implemented in Part 1.

The dependency installation and lockfile strategy, and application checks, will be
finalized in Part 3. `docs/DEVELOPMENT_WORKFLOW.md`, `EVIDENCE.md`, and
`PROJECT_TODO.md` are planned for later bootstrap parts.
