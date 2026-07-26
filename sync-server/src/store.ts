import type { WebSocket } from 'ws'

export interface OrgRecord {
  orgId: string
  name: string
  keyHash: string
  description?: string
  orgType: string
  createdBy: string
  createdAt: string
  members: Array<{ username: string; role: string; joinedAt: string }>
}

class OrgStore {
  private orgs = new Map<string, OrgRecord>()
  private connections = new Map<string, Set<WebSocket>>()

  createOrg(record: OrgRecord): OrgRecord {
    this.orgs.set(record.orgId, record)
    return record
  }

  getOrg(orgId: string): OrgRecord | undefined {
    return this.orgs.get(orgId)
  }

  findOrgByKeyHash(keyHash: string): OrgRecord | undefined {
    for (const org of this.orgs.values()) {
      if (org.keyHash === keyHash) return org
    }
    return undefined
  }

  addMember(orgId: string, username: string, role = 'member'): boolean {
    const org = this.orgs.get(orgId)
    if (!org) return false
    if (!org.members.some(m => m.username === username)) {
      org.members.push({ username, role, joinedAt: new Date().toISOString() })
    }
    return true
  }

  registerWs(orgId: string, ws: WebSocket) {
    if (!this.connections.has(orgId)) {
      this.connections.set(orgId, new Set())
    }
    this.connections.get(orgId)!.add(ws)
  }

  unregisterWs(orgId: string, ws: WebSocket) {
    const clients = this.connections.get(orgId)
    if (clients) {
      clients.delete(ws)
      if (clients.size === 0) this.connections.delete(orgId)
    }
  }

  broadcast(orgId: string, sender: WebSocket, data: unknown) {
    const clients = this.connections.get(orgId)
    if (!clients) return
    const payload = JSON.stringify(data)
    for (const client of clients) {
      if (client !== sender && client.readyState === 1) {
        client.send(payload)
      }
    }
  }
}

export const orgStore = new OrgStore()
