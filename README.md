# OrgHumans ☤

> **The AI Desktop Agent & Collaboration Platform for Teams & Organisations**

OrgHumans is an autonomous AI desktop agent built with a **Liquid Glass UI**, **Composio 1-Click Third-Party Integrations** (Gmail, Google Calendar, Reddit, Slack, GitHub, Linear, Jira, Notion, and 250+ others), **Profile & Workspace Isolation**, and **Composio Role-Based Access Control (RBAC)**.

---

## ✨ Core Features

<table>
<tr><td><b>Liquid Glass Desktop Interface</b></td><td>Sleek dark-mode desktop UI (`#0a0a0a` void base, `#7c6bff` violet accent, Inter font) built on Electron + React with smooth micro-animations.</td></tr>
<tr><td><b>Composio 1-Click Integrations</b></td><td>Connect personal and work accounts (Gmail, Google Calendar, Google Drive, Reddit, Slack, Discord, GitHub, Linear, Jira, Notion) in 1 click via Composio OAuth.</td></tr>
<tr><td><b>Organisation & Profile Isolation</b></td><td>Separate personal and team profiles. Each workspace maintains its own isolated context, memory, skills, and encrypted environment credentials.</td></tr>
<tr><td><b>Granular Member RBAC</b></td><td>Organisation owners can assign `can_read` and `can_write` permissions per integration to team members. The agent automatically enforces permissions before executing tools.</td></tr>
<tr><td><b>System Prompt Context Injection</b></td><td>Automatically appends organisation identity, brand voice, team handles, brand glossary, and GitHub repositories into system prompts with zero cross-profile leakage.</td></tr>
<tr><td><b>Local-First Peer Sync</b></td><td>HMAC-SHA256 authenticated, AES-256-GCM encrypted delta replication across peer nodes and team devices over WebSockets/TCP.</td></tr>
</table>

---

## 🚀 Quick Start

### 1. Run in Development Mode (Electron Desktop App)

```powershell
# Navigate to desktop app directory
cd apps/desktop

# Install dependencies and launch dev server
npm install
npm run dev
```

### 2. Run the CLI Engine

```powershell
python cli.py
```

### 3. Build Production Windows Executable (`.exe`)

```powershell
cd apps/desktop
npm run dist:win
```

The standalone installer will be built inside `apps/desktop/dist/OrgHumans Setup 0.17.0.exe`.

---

## 🔑 Composio Integration Setup

OrgHumans comes pre-configured with a master developer Composio key (`ak_...`) for zero-friction end-user onboarding.

1. Open **OrgHumans Desktop**.
2. Click the **Integrations** icon (plug icon in top-left sidebar).
3. Tap **Connect →** next to **Gmail**, **Google Calendar**, **Reddit**, **Slack**, or **GitHub**.
4. Complete standard 1-click OAuth in your browser.
5. Your agent is instantly empowered to manage emails, events, posts, and repositories!

---

## 🏢 Organisation & Team Collaboration

- **Create Organisation**: Click `+` on the sidebar → **+ Create Organisation** → Name your org & copy the invite key (`XXXX-XXXX-XXXX`).
- **Join Organisation**: Click `+` on the sidebar → **+ Join Organisation** → Paste invite key.
- **Team Permissions**: Manage member access (`@username`) per connected integration under Team & RBAC Settings.

---

## 🛡️ Privacy & Encryption

All OAuth tokens and API keys stored on disk by OrgHumans are encrypted at rest with AES-256-GCM. Workspace databases (`identity.db`, `members.db`, `integrations.db`) reside locally on your machine (`~/.orghumans/`).

---

## 📄 License

OrgHumans is distributed under the MIT License.
