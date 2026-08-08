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

The real Imperavis-specific work is focused on making Hermes easier to use for non-technical users and teams:

### 1. One-click Composio integrations

Imperavis adds a simpler account-connection flow for users who do not know what MCP, API keys, or tool configuration are.

Instead of asking the user to manually configure Composio or paste keys locally, Imperavis adds a backend-backed integration flow where users can connect apps from the desktop UI and have the agent tools become available automatically.

This includes the custom Composio proxy/MCP wiring used for personal-account integrations such as Gmail, Google apps, Reddit, LinkedIn, GitHub, and other supported apps.

### 2. Organization-based profile sync

Hermes already had profiles, but Imperavis extends the idea toward an organization workflow.

With Imperavis, a user can create or join an organization and share an organization code. People inside the same organization can stay synced through the shared organization setup, instead of every person manually configuring their own isolated agent environment.

The goal is to make the agent usable for non-technical clients and teams: one organization setup, shared code, synced members.

### 3. Desktop integrations UI

Imperavis updates the desktop integrations experience so account connections feel like normal app connections instead of developer configuration.

This includes a cleaner integrations catalog, OAuth-style connection states, and disconnect handling through the desktop app.

### 4. Desktop stability fixes

Imperavis includes desktop-side reliability fixes for packaged app usage, including safer backend process cleanup and watchdog behavior so the local backend does not get orphaned when the desktop app is killed.

### 5. Light personal rebranding

Some visible naming, copy, and agent identity text were changed from the upstream Hermes/OrgHumans defaults toward Vedansh's personal-agent setup.

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

This fork follows the upstream Hermes Agent license where applicable. See this repository's license and upstream Hermes Agent for full details.
