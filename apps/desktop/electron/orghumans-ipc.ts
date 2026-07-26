import { app, ipcMain, shell } from 'electron'
import { execFile } from 'child_process'
import { existsSync } from 'fs'
import { fileURLToPath } from 'url'
import { dirname, join } from 'path'
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

  ipcMain.handle('orghumans:integrations:listAvailable', async () => {
    try {
      const result = await runOrghumans(`
from orghumans.composio_client import list_available_integrations
print(json.dumps(list_available_integrations()))
`)
      return { ok: true, integrations: result }
    } catch (err) {
      return { ok: false, error: String(err), integrations: [] }
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
      return { ok: false, error: String(err), connected: [] }
    }
  })

  ipcMain.handle(
    'orghumans:integrations:initiateOAuth',
    async (_event, { provider, profileId }: { provider: string; profileId: string }) => {
      try {
        const result = (await runOrghumans(`
from orghumans.composio_client import initiate_oauth
url = initiate_oauth(${JSON.stringify(provider)}, ${JSON.stringify(profileId)})
print(json.dumps({'url': url}))
`)) as { url: string }
        if (result.url) {
          await shell.openExternal(result.url)
        }
        return { ok: true, url: result.url }
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

  ipcMain.handle('orghumans:integrations:hasComposioKey', async (_event, profileId: string) => {
    try {
      const result = (await runOrghumans(`
from orghumans.composio_client import has_composio_api_key
print(json.dumps({'has_key': has_composio_api_key(${JSON.stringify(profileId)})}))
`)) as { has_key: boolean }
      return { ok: true, hasKey: result.has_key }
    } catch (err) {
      return { ok: false, hasKey: false, error: String(err) }
    }
  })

  ipcMain.handle(
    'orghumans:integrations:setComposioKey',
    async (_event, { profileId, apiKey }: { profileId: string; apiKey: string }) => {
      try {
        await runOrghumans(`
from orghumans.composio_client import set_composio_api_key
set_composio_api_key(${JSON.stringify(profileId)}, ${JSON.stringify(apiKey)})
print(json.dumps({'ok': True}))
`)
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
