# OrgHumans — Full Product Requirements Document

**Version:** 0.2 · **Status:** Draft · **Author:** ved.dev  
**Base:** Fork of NousResearch/hermes-agent (MIT License)

---

## 1. What This Is

A fork of the Hermes desktop agent app. We are making internal changes to Hermes to add:

1. A **profile system** — personal profile and one or more org profiles, each fully isolated via separate `HERMES_HOME` directories
2. An **organisation layer** — create an org, get an invite key, others join with that key
3. **Composio integration per profile** — personal integrations tied to the person, org integrations tied to the org and controlled by the owner
4. **Role-based access control (RBAC)** — owner manages what each member can read or write on org-connected apps
5. A **team panel** — see who's in the org, manage members and their permissions

Everything else Hermes already does (agent memory, SKILL.md self-improvement, session history, skills, tools, model switching) stays exactly as is. We are adding layers on top and making wiring changes. We are not rebuilding the agent.

**We are building on top of the existing `apps/desktop` desktop app**, transforming its UI into our custom Liquid Glass design system, rebranding it to OrgHumans, and wiring in profile/org isolation, Composio integrations, and team features directly into `apps/desktop`.

---

## 2. What We Are NOT Building

- A new agent runtime (Hermes handles this)
- A cloud-hosted agent (everything runs locally)
- Forking any existing Hermes desktop UI (we build our own from scratch)
- Any LinkedIn or ToS-violating scraping features
- A mobile app

---

## 3. Core Concepts

### 3.1 Profile

A profile is one isolated context for the agent. Every profile gets its own `HERMES_HOME` directory on disk. Switching profiles = switching which `HERMES_HOME` is active = completely different agent memory, skills, integrations, and session history.

There are two types of profiles:

**Personal Profile**
- Created automatically when the user first opens the app
- Belongs only to that user
- Stores: personal memory, personal skills, personal session history, personal Composio integrations
- Never synced to anyone else
- The user connects their own accounts here (their Gmail, their Notion, their GitHub, etc.)

**Org Profile**
- Created when a user creates an org, or when a user joins an org via invite key
- One org profile per org the user belongs to
- Stores: org memory context (read from org DB), user's sessions within that org context, user's username for that org
- The org's shared integrations (Google Workspace, Slack, etc.) are connected once by the org owner and flow into every member's org profile with permissions applied

### 3.2 Organisation

An organisation is a shared entity that multiple users belong to. It has:
- A name
- A unique secret invite key (generated on creation)
- A shared identity database (brand info, products, etc.)
- A list of members with their usernames and roles
- A set of org-level integrations connected by the owner
- A permissions table mapping members to integration access levels

### 3.3 HERMES_HOME Isolation

```
~/.orghumans/
  profiles/
    personal/                        ← Personal profile HERMES_HOME
      MEMORY.md
      USER.md
      SOUL.md
      skills/
      state.db
      .env                           ← personal API keys + Composio tokens

    org-{org_id}/                    ← One per org the user has joined
      MEMORY.md                      ← agent memory within org context
      USER.md
      SOUL.md
      skills/
      state.db
      .env                           ← org Composio tokens injected here (read/write per permissions)

  orgs/
    {org_id}/
      meta.json                      ← org name, invite key hash, created_at
      identity.db                    ← brand context, products, tone, glossary
      members.db                     ← usernames, roles, joined_at
      integrations.db                ← org Composio connections + per-member permissions
      sync_log.db                    ← what changed and when (for thin cloud sync)
```

---

## 4. Feature List — Every Feature, Every Detail

### 4.1 First Launch & Onboarding

#### 4.1.1 Welcome Screen
- [ ] On first launch, show a welcome screen
- [ ] Welcome screen has two options: **"Set up my personal workspace"** and **"Join an organisation"**
- [ ] User can do both — the welcome screen is not a forced either/or. Both options can be selected before proceeding
- [ ] A "Skip for now" option exists — user can proceed with an empty state and set things up later from settings

#### 4.1.2 Personal Profile Setup
- [ ] Ask the user for a display name (used locally, not synced anywhere)
- [ ] Ask the user which LLM provider they want to use (same options Hermes already supports — Anthropic, OpenRouter, OpenAI, etc.)
- [ ] Ask the user to enter the API key for their chosen provider
- [ ] API key is stored encrypted in the personal profile `.env` file
- [ ] Personal `HERMES_HOME` is created at `~/.orghumans/profiles/personal/`
- [ ] Hermes is booted with this `HERMES_HOME` — all Hermes defaults apply from here
- [ ] Show a confirmation screen: "Your personal workspace is ready"

