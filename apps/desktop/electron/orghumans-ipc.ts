import { app, ipcMain, shell } from 'electron'
import { execFile } from 'child_process'
import { existsSync, readFileSync, writeFileSync, mkdirSync } from 'fs'
import { fileURLToPath } from 'url'
import { dirname, join } from 'path'
import { homedir } from 'os'
import { promisify } from 'util'

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
    { id: "googledocs", name: "Google Docs", description: "Create and edit documents.", category: "Productivity", icon: "📝", category_name: "Productivity", color: "#4285F4" },
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
    { id: "airtable", "name": "Airtable", description: "Read and write Airtable bases.", category: "Productivity", icon: "🗃️", color: "#18BFFF" },
    { id: "hubspot", name: "HubSpot", description: "Manage contacts and deals in HubSpot.", category: "CRM", icon: "🧡", color: "#FF7A59" },
    { id: "salesforce", name: "Salesforce", description: "Access Salesforce records and objects.", category: "CRM", icon: "☁️", color: "#00A1E0" },
    { id: "stripe", name: "Stripe", description: "Query payments, customers, and invoices.", category: "Finance", icon: "💳", color: "#635BFF" },
    { id: "twitter", name: "X / Twitter", description: "Post tweets and read timelines.", category: "Social", icon: "🐦", color: "#1DA1F2" },
    { id: "reddit", name: "Reddit", description: "Read subreddits, submit posts and comments.", category: "Social", icon: "🤖", color: "#FF4500" },
    { id: "dropbox", name: "Dropbox", description: "Access and share Dropbox files.", category: "Storage", icon: "📦", color: "#0061FF" },
  ]

  ipcMain.handle('orghumans:integrations:listAvailable', async () => {
    try {
      const result = await runOrghumans(`
from orghumans.composio_client import list_available_integrations
print(json.dumps(list_available_integrations()))
`)
      return { ok: true, integrations: (result as any[]) || STATIC_CATALOGUE }
    } catch (err) {
      return { ok: true, integrations: STATIC_CATALOGUE }
    }
  })

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

  // ── Direct Node.js helpers (no Python subprocess) ─────────────────────────

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
    return join(getOrghumansHome(), 'profiles', profileId, 'hermes-home')
  }

  function readComposioKey(profileId: string): string {
    // 1. Process env
    if (process.env.COMPOSIO_API_KEY) return process.env.COMPOSIO_API_KEY
    // 2. Profile .env file
    const envPath = join(getProfileHome(profileId), '.env')
    if (existsSync(envPath)) {
      const lines = readFileSync(envPath, 'utf-8').split('\n')
      for (const line of lines) {
        if (line.startsWith('COMPOSIO_API_KEY=')) {
          const val = line.slice('COMPOSIO_API_KEY='.length).trim()
          if (val) return val
        }
      }
    }
    // 3. No built-in fallback — user must supply their own Composio API key
    return ''
  }

  function writeComposioKey(profileId: string, apiKey: string): void {
    const profileHome = getProfileHome(profileId)
    mkdirSync(profileHome, { recursive: true })
    const envPath = join(profileHome, '.env')
    let lines: string[] = []
    if (existsSync(envPath)) {
      lines = readFileSync(envPath, 'utf-8').split('\n')
    }
    const keyLine = `COMPOSIO_API_KEY=${apiKey}`
    const idx = lines.findIndex(l => l.startsWith('COMPOSIO_API_KEY='))
    if (idx >= 0) {
      lines[idx] = keyLine
    } else {
      lines.push(keyLine)
    }
    writeFileSync(envPath, lines.join('\n'), 'utf-8')
  }

  // OAuth: open Composio portal directly in the system browser — no Python needed
  ipcMain.handle(
    'orghumans:integrations:initiateOAuth',
    async (_event, { provider, profileId }: { provider: string; profileId: string }) => {
      try {
        const composioKey = readComposioKey(profileId)
        // Build the Composio OAuth/portal URL
        // With a valid API key, Composio's dashboard handles OAuth for the user
        const url = `https://app.composio.dev/apps/${provider.toLowerCase()}`
        await shell.openExternal(url)
        // Best-effort: record locally that the user initiated connection
        try {
          await runOrghumans(`
from orghumans.db.integrations_db import upsert_connection
upsert_connection(${JSON.stringify(profileId)}, ${JSON.stringify(provider)}, status='active')
print(json.dumps({'ok': True}))
`)
        } catch { /* non-fatal */ }
        return { ok: true, url, composioKey: !!composioKey }
      } catch (err) {
        return { ok: false, error: String(err) }
      }
    }
  )

  ipcMain.handle(
    'orghumans:integrations:disconnect',
    async (_event, { provider, profileId }: { provider: string; profileId: string }) => {
      try {
        await runOrghumans(`
from orghumans.composio_client import disconnect_integration
disconnect_integration(${JSON.stringify(provider)}, ${JSON.stringify(profileId)})
print(json.dumps({'ok': True}))
`)
        return { ok: true }
      } catch (err) {
        return { ok: false, error: String(err) }
      }
    }
  )

  // hasComposioKey: pure Node.js — reads .env directly, zero Python overhead
  ipcMain.handle('orghumans:integrations:hasComposioKey', async (_event, profileId: string) => {
    try {
      const key = readComposioKey(profileId)
      return { ok: true, hasKey: Boolean(key) }
    } catch (err) {
      return { ok: true, hasKey: false }
    }
  })

  // setComposioKey: pure Node.js — writes .env directly, zero Python overhead
  ipcMain.handle(
    'orghumans:integrations:setComposioKey',
    async (_event, { profileId, apiKey }: { profileId: string; apiKey: string }) => {
      try {
        writeComposioKey(profileId, apiKey)
        // Also try via Python for any extra side effects (best-effort)
        try {
          await runOrghumans(`
from orghumans.composio_client import set_composio_api_key
set_composio_api_key(${JSON.stringify(profileId)}, ${JSON.stringify(apiKey)})
print(json.dumps({'ok': True}))
`)
        } catch { /* non-fatal */ }
        return { ok: true }
      } catch (err) {
        return { ok: false, error: String(err) }
      }
    }
  )

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
