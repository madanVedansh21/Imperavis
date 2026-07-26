import Fastify from 'fastify'
import cors from '@fastify/cors'
import websocket from '@fastify/websocket'
import { orgRoutes } from './routes/orgs.js'
import { orgStore } from './store.js'

const server = Fastify({ logger: true })

await server.register(cors, { origin: true })
await server.register(websocket)

await server.register(orgRoutes)

// Health check
server.get('/health', async () => ({ status: 'ok', time: new Date().toISOString() }))

// WebSocket sync channel per org
server.get('/orgs/:orgId/sync', { websocket: true }, (connection, req) => {
  const { orgId } = req.params as { orgId: string }
  const socket = connection.socket

  orgStore.registerWs(orgId, socket)
  server.log.info(`Client connected to sync channel for org ${orgId}`)

  socket.on('message', (message: Buffer) => {
    try {
      const data = JSON.parse(message.toString())
      // Relay diff to all other clients in the same org
      orgStore.broadcast(orgId, socket, data)
    } catch (err) {
      server.log.error('Failed to parse WS message:', err)
    }
  })

  socket.on('close', () => {
    orgStore.unregisterWs(orgId, socket)
    server.log.info(`Client disconnected from sync channel for org ${orgId}`)
  })
})

const PORT = Number(process.env.PORT || 8080)
const HOST = '0.0.0.0'

try {
  await server.listen({ port: PORT, host: HOST })
  console.log(`OrgHumans Sync Server running on http://${HOST}:${PORT}`)
} catch (err) {
  server.log.error(err)
  process.exit(1)
}
