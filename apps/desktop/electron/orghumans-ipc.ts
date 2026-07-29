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

  function getOrghumansHome(): string {
    const override = process.env.ORGHUMANS_HOME || process.env.HERMES_HOME
    if (override) return override
    if (process.platform === 'win32') {
      const local = process.env.LOCALAPPDATA
      return local ? join(local, 'orghumans') : join(homedir(), 'AppData', 'Local', 'orghumans')
    }
    return join(homedir(), '.orghumans')
  }

  function getProfileHome(profileId: string): string {
    return join(getOrghumansHome(), 'profiles', profileId)
  }

  /**
   * Reads or creates a stable entity_id for this client.
   * Stored in ~/.orghumans/profiles/<profileId>/profile.json
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
        // Delete from local SQLite — pure, fast, no Python Composio SDK
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