#### 4.1.3 Join Organisation Flow (from welcome or later)
- [ ] Show an input field: "Enter your organisation invite key"
- [ ] Validate the invite key format (it will be a UUID or short alphanumeric string)
- [ ] If valid key: fetch org metadata from the thin cloud sync server (org name, description)
- [ ] Show org preview: org name, member count, created date
- [ ] Ask the user to pick a username for this org (this is how they appear to teammates)
- [ ] Username rules: 3–20 characters, alphanumeric + underscores, must be unique within the org
- [ ] Check username availability against the org's members list via sync server
- [ ] If username taken: show error, let user pick another
- [ ] On confirm: register user in the org's `members.db` with role `member`
- [ ] Create org profile directory at `~/.orghumans/profiles/org-{org_id}/`
- [ ] Pull org identity data (`identity.db`) from sync server and store locally
- [ ] Pull org integrations metadata (not raw tokens) — what integrations exist and what permissions this member has
- [ ] Inject permitted org integration tokens into the org profile `.env`
- [ ] Boot Hermes with org `HERMES_HOME` to verify it works
- [ ] Show confirmation: "You've joined {org name} as @{username}"

---

### 4.2 Profile Switcher

#### 4.2.1 Switcher UI
- [ ] A persistent profile switcher is visible in the top-left of the app at all times
- [ ] Shows current active profile name and type (Personal or org name)
- [ ] Clicking it opens a dropdown listing all available profiles:
  - Personal (always first)
  - Each org the user has joined (listed by org name)
  - A "+ Create Organisation" option at the bottom
  - A "+ Join Organisation" option at the bottom
- [ ] Active profile is visually highlighted (bold, checkmark, or accent color)

