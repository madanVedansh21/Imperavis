import { app, ipcMain, shell } from 'electron'
import { execFile } from 'child_process'
import { existsSync, readFileSync, writeFileSync, mkdirSync } from 'fs'
import { fileURLToPath } from 'url'
import { dirname, join } from 'path'
import { homedir } from 'os'
import { promisify } from 'util'
import { randomUUID } from 'crypto'

const execFileAsync = promisify(execFile)

const _currentDir = typeof __dirname !== 'undefined'
  ? __dirname
  : dirname(fileURLToPath(import.meta.url))

function getRepoRoot(): string {
  // If running inside compiled ASAR package
  if (app && app.isPackaged) {
    const unpacked = join(process.resourcesPath, 'app.asar.unpacked')
    if (existsSync(unpacked)) return unpacked
    return process.resourcesPath
  }
  // Development mode
  return join(_currentDir, '../../..')
}

const PYTHON_CMD = process.platform === 'win32' ? 'python' : 'python3'

// ── Backend URL ─────────────────────────────────────────────────────────────
// Replace with your deployed Railway / Render / Fly.io backend URL.
// This backend owns the Composio API key — clients never see or input it.
const BACKEND_URL = 'https://orghumanserver.vercel.app/api'

async function runOrghumans(snippet: string): Promise<unknown> {
  const repoRoot = getRepoRoot()
  const script = `
import json, sys
sys.path.insert(0, r'${repoRoot.replace(/\\/g, '\\\\')}')
${snippet}
`
  try {
    const { stdout } = await execFileAsync(PYTHON_CMD, ['-c', script], {
      cwd: existsSync(repoRoot) ? repoRoot : process.cwd(),
      timeout: 20_000,
    })
    const trimmed = stdout.trim()
    return trimmed ? JSON.parse(trimmed) : { ok: true }
  } catch (err) {
    console.error('runOrghumans error:', err)
    throw err
  }
}

