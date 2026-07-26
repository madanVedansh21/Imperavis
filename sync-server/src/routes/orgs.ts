import type { FastifyInstance } from 'fastify'
import { hashInviteKey } from '../crypto.js'
import { orgStore } from '../store.js'

export async function orgRoutes(fastify: FastifyInstance) {
  // Create Organisation
  fastify.post('/orgs', async (req, reply) => {
    const body = req.body as {
      orgId: string
      name: string
      inviteKey: string
      description?: string
      orgType: string
      createdBy: string
    }

    if (!body.orgId || !body.name || !body.inviteKey || !body.createdBy) {
      return reply.code(400).send({ error: 'Missing required org fields' })
    }

    const keyHash = hashInviteKey(body.inviteKey)
    const org = orgStore.createOrg({
      orgId: body.orgId,
      name: body.name,
      keyHash,
      description: body.description,
      orgType: body.orgType || 'General',
      createdBy: body.createdBy,
      createdAt: new Date().toISOString(),
      members: [{ username: body.createdBy, role: 'owner', joinedAt: new Date().toISOString() }],
    })

    return reply.code(201).send({ ok: true, orgId: org.orgId })
  })

  // Join Organisation by Invite Key
  fastify.post('/orgs/join', async (req, reply) => {
    const body = req.body as { inviteKey: string; username: string }
    if (!body.inviteKey || !body.username) {
      return reply.code(400).send({ error: 'Missing inviteKey or username' })
    }

    const keyHash = hashInviteKey(body.inviteKey)
    const org = orgStore.findOrgByKeyHash(keyHash)

    if (!org) {
      return reply.code(404).send({ error: 'Invalid invite key or org not found' })
    }

    orgStore.addMember(org.orgId, body.username, 'member')

    return reply.send({
      ok: true,
      org: {
        org_id: org.orgId,
        name: org.name,
        description: org.description,
        org_type: org.orgType,
        created_by: org.createdBy,
        created_at: org.createdAt,
      },
    })
  })
}
