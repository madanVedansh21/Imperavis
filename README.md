# Imperavis

> A personal AI agent built by **Vedansh Madan** on top of [Nous Research's Hermes Agent](https://github.com/NousResearch/hermes-agent).

Imperavis is Vedansh's personal fork/customization of Hermes Agent. It keeps the Hermes agent runtime, desktop app, MCP/tooling system, skills, memory, provider support, and most of the core product exactly as Hermes provides it.

This README was updated by **Imperavis itself** — the personal agent running from this repository — to clearly separate Vedansh's custom additions from the upstream Hermes work.

## Upstream credit

Imperavis is **not a from-scratch agent framework**. Around 99% of the core capability comes from upstream Hermes Agent:

- Repository: https://github.com/NousResearch/hermes-agent
- Docs: https://hermes-agent.nousresearch.com/docs

All base agent behavior, tool execution, memory, skills, desktop/chat surfaces, MCP support, provider abstraction, and multi-platform architecture should be credited to Hermes Agent / Nous Research unless explicitly listed below as an Imperavis-specific customization.

## What Vedansh changed on top of Hermes

Based on the commit range `bfded63d24ad281dc67a190716638de389756870` through `fef9f132a9f1e5979c1fb1ec4f24afacf2546994`, the main Imperavis-specific changes are:

### 1. Personal Composio integration layer

- Reworked the desktop integrations flow around a backend-owned Composio setup instead of asking the local user to paste a Composio API key.
- Added a secure proxy/MCP flow pointing to Vedansh's integration backend.
- Added automatic MCP config injection so connected tools become available to the agent after setup.
- Added stable per-profile `entity_id` handling for user-specific Composio tool access.

### 2. Desktop integrations UI changes

- Replaced the old API-key modal flow with a simpler account connection UX.
- Added OAuth pending/confirmation states.
- Added restart-needed messaging after integrations are connected.
- Added disconnect handling through desktop IPC.
- Updated the integration catalog to focus on the apps Vedansh wanted, including Reddit and LinkedIn.

### 3. Composio tool fixes

- Removed a hardcoded Composio API key from the client-side/local code path.
- Fixed Reddit tool loading and Composio app compatibility issues.
- Added LinkedIn as a connected social integration option.
- Adjusted MCP loading so Composio tools can be injected from config/profile state.

### 4. Profile and path customization

- Added support for `ORGHUMANS_HOME` alongside `HERMES_HOME`.
- Adjusted desktop/profile path resolution for Vedansh's local setup.
- Updated config polling/loading behavior so the desktop app and CLI pick up generated MCP config.

### 5. Desktop stability fixes

- Added crash-resilient cleanup for orphaned backend processes using a PID file.
- Added a Python watchdog process to kill the backend when the Electron desktop process is hard-killed.
- Fixed packaged Electron path/preload resolution issues.
- Improved renderer loading fallback behavior for packaged desktop builds.

### 6. Light rebranding/personalization

- Changed some visible naming/copy from Hermes/OrgHumans toward Vedansh's personal-agent setup.
- Updated prompt identity text for the customized agent.
- Removed/rewrote parts of the previous README that over-claimed unrelated product features.

## What remains Hermes

Everything not listed above should be treated as upstream Hermes Agent functionality, including but not limited to:

- Core agent loop and tool calling
- Skills and memory system
- MCP server support
- Desktop app foundation
- CLI and session handling
- Provider/model support
- Background tasks, cron, delegation, and general automation architecture
- Most UI surfaces and agent infrastructure

## Author

Built/customized by **Vedansh Madan** for his personal workflow.

- GitHub: https://github.com/madanVedansh21
- LinkedIn: https://www.linkedin.com/in/vedansh-madan-100a49312

## License

This fork follows the upstream Hermes Agent license where applicable. See the repository license and upstream Hermes Agent for full details.