#### 4.2.2 Switching Profiles
- [ ] Clicking a profile in the dropdown switches to it
- [ ] On switch: current Hermes session is suspended (state saved to current profile's `state.db`)
- [ ] `HERMES_HOME` environment variable is updated to the new profile's directory
- [ ] Hermes is re-initialised with the new `HERMES_HOME`
- [ ] New profile's memory, skills, integrations all load automatically
- [ ] If switching to an org profile: org identity context is injected into agent's system prompt
- [ ] UI updates to reflect the new profile (profile name, available integrations, team panel visibility)
- [ ] Switch completes in under 2 seconds on a normal machine
- [ ] No data from the previous profile leaks into the new profile's context

#### 4.2.3 Profile Indicators
- [ ] Personal profile has a distinct icon (person icon)
- [ ] Org profiles have the org's initials or logo as icon
- [ ] If the user has unread activity in a non-active profile (e.g., an org sync update), show a notification dot on that profile in the switcher

---

### 4.3 Organisation Creation

#### 4.3.1 Create Org Flow
- [ ] Accessible from: welcome screen, profile switcher dropdown, settings
- [ ] Step 1 — Org basics:
  - [ ] Org name (required, 2–50 characters)
  - [ ] Org description (optional, up to 200 characters)
  - [ ] Org type selector: Company / Startup / Freelance Team / Personal Project / Other
- [ ] Step 2 — Brand identity (all optional, can be filled later):
  - [ ] What does your brand do? (text area, up to 500 characters)
  - [ ] Brand tone: dropdown — Professional / Casual / Technical / Friendly / Formal
  - [ ] Products or services offered (multi-line text, one per line)
  - [ ] Target audience description (text area)
  - [ ] Brand glossary: key terms and what they mean (add rows dynamically)
- [ ] Step 3 — GitHub connection (optional):
  - [ ] Connect org's GitHub account via OAuth
  - [ ] Select which repos to mark as org context (multi-select)
  - [ ] Selected repos will be available as context for all members' agents
- [ ] Step 4 — Review and confirm:
  - [ ] Show summary of everything entered
  - [ ] "Create Organisation" button
- [ ] On creation:
  - [ ] Generate a unique org ID (UUID)
  - [ ] Generate a secret invite key (alphanumeric, 12 characters, e.g. `AX7K-9MNP-Q2RT`)
  - [ ] Create org record on thin cloud sync server
  - [ ] Create local org directory at `~/.orghumans/orgs/{org_id}/`
  - [ ] Write `meta.json`, `identity.db`, `members.db`, `integrations.db` locally
  - [ ] Register creator as first member with role `owner`
  - [ ] Creator picks their own username for this org
  - [ ] Create org profile at `~/.orghumans/profiles/org-{org_id}/`
  - [ ] Boot Hermes with org profile to verify
  - [ ] Show confirmation screen with the invite key displayed prominently

#### 4.3.2 Invite Key Display
- [ ] Invite key shown in large, readable format: `AX7K-9MNP-Q2RT`
- [ ] "Copy to clipboard" button next to the key
- [ ] Warning text: "Keep this key safe. Anyone with this key can join your organisation."
- [ ] Option to regenerate the invite key (invalidates the old one, existing members are unaffected)
- [ ] Invite key also accessible later from: Org Settings → Invite Key

---

### 4.4 Personal Integrations (Personal Profile)

#### 4.4.1 Integrations Panel — Personal
- [ ] Accessible only when the personal profile is active
- [ ] Shows a list of all available Composio integrations (118+ providers)
- [ ] Searchable by name (e.g. type "Gmail" to filter)
- [ ] Each integration shows: provider logo, provider name, connection status (Connected / Not connected)
- [ ] "Connect" button on each unconnected integration
- [ ] "Disconnect" button on each connected integration (with confirmation dialog)
- [ ] "Re-authenticate" button if a token has expired

#### 4.4.2 Connecting a Personal Integration
- [ ] User clicks "Connect" on a provider
- [ ] Composio OAuth flow opens in a browser window (or in-app webview)
- [ ] User authenticates with their own account for that provider
- [ ] On success: OAuth token is stored encrypted in personal profile `.env`
- [ ] Integration status updates to "Connected" in the UI
- [ ] Agent is notified that this integration is now available (Hermes picks it up on next session via `.env`)
- [ ] No one else — not org members, not org owner — can see or access this token

#### 4.4.3 Personal Integration Permissions
- [ ] Each connected personal integration has a settings panel:
  - [ ] Read access toggle (default: on)
  - [ ] Write access toggle (default: on, user can restrict their own agent)
  - [ ] This controls what the agent is allowed to do with this integration
- [ ] These are the user's own settings — not controlled by anyone else

---

### 4.5 Org Integrations (Org Profile — Owner Only to Connect)

#### 4.5.1 Integrations Panel — Org (Owner view)
- [ ] Accessible only when an org profile is active
- [ ] Owner sees the full integrations panel with "Connect" buttons
- [ ] Non-owner members see the panel but "Connect" buttons are disabled with a tooltip: "Only the organisation owner can connect apps"
- [ ] Shows all available Composio integrations, searchable
- [ ] Each integration shows: logo, name, connection status, and a "Permissions" button if connected

#### 4.5.2 Owner Connecting an Org Integration
- [ ] Owner clicks "Connect" on a provider
- [ ] Composio OAuth flow opens — owner authenticates with the **company's** account (e.g. company Google Workspace, company Slack workspace)
- [ ] On success: token stored encrypted in `integrations.db` under the org directory
- [ ] Integration status updates to "Connected (Org)"
- [ ] Default permissions are applied automatically: all members get read access, no one gets write access except the owner
- [ ] Sync server is notified that a new integration exists for this org
- [ ] All member devices receive the update on next sync — their org profile `.env` is updated with a read-scoped version of the token

#### 4.5.3 Org Integration Permissions Management (Owner)
- [ ] Owner clicks "Permissions" on a connected org integration
- [ ] Opens a permissions panel showing a table:
  - Columns: Username | Role | Read Access | Write Access
  - Rows: one per org member
- [ ] Owner can toggle Read and Write access per member per integration
- [ ] Read access is on by default for all members
- [ ] Write access is off by default for all members (except owner, who always has full access)
- [ ] Owner can also set a permission at the role level: "All members get write access to this integration"
- [ ] Saving permissions triggers a sync to all affected member devices
- [ ] Members whose write access was just granted: their org profile `.env` is updated with a write-scoped token
- [ ] Members whose access was revoked: their token for that integration is removed from `.env` and Hermes context refreshes

#### 4.5.4 What Members See (Non-Owner)
- [ ] When on an org profile, members see which org integrations are connected
- [ ] They can see their own access level (Read / Read+Write / No Access) per integration
- [ ] They cannot see other members' access levels
- [ ] They cannot connect, disconnect, or modify any org integration
- [ ] If they try to perform a write action via the agent and they only have read access: agent returns a clear error "You don't have write permission for [integration name] in this org. Contact your org owner."

---

### 4.6 Team Panel

#### 4.6.1 Accessing the Team Panel
- [ ] Team panel is only visible when an org profile is active
- [ ] Accessible from the main navigation sidebar (e.g. "Team" tab)
- [ ] Not visible at all when personal profile is active

#### 4.6.2 Member List (All Members See This)
- [ ] Shows a list of all members who have joined the org
- [ ] Each member row shows:
  - [ ] Username (e.g. @alice)
  - [ ] Role badge (Owner or Member)
  - [ ] Joined date (e.g. "Joined 3 days ago")
  - [ ] Online/offline status indicator (based on last sync ping, not real-time)
- [ ] List is sorted: Owner first, then Members alphabetically by username
- [ ] Search bar to filter members by username
- [ ] Total member count shown at the top (e.g. "4 members")

#### 4.6.3 Member Management (Owner Only)
- [ ] Owner sees additional controls on each member row:
  - [ ] "Manage Permissions" button → opens the permissions panel for that member across all integrations
  - [ ] "Remove from org" button → removes the member (with confirmation dialog)
- [ ] Removing a member:
  - [ ] Their entry is deleted from `members.db`
  - [ ] Sync server is notified
  - [ ] On the removed member's device: their org profile is locked (they see a "You've been removed from this org" screen)
  - [ ] Their org integration tokens are revoked and removed from their local `.env`
  - [ ] Their personal profile is completely unaffected

#### 4.6.4 Owner Cannot Be Removed
- [ ] The owner row has no "Remove" button — owners cannot be removed by anyone
- [ ] If the owner wants to leave the org, they must transfer ownership first (v2 feature — flag this)

#### 4.6.5 Member's Own Profile in Team Panel
- [ ] Each member can see their own entry in the list highlighted
- [ ] They can edit their own username from here (subject to uniqueness check)
- [ ] Username change is synced to all other members

---

### 4.7 Org Identity & Brand Context

#### 4.7.1 Org Identity Panel
- [ ] Accessible from org profile → "Org Settings" or "Brand" tab
- [ ] Only the Owner can edit; Members see it read-only
- [ ] Fields:
  - [ ] Org name (editable by owner)
  - [ ] Org description
  - [ ] What the brand does
  - [ ] Brand tone
  - [ ] Products / services list
  - [ ] Target audience
  - [ ] Brand glossary (key → value pairs, add/remove rows)

#### 4.7.2 How Brand Context Flows Into the Agent
- [ ] When user activates an org profile, the identity data is read from `identity.db`
- [ ] It is formatted into a context string and injected into the Hermes system prompt as an additional context file
- [ ] The agent can reference brand context in responses (e.g. "Based on your brand tone, here's a draft...")
- [ ] If the owner updates identity data, all members get the update on next sync
- [ ] Updated context is loaded on the member's next profile activation or next session start

#### 4.7.3 GitHub Connection (Org Level)
- [ ] Owner can connect the org's GitHub account from Org Settings
- [ ] After connecting: a repo selector shows all repos in that GitHub org
- [ ] Owner selects which repos to include as org context (multi-select, with search)
- [ ] Selected repos are synced: README, open issues summary, recent commit messages are pulled and stored in `identity.db` as context snippets
- [ ] Repo context is included in the agent's system prompt alongside brand identity
- [ ] Owner can add or remove repos from the selection at any time
- [ ] Re-sync button to refresh repo context on demand
- [ ] Members cannot modify GitHub settings but their agents benefit from the repo context automatically

---

### 4.8 Invite Key Management

#### 4.8.1 Viewing the Invite Key
- [ ] Owner can view the current invite key from Org Settings → "Invite & Access"
- [ ] Key is shown partially masked by default (e.g. `AX7K-****-****`) with a "Reveal" button
- [ ] "Copy" button to copy the full key to clipboard

#### 4.8.2 Regenerating the Invite Key
- [ ] Owner sees a "Regenerate Key" button
- [ ] Clicking it shows a confirmation dialog: "Regenerating the key will invalidate the current one. People who haven't joined yet will need the new key. Existing members are not affected."
- [ ] On confirm: new key is generated, old key is invalidated on the sync server
- [ ] New key is displayed and can be copied

#### 4.8.3 Invalid Key Handling (Joiner Side)
- [ ] If a user enters an expired or incorrect invite key: show error "This invite key is invalid or has expired. Ask your org owner for the current key."
- [ ] Do not reveal whether an org exists or not — just say the key is invalid

---

### 4.9 Agent Behaviour Per Profile

#### 4.9.1 Personal Profile Agent
- [ ] Agent has access only to personal integrations connected by the user
- [ ] Agent's memory (`MEMORY.md`, `USER.md`, `state.db`) is personal and isolated
- [ ] Agent has no knowledge of any org the user belongs to
- [ ] Agent's skills are personal — built from the user's own past tasks
- [ ] Agent can use all Hermes tools: browser, terminal, file system, etc. (unchanged from base Hermes)

#### 4.9.2 Org Profile Agent
- [ ] Agent has access to org integrations with permissions applied (read-only or read+write depending on member's grants)
- [ ] Agent's memory is org-scoped — it remembers things done within the org context
- [ ] Agent's system prompt includes org identity context (brand, products, GitHub repos)
- [ ] Agent knows the user's username within the org
- [ ] Agent knows the list of other members and their usernames (for A2A request framing — v2 feature)
- [ ] Agent cannot access the user's personal integrations (no cross-profile leakage)
- [ ] Agent cannot access any other org's data

#### 4.9.3 Context Injection on Profile Activation
- [ ] When org profile is activated, the following is injected into Hermes system prompt:
  - [ ] Org name and description
  - [ ] Brand identity context (what the brand does, tone, products, audience)
  - [ ] Glossary terms
  - [ ] GitHub repo context snippets (if connected)
  - [ ] User's username and role within the org
  - [ ] List of org members (usernames only)
  - [ ] List of connected org integrations and the user's access level for each
- [ ] This injection happens via Hermes's existing `additional_context` mechanism in `prompt_builder.py`
- [ ] The injected context is read-only as far as the agent is concerned — the agent cannot modify org identity directly (it has no write tool for `identity.db`)

---

### 4.10 Thin Cloud Sync Layer

#### 4.10.1 What Gets Synced
- [ ] Org metadata (`meta.json`)
- [ ] Org identity (`identity.db` contents)
- [ ] Members list (`members.db` contents)
- [ ] Org integration metadata (what integrations exist and what permissions each member has — NOT raw tokens)
- [ ] Permission changes made by owner
- [ ] Member join/leave events
- [ ] Username changes

#### 4.10.2 What Does NOT Get Synced
- [ ] Personal profile data of any kind
- [ ] Personal integration tokens
- [ ] Personal agent memory
- [ ] Raw org integration OAuth tokens (these are re-issued locally per member's permission scope)
- [ ] Session history
- [ ] Agent skills

#### 4.10.3 Sync Mechanism
- [ ] Thin cloud sync server: lightweight WebSocket + REST server (Node.js or Go, minimal logic)
- [ ] Each device maintains a persistent WebSocket connection to the sync server when online
- [ ] On org data change (any of the items in 4.10.1): the changing device sends a diff to the sync server
- [ ] Sync server broadcasts the diff to all other connected devices in the same org
- [ ] Receiving device applies the diff to its local org DB
- [ ] If a device is offline when a change happens: on next connection, it pulls a full sync from the server
- [ ] Sync server does not permanently store org data — it holds the latest snapshot in memory and flushes to a minimal persistent store only for offline-member catch-up
- [ ] All data in transit is encrypted (TLS)

#### 4.10.4 Conflict Resolution
- [ ] Last-write-wins for org identity fields (simple enough for now)
- [ ] Member joins are append-only (no conflict possible)
- [ ] Permission changes: owner's write always wins
- [ ] If two owners exist (not possible in v1 — only one owner per org), this would need CRDTs. Defer to v2.

#### 4.10.5 Offline Behaviour
- [ ] App works fully offline for personal profile (no sync needed)
- [ ] App works fully offline for org profile for agent tasks (local data is sufficient)
- [ ] Org data may be stale if offline — a banner is shown: "You're offline. Org data was last synced at {timestamp}."
- [ ] Member join/leave and permission changes are queued and applied on reconnect

---

### 4.11 Settings

#### 4.11.1 Personal Settings
- [ ] Display name (editable)
- [ ] Default LLM provider and model
- [ ] API key management (add, rotate, remove keys per provider)
- [ ] Personal integrations (shortcut to integrations panel)
- [ ] Data & Privacy: option to wipe personal profile data entirely (with strong confirmation)

#### 4.11.2 Org Settings (Owner Only)
- [ ] Org name and description (editable)
- [ ] Brand identity panel (editable)
- [ ] GitHub connection (connect/disconnect/change repo selection)
- [ ] Invite key management (view, copy, regenerate)
- [ ] Org integrations panel (connect/disconnect/manage permissions)
- [ ] Danger zone:
  - [ ] Delete organisation (with multi-step confirmation: type org name to confirm)
  - [ ] Deleting org: removes org from sync server, notifies all members, locks their org profile

#### 4.11.3 Org Settings (Member — Read Only)
- [ ] Can see: org name, description, brand identity, connected integrations, their own permissions
- [ ] Cannot edit anything

#### 4.11.4 App-level Settings
- [ ] Theme: Light / Dark / System
- [ ] Startup behaviour: launch on system startup yes/no
- [ ] Sync server URL (advanced, for self-hosting the sync server)
- [ ] Check for Hermes updates button
- [ ] App version display

---

### 4.12 Hermes Internal Changes (Code-level)

These are the specific changes we make inside the forked Hermes repo.

#### 4.12.1 `hermes_constants.py`
- [ ] Add `get_profile_home(profile_id: str)` function that returns `~/.orghumans/profiles/{profile_id}/`
- [ ] Override `get_hermes_home()` to call `get_profile_home()` with the currently active profile ID
- [ ] Active profile ID is read from a global config file at `~/.orghumans/active_profile.json`
- [ ] All existing code that calls `get_hermes_home()` automatically works correctly with zero other changes

#### 4.12.2 `prompt_builder.py`
- [ ] Add a new context source: `org_context`
- [ ] If the active profile is an org profile: read `~/.orghumans/orgs/{org_id}/identity.db` and format as markdown string
- [ ] Inject this string as an additional context block in the system prompt, clearly labelled `## Organisation Context`
- [ ] If the active profile is a personal profile: `org_context` is empty string, nothing injected
- [ ] This change is additive — existing prompt assembly is untouched

#### 4.12.3 `.env` management
- [ ] Each profile's `.env` file is the source of truth for that profile's integrations
- [ ] Personal profile `.env`: populated by Composio OAuth flows triggered by the user
- [ ] Org profile `.env`: populated automatically based on which org integrations exist and what permissions this member has
- [ ] When profile is switched: Hermes re-reads the new profile's `.env` on boot
- [ ] When org permissions change (owner grants/revokes): the affected member's org profile `.env` is updated by the sync layer and Hermes is signalled to refresh its tool availability

#### 4.12.4 New Module: `orghumans/`
A new Python module added alongside the existing Hermes code:

```
orghumans/
  __init__.py
  profile_manager.py     ← create/switch/list profiles, manage active_profile.json
  org_manager.py         ← create org, join org, generate invite key, sync org data
  composio_rbac.py       ← wrap Composio OAuth with RBAC logic
  sync_client.py         ← WebSocket client for thin cloud sync
  context_builder.py     ← build org_context string from identity.db
  member_manager.py      ← add/remove members, update permissions, manage usernames
```

#### 4.12.5 Desktop App — Electron Shell (`/electron` folder)

We build our own Electron app from scratch. It lives in an `/electron` folder added directly inside the forked Hermes repo. It talks to the Hermes Python backend running locally as a subprocess.

**Stack:**
- [ ] Electron (latest stable) as the desktop shell
- [ ] React + TypeScript for the frontend
- [ ] Hermes Python process spawned as a child process on app launch, communicating via local HTTP (Hermes's existing `/v1/chat/completions` server)
- [ ] No dependency on any existing Hermes desktop UI code — built entirely from scratch

**Theme — Pure Liquid Glass:**
- [ ] The entire UI uses a pure dark liquid glass aesthetic — dark base with glass surfaces layered on top
- [ ] Base background: very deep dark (near black, e.g. `#080808` to `#0d0d0d`) — not grey, not navy, pure dark
- [ ] Glass panels: semi-transparent dark surfaces with real blur (`backdrop-filter: blur(20px+)`), subtle light refraction on edges, soft inner glow
- [ ] Every card, modal, sidebar, panel, and input is a glass surface — nothing is flat or opaque
- [ ] Light diffusion: soft caustic-style light spill on glass edges — always rendered against the dark base, no light mode
- [ ] Typography: clean, light-weight sans-serif — white or near-white text throughout, high contrast against dark glass
- [ ] Accent color: a single cool iridescent tone (blue-violet spectrum) used sparingly for active states and highlights
- [ ] Animations: all transitions are fluid — panels slide and blur in, modals bloom open, no hard cuts
- [ ] No borders in the traditional sense — separation is achieved through depth and blur layers only
- [ ] Scrollbars: hidden by default, thin glass-style on hover
- [ ] Icons: line-style, thin weight, monochrome to match the glass theme

**Screens to build:**
- [ ] Welcome / onboarding screen (first launch only)
- [ ] Profile switcher component (persistent, top-left of sidebar)
- [ ] Create org wizard (multi-step, each step is a glass panel)
- [ ] Join org screen (invite key input + username picker)
- [ ] Main chat interface (agent conversation, per active profile)
- [ ] Integrations panel — personal view
- [ ] Integrations panel — org view (with permissions table)
- [ ] Team panel (member list, roles, online status)
- [ ] Permissions management modal (owner only)
- [ ] Org settings panel (brand identity, GitHub, invite key)
- [ ] Personal settings panel (API keys, display name, LLM provider)
- [ ] App-level settings (theme, startup, sync server URL)
- [ ] Offline banner component (shown when sync server unreachable)

---

### 4.13 Security Requirements

- [ ] All OAuth tokens stored AES-256 encrypted at rest in `.env` files
- [ ] Encryption key derived from the user's device ID + a local passphrase set at first launch
- [ ] Invite keys are hashed before storage on the sync server (server never stores the plaintext key)
- [ ] When a member is removed: their org integration tokens are immediately revoked on their device via a sync push
- [ ] No personal data ever leaves the device
- [ ] Org data in transit is encrypted via TLS (HTTPS/WSS only)
- [ ] Sync server is stateless as much as possible — minimal data held server-side
- [ ] Org profile cannot access personal profile's `.env` or `state.db` (enforced by directory isolation)
- [ ] Agent in org profile cannot execute file system operations outside its own `HERMES_HOME` (sandboxing — check Hermes's existing sandboxing hooks)

---

### 4.14 Error States & Edge Cases

- [ ] User enters wrong invite key → "Invalid or expired invite key"
- [ ] Username already taken in org → "This username is taken in this org. Please choose another."
- [ ] Org owner disconnects an integration while a member's agent is mid-task using it → agent receives a tool error, returns graceful message to user
- [ ] Sync server unreachable → app works offline, shows sync status banner
- [ ] User's API key for LLM expires → agent returns error, user is prompted to update the key in settings
- [ ] User tries to perform write action on org integration without write permission → agent returns clear permission error
- [ ] User tries to join an org they're already in → "You're already a member of this organisation"
- [ ] Org is deleted while members are active → members see "This organisation has been dissolved by the owner" on their org profile
- [ ] Two devices of the same user (e.g. laptop + desktop) → each device has its own local state, both are members in the org's `members.db` as the same username. Sync keeps org data in sync but personal data remains per-device. (Multi-device personal sync is a v2 feature.)

---

## 5. Build Order

### Phase 1 — Profile Isolation (Week 1–2)
Goal: personal profile working with isolated HERMES_HOME

- [ ] Fork hermes-agent repo ✅ (already done)
- [ ] Implement `get_profile_home()` in `hermes_constants.py`
- [ ] Implement `active_profile.json` switching logic
- [ ] Create `profile_manager.py`
- [ ] Test: two profiles on same machine, completely isolated memory and sessions
- [ ] Basic profile switcher UI (dropdown, no org features yet)

### Phase 2 — Personal Integrations (Week 3–4)
Goal: user can connect personal Composio integrations per profile

- [ ] Composio OAuth flow wired into personal profile `.env`
- [ ] Integrations panel UI (personal view)
- [ ] Connect / disconnect / re-authenticate flows
- [ ] Agent picks up integrations from `.env` on session start
- [ ] Test: connect Gmail on personal profile, agent can read emails

### Phase 3 — Org Creation & Join (Week 5–6)
Goal: user can create an org and another user can join it

- [ ] `org_manager.py` — create org, generate invite key, write local files
- [ ] Sync server setup (minimal — just store org metadata and member list)
- [ ] `sync_client.py` — connect to sync server, push/pull org data
- [ ] Create org wizard UI
- [ ] Join org flow UI (invite key input + username picker)
- [ ] Org profile directory created on join
- [ ] Profile switcher updated to show org profiles

### Phase 4 — Org Context & Agent Wiring (Week 7–8)
Goal: agent in org profile has org context in its system prompt

- [ ] `context_builder.py` — reads `identity.db`, formats as markdown
- [ ] `prompt_builder.py` modification — injects org context
- [ ] Org identity panel UI (owner edit, member read-only)
- [ ] GitHub connection (OAuth + repo selector + context pull)
- [ ] Test: agent in org profile responds with org brand awareness

### Phase 5 — Org Integrations & RBAC (Week 9–10)
Goal: owner connects org apps, members get scoped access

- [ ] `composio_rbac.py` — wrap Composio with read/write scoping
- [ ] `integrations.db` schema and local storage
- [ ] Org integrations panel UI (owner view with connect buttons, member view read-only)
- [ ] Permissions management modal (owner)
- [ ] Permission changes sync to member devices via `sync_client.py`
- [ ] Member's org `.env` updated on permission change
- [ ] Agent enforces access level (returns error on write attempt without write permission)

### Phase 6 — Team Panel & Member Management (Week 11–12)
Goal: full team visibility and owner controls

- [ ] `member_manager.py` — add/remove members, update permissions
- [ ] Team panel UI (member list, online status, joined date)
- [ ] Owner controls: manage permissions per member, remove member
- [ ] Username editing (member edits own username)
- [ ] Member removal flow + sync push to revoke tokens on removed member's device
- [ ] Invite key management UI (view, copy, regenerate)

### Phase 7 — Polish & Security (Week 13–14)
Goal: production-ready security and edge case handling

- [ ] AES-256 encryption for all `.env` files
- [ ] Passphrase setup at first launch
- [ ] All error states implemented (see section 4.14)
- [ ] Offline behaviour (banner, queue, catch-up sync)
- [ ] Org deletion flow
- [ ] Full settings panel (personal + org)
- [ ] End-to-end test: create org, invite 2 members, connect integrations, set permissions, agent tasks across all profiles

---

## 6. Open Questions (Decide Before Building)

1. **Electron app structure** — The `/electron` folder is self-contained inside the Hermes fork. Decide upfront whether the Electron app is a separate `package.json` workspace or merged into the root. **Recommended:** separate workspace so Hermes Python dependencies and Electron Node dependencies don't clash.

2. **Sync server hosting** — Where does the thin cloud sync server live? Options: (a) we host it (cheapest path, Fly.io or Railway), (b) we let orgs self-host it (advanced). **Start with (a) for v1.**

3. **Composio account** — Does each user need their own Composio account, or do we use one Composio project and manage tokens ourselves? Check Composio's multi-tenant pricing before building.

4. **Multi-device for same user** — Out of scope for v1, but flag it. If a user has two laptops, their personal profile is not in sync between them. Decide early whether to promise or explicitly not promise this.

5. **Hermes version to fork from** — Pin to a specific Hermes release tag before starting. Do not fork from `main` — it moves fast (1,000+ commits between releases). Pin to `v0.19.0` or the latest stable tag.

---

## 7. Key Design Principles

1. **Prompt caching is sacred.** Profile switching re-initialises the agent; it does not mutate context mid-conversation.
2. **Core is a narrow waist.** New functionality goes into `orghumans/` module, not `run_agent.py` or `model_tools.py`.
3. **Directory isolation is the security model.** No code path crosses profile boundaries.
4. **Additive changes only to Hermes core.** `hermes_constants.py` and `prompt_builder.py` changes are strictly additive.
5. **Sync server is dumb.** Business logic lives on the client. The sync server broadcasts diffs and holds a snapshot; it does not run permissions logic.