export function registerOrghumansIpc(): void {
  // ── Org Management ─────────────────────────────────────────────────────────

  ipcMain.handle(
    'orghumans:org:create',
    async (
      _event,
      {
        name,
        description,
        orgType,
        creatorUsername,
        brandIdentity,
        glossary,
      }: {
        name: string
        description: string
        orgType: string
        creatorUsername: string
        brandIdentity?: Record<string, unknown>
        glossary?: Array<{ term: string; definition: string }>
      }
    ) => {
      try {
        const result = await runOrghumans(`
from orghumans.org_manager import create_org
res = create_org(
    ${JSON.stringify(name)},
    ${JSON.stringify(description)},
    ${JSON.stringify(orgType)},
    ${JSON.stringify(creatorUsername)},
    brand_identity=${JSON.stringify(brandIdentity || null)},
    glossary=${JSON.stringify(glossary || null)}
)
print(json.dumps({'ok': True, 'org': res}))
`)
        return result
      } catch (err) {
        return { ok: false, error: String(err) }
      }
    }
  )

  ipcMain.handle(
    'orghumans:org:join',
    async (_event, { inviteKey, username }: { inviteKey: string; username: string }) => {
      try {
        const result = await runOrghumans(`
from orghumans.org_manager import join_org_by_invite_key
res = join_org_by_invite_key(${JSON.stringify(inviteKey)}, ${JSON.stringify(username)})
print(json.dumps({'ok': True, 'joined': res}))
`)
        return result
      } catch (err) {
        return { ok: false, error: String(err) }
      }
    }
  )

  ipcMain.handle('orghumans:org:list', async () => {
    try {
      const result = await runOrghumans(`
from orghumans.org_manager import list_joined_orgs
print(json.dumps({'ok': True, 'orgs': list_joined_orgs()}))
`)
      return result
    } catch (err) {
      return { ok: false, error: String(err), orgs: [] }
    }
  })

  // ── Integrations ───────────────────────────────────────────────────────────

  const STATIC_CATALOGUE = [
    { id: "gmail", name: "Gmail", description: "Read, send and manage emails.", category: "Email", icon: "📧", color: "#EA4335" },
    { id: "googlecalendar", name: "Google Calendar", description: "Read and create calendar events.", category: "Calendar", icon: "📅", color: "#4285F4" },
    { id: "googledrive", name: "Google Drive", description: "Access and manage files in Drive.", category: "Storage", icon: "📁", color: "#34A853" },
    { id: "googlesheets", name: "Google Sheets", description: "Read and write spreadsheet data.", category: "Productivity", icon: "📊", color: "#0F9D58" },
    { id: "googledocs", name: "Google Docs", description: "Create and edit documents.", category: "Productivity", icon: "📝", color: "#4285F4" },
    { id: "slack", name: "Slack", description: "Send messages and read channels.", category: "Communication", icon: "💬", color: "#4A154B" },
    { id: "discord", name: "Discord", description: "Send messages to Discord channels.", category: "Communication", icon: "🎮", color: "#5865F2" },
    { id: "zoom", name: "Zoom", description: "Schedule and manage Zoom meetings.", category: "Communication", icon: "📹", color: "#2D8CFF" },
    { id: "microsoftteams", name: "Microsoft Teams", description: "Send messages and join meetings.", category: "Communication", icon: "👥", color: "#6264A7" },
    { id: "outlook", name: "Outlook", description: "Read and send Outlook emails.", category: "Email", icon: "📨", color: "#0078D4" },
    { id: "github", name: "GitHub", description: "Manage repos, issues, and PRs.", category: "Development", icon: "🐙", color: "#24292F" },
    { id: "linear", name: "Linear", description: "Create and update Linear issues.", category: "Development", icon: "📐", color: "#5E6AD2" },
    { id: "jira", name: "Jira", description: "Track issues and sprints in Jira.", category: "Development", icon: "🎯", color: "#0052CC" },
    { id: "notion", name: "Notion", description: "Read and write Notion pages.", category: "Productivity", icon: "📓", color: "#000000" },
    { id: "trello", name: "Trello", description: "Manage Trello boards and cards.", category: "Productivity", icon: "📋", color: "#0052CC" },
    { id: "asana", name: "Asana", description: "Create and track Asana tasks.", category: "Productivity", icon: "✅", color: "#F06A6A" },
    { id: "airtable", name: "Airtable", description: "Read and write Airtable bases.", category: "Productivity", icon: "🗃️", color: "#18BFFF" },
    { id: "hubspot", name: "HubSpot", description: "Manage contacts and deals in HubSpot.", category: "CRM", icon: "🧡", color: "#FF7A59" },
    { id: "salesforce", name: "Salesforce", description: "Access Salesforce records and objects.", category: "CRM", icon: "☁️", color: "#00A1E0" },
    { id: "stripe", name: "Stripe", description: "Query payments, customers, and invoices.", category: "Finance", icon: "💳", color: "#635BFF" },
    { id: "twitter", name: "X / Twitter", description: "Post tweets and read timelines.", category: "Social", icon: "🐦", color: "#1DA1F2" },
    { id: "reddit", name: "Reddit", description: "Read subreddits, submit posts and comments.", category: "Social", icon: "🤖", color: "#FF4500" },
    { id: "dropbox", name: "Dropbox", description: "Access and share Dropbox files.", category: "Storage", icon: "📦", color: "#0061FF" },
  ]

  // ── Pure Node.js helpers (no Python subprocess) ─────────────────────────

  /**
   * Returns the OrgHumans data root (where active_profile.json lives).
   * Priority: ORGHUMANS_HOME env > platform default
   * NOTE: This is NOT HERMES_HOME — it is the orghumans root that CONTAINS profiles.
   */
  function getOrghumansRoot(): string {
    const override = process.env.ORGHUMANS_HOME
    if (override) return override
    if (process.platform === 'win32') {
      const local = process.env.LOCALAPPDATA
      return local ? join(local, 'orghumans') : join(homedir(), 'AppData', 'Local', 'orghumans')
    }
    return join(homedir(), '.orghumans')
  }

  /**
   * Mirrors hermes_constants.py `get_hermes_home()` exactly.
   *
   * Resolution order (matches Python):
   *   1. HERMES_HOME env var — if set, use it directly (handles non-standard
   *      installs like D:\OrgHumansData where C: was full)
   *   2. OrgHumans active profile — reads active_profile.json and resolves
   *      the per-profile HERMES_HOME (normal client path)
   *   3. Platform default — Windows: LOCALAPPDATA/hermes · Mac/Linux: ~/.hermes
   *
   * This function is the single source of truth for where config.yaml lives.
   * Never hardcode any absolute path.
   */
  function getHermesHome(): string {
    // 1. Explicit HERMES_HOME override (e.g. dev machine with D: redirect)
    const explicit = process.env.HERMES_HOME?.trim()
    if (explicit) return explicit

    // 2. OrgHumans active profile hook
    try {
      const orgRoot = getOrghumansRoot()
      const activeJson = join(orgRoot, 'active_profile.json')
      if (existsSync(activeJson)) {
        const data = JSON.parse(readFileSync(activeJson, 'utf-8')) as { active?: string }
        const profileId = data.active?.trim()
        if (profileId) {
          const profileHome = join(orgRoot, 'profiles', profileId)
          if (existsSync(profileHome)) return profileHome
        }
      }
    } catch { /* silently fall through to platform default */ }

    // 3. Platform-native default (same as hermes_constants._get_platform_default_hermes_home)
    if (process.platform === 'win32') {
      const local = process.env.LOCALAPPDATA
      return local ? join(local, 'hermes') : join(homedir(), 'AppData', 'Local', 'hermes')
    }
    return join(homedir(), '.hermes')
  }

  /** Returns the orghumans profile directory (for profile.json / entity_id storage). */
  function getProfileHome(profileId: string): string {
    return join(getOrghumansRoot(), 'profiles', profileId)
  }

  // Keep getOrghumansHome as a backwards-compat alias used by existing callers.
  function getOrghumansHome(): string { return getOrghumansRoot() }

  /**
   * Reads or creates a stable entity_id for this client.
   * Stored in <orghumansRoot>/profiles/<profileId>/profile.json
   * This is the only identifier passed to the backend — the client
   * never sees or inputs a Composio API key.
   */
  function getOrCreateEntityId(profileId: string): string {
    const profileHome = getProfileHome(profileId)
    mkdirSync(profileHome, { recursive: true })
    const profileJsonPath = join(profileHome, 'profile.json')

    let data: Record<string, string> = {}
    if (existsSync(profileJsonPath)) {
      try {
        data = JSON.parse(readFileSync(profileJsonPath, 'utf-8'))
      } catch { /* corrupt JSON — start fresh */ }
    }

    if (!data.entity_id) {
      data.entity_id = randomUUID()
      writeFileSync(profileJsonPath, JSON.stringify(data, null, 2), 'utf-8')
    }

    return data.entity_id
  }

  // ── Integration IPC handlers ───────────────────────────────────────────────

  ipcMain.handle('orghumans:integrations:listAvailable', async () =>
    // Return static catalogue immediately — no Python subprocess needed
    ({ ok: true, integrations: STATIC_CATALOGUE })
  )

  ipcMain.handle('orghumans:integrations:listConnected', async (_event, profileId: string) => {
    try {
      const result = await runOrghumans(`
from orghumans.composio_client import get_connected_integrations
print(json.dumps(get_connected_integrations(${JSON.stringify(profileId)})))
`)
      return { ok: true, connected: result }
    } catch (err) {
      return { ok: true, connected: [] }
    }
  })

  /**
   * initiateOAuth: POST to our backend, which calls Composio using its
   * server-side API key, and returns a redirect URL for this entity_id.
   * The client just opens the URL — they never touch a Composio key.
   */
  ipcMain.handle(
    'orghumans:integrations:initiateOAuth',
    async (_event, { provider, profileId }: { provider: string; profileId: string }) => {
      try {
        const entityId = getOrCreateEntityId(profileId)

        const response = await fetch(`${BACKEND_URL}/integrations/connect`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ entity_id: entityId, app: provider }),
        })

        if (!response.ok) {
          const errText = await response.text()
          return { ok: false, error: `Backend error ${response.status}: ${errText}` }
        }

        const data = (await response.json()) as { url?: string }
        const url = data.url
        if (!url) return { ok: false, error: 'Backend did not return a redirect URL' }

        await shell.openExternal(url)
        return { ok: true, url }
      } catch (err) {
        return { ok: false, error: String(err) }
      }
    }
  )

  /**
   * getIntegrationStatus: GET backend status for this entity_id.
   * Returns which apps are actually connected in Composio, then syncs
   * the local SQLite DB so the UI status dots are accurate.
   */
  ipcMain.handle(
    'orghumans:integrations:getStatus',
    async (_event, profileId: string) => {
      try {
        const entityId = getOrCreateEntityId(profileId)

        const response = await fetch(
          `${BACKEND_URL}/integrations/status?entity_id=${encodeURIComponent(entityId)}`
        )

        if (!response.ok) {
          return { ok: false, connected: [] }
        }

        const data = (await response.json()) as { connected?: string[] }
        const connectedApps: string[] = data.connected ?? []

        // Sync results into local SQLite so the UI tile dots are accurate
        for (const app of connectedApps) {
          try {
            await runOrghumans(`
from orghumans.db.integrations_db import upsert_connection
upsert_connection(${JSON.stringify(profileId)}, ${JSON.stringify(app)}, status='active')
print(json.dumps({'ok': True}))
`)
          } catch { /* non-fatal */ }
        }

        return { ok: true, connected: connectedApps }
      } catch (err) {
        return { ok: false, connected: [], error: String(err) }
      }
    }
  )

  ipcMain.handle(
    'orghumans:integrations:disconnect',
    async (_event, { provider, profileId }: { provider: string; profileId: string }) => {
      try {
        const entityId = getOrCreateEntityId(profileId)

        // 1. Tell the backend to actually disconnect it from Composio
        const response = await fetch(`${BACKEND_URL}/integrations/disconnect`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ entity_id: entityId, app: provider }),
        })

        if (!response.ok) {
          console.warn(`[Integrations] Backend disconnect failed for ${provider}: ${response.status}`)
        }

        // 2. Delete from local SQLite
        await runOrghumans(`
from orghumans.db.integrations_db import delete_connection
delete_connection(${JSON.stringify(profileId)}, ${JSON.stringify(provider)})
print(json.dumps({'ok': True}))
`)
        return { ok: true }
      } catch (err) {
        return { ok: false, error: String(err) }
      }
    }
  )

  // markConnected: called by the UI after the user confirms OAuth in the browser
  ipcMain.handle(
    'orghumans:integrations:markConnected',
    async (_event, { provider, profileId }: { provider: string; profileId: string }) => {
      try {
        await runOrghumans(`
from orghumans.db.integrations_db import upsert_connection
upsert_connection(${JSON.stringify(profileId)}, ${JSON.stringify(provider)}, status='active')
print(json.dumps({'ok': True}))
`)
        return { ok: true }
      } catch (err) {
        return { ok: false, error: String(err) }
      }
    }
  )

  // getEntityId: expose entity_id to the renderer (read-only)
  ipcMain.handle('orghumans:integrations:getEntityId', async (_event, profileId: string) => {
    try {
      const entityId = getOrCreateEntityId(profileId)
      return { ok: true, entityId }
    } catch (err) {
      return { ok: false, error: String(err) }
    }
  })

  /**
   * writeMcpConfig: Fetches a per-user Composio MCP URL from the backend and
   * writes it into the correct config.yaml (resolved via getHermesHome()).
   *
   * The resolution is dynamic — it will work correctly regardless of whether
   * the client has HERMES_HOME set (like a D: redirect), uses OrgHumans profiles,
   * or is on a plain Hermes install. No path is hardcoded.
   */
  ipcMain.handle('orghumans:integrations:writeMcpConfig', async (_event, profileId: string) => {
    try {
      const entityId = getOrCreateEntityId(profileId)
      const hermesHome = getHermesHome()

      // 1. Fetch per-user MCP URL from our Vercel backend proxy
      const response = await fetch(`${BACKEND_URL}/integrations/mcp-url`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ entity_id: entityId }),
      })
      if (!response.ok) {
        const err = await response.text()
        return { ok: false, error: `Backend error: ${err}` }
      }
      const { url } = (await response.json()) as { url: string }
      if (!url) return { ok: false, error: 'Backend returned no MCP URL' }

      // 2. Read existing config.yaml (if any) and patch mcp_servers block
      const configPath = join(hermesHome, 'config.yaml')
      mkdirSync(hermesHome, { recursive: true })

      // Use a minimal yaml write — we only touch the composio-integrations key
      // and preserve everything else by doing a line-level upsert.
      // IMPORTANT: Only match an *uncommented* mcp_servers key (starts at column 0,
      // no leading '#' or whitespace) to avoid being confused by the commented-out
      // template block that ships inside the default config.yaml.
      let yaml = existsSync(configPath) ? readFileSync(configPath, 'utf-8') : ''

      const serverKey = 'composio-integrations'
      // Matches an uncommented top-level mcp_servers: key
      const hasMcpBlock = /^mcp_servers:/m.test(yaml)
      // Matches an uncommented composio-integrations: key (indented under mcp_servers)
      const hasOurKey = new RegExp(`^  ${serverKey}:`, 'm').test(yaml)

      const serverEntry = [
        `  ${serverKey}:`,
        `    url: "${url}"`,
        `    transport: streamable_http`,
      ].join('\n')

      if (!hasMcpBlock) {
        // No active mcp_servers block — append a clean one at the end
        yaml = yaml.trimEnd() + '\n\nmcp_servers:\n' + serverEntry + '\n'
      } else if (!hasOurKey) {
        // Active mcp_servers block exists but our key is missing — inject under it
        yaml = yaml.replace(
          /^mcp_servers:/m,
          `mcp_servers:\n${serverEntry}`
        )
      } else {
        // Key already exists — update just the url line in-place
        yaml = yaml.replace(
          new RegExp(`(^  ${serverKey}:[\\s\\S]*?^    url: )[^\\n]+`, 'm'),
          `$1"${url}"`
        )
      }

      writeFileSync(configPath, yaml, 'utf-8')
      return { ok: true, hermesHome, configPath, url }
    } catch (err) {
      return { ok: false, error: String(err) }
    }
  })

  // ── Org RBAC Management ───────────────────────────────────────────────────

  ipcMain.handle('orghumans:org:integrations:list', async (_event, orgId: string) => {
    try {
      const result = await runOrghumans(`
from orghumans.composio_rbac import list_org_integrations
print(json.dumps({'ok': True, 'integrations': list_org_integrations(${JSON.stringify(orgId)})}))
`)
      return result
    } catch (err) {
      return { ok: false, error: String(err), integrations: [] }
    }
  })

  ipcMain.handle(
    'orghumans:org:integrations:setPermission',
    async (
      _event,
      {
        orgId,
        provider,
        username,
        canRead,
        canWrite,
      }: {
        orgId: string
        provider: string
        username: string
        canRead: boolean
        canWrite: boolean
      }
    ) => {
      try {
        await runOrghumans(`
from orghumans.composio_rbac import set_member_permission
set_member_permission(
    ${JSON.stringify(orgId)},
    ${JSON.stringify(provider)},
    ${JSON.stringify(username)},
    can_read=${canRead ? 'True' : 'False'},
    can_write=${canWrite ? 'True' : 'False'}
)
print(json.dumps({'ok': True}))
`)
        return { ok: true }
      } catch (err) {
        return { ok: false, error: String(err) }
      }
    }
  )

  // ── Sync Protocol ──────────────────────────────────────────────────────────

  ipcMain.handle('orghumans:sync:status', async (_event, orgId: string) => {
    try {
      const result = await runOrghumans(`
from orghumans.sync import generate_challenge
nonce = generate_challenge()
print(json.dumps({'ok': True, 'sync_ready': True, 'nonce': nonce}))
`)
      return result
    } catch (err) {
      return { ok: false, sync_ready: false, error: String(err) }
    }
  })
}
