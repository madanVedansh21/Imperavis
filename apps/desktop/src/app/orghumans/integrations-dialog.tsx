import { useEffect, useState } from 'react'
import { useStore } from '@nanostores/react'
import { $activeGatewayProfile } from '@/store/profile'

interface Integration {
  id: string
  name: string
  description: string
  category: string
  icon: string
  color: string
}

interface ConnectedIntegration {
  provider: string
  connected_at: string
  status: 'active' | 'expired' | 'error'
}

const CATEGORIES = [
  'All',
  'Email',
  'Calendar',
  'Communication',
  'Development',
  'Productivity',
  'CRM',
  'Finance',
  'Social',
  'Storage',
]

export function IntegrationsDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const activeProfile = useStore($activeGatewayProfile) || 'personal'
  const [available, setAvailable] = useState<Integration[]>([])
  const [connected, setConnected] = useState<ConnectedIntegration[]>([])
  const [search, setSearch] = useState('')
  const [selectedCat, setSelectedCat] = useState('All')
  const [loading, setLoading] = useState(false)
  const [composioKey, setComposioKeyInput] = useState('')
  const [hasKey, setHasKey] = useState(true)
  const [showKeyModal, setShowKeyModal] = useState(false)
  const [disconnecting, setDisconnecting] = useState<string | null>(null)
  const [pendingProvider, setPendingProvider] = useState<string | null>(null)

  const loadIntegrations = async () => {
    if (!window.hermesDesktop?.orghumans) return
    setLoading(true)

    try {
      const keyRes = await window.hermesDesktop.orghumans.hasComposioKey(activeProfile)
      setHasKey(keyRes?.hasKey ?? false)
    } catch {
      setHasKey(false)
    }

    try {
      const availRes = await window.hermesDesktop.orghumans.listAvailableIntegrations()
      if (availRes?.integrations && availRes.integrations.length > 0) {
        setAvailable(availRes.integrations)
      }
    } catch (err) {
      console.error('[Integrations] failed to load available:', err)
    }

    try {
      const connRes = await window.hermesDesktop.orghumans.listConnectedIntegrations(activeProfile)
      if (connRes?.connected) {
        setConnected(connRes.connected)
      }
    } catch (err) {
      console.error('[Integrations] failed to load connected:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (open) {
      loadIntegrations()
    }
  }, [open, activeProfile])

  const isConnected = (providerId: string) =>
    connected.some(c => c.provider.toLowerCase() === providerId.toLowerCase() && c.status === 'active')

  const handleConnect = async (provider: string) => {
    if (!hasKey) {
      setPendingProvider(provider)
      setShowKeyModal(true)
      return
    }
    try {
      await window.hermesDesktop?.orghumans?.initiateOAuth({ provider, profileId: activeProfile })
    } catch (err) {
      console.error('[Integrations] OAuth error:', err)
    }
  }

  const handleDisconnect = async (provider: string) => {
    try {
      await window.hermesDesktop?.orghumans?.disconnectIntegration({ provider, profileId: activeProfile })
      setDisconnecting(null)
      await loadIntegrations()
    } catch (err) {
      console.error('[Integrations] Disconnect error:', err)
    }
  }

  const handleSaveComposioKey = async () => {
    if (!composioKey.trim()) return
    try {
      await window.hermesDesktop?.orghumans?.setComposioKey({
        profileId: activeProfile,
        apiKey: composioKey.trim(),
      })
      setHasKey(true)
      setShowKeyModal(false)
      setComposioKeyInput('')
      // Auto-proceed with the connection that triggered the key prompt
      if (pendingProvider) {
        const provider = pendingProvider
        setPendingProvider(null)
        try {
          await window.hermesDesktop?.orghumans?.initiateOAuth({ provider, profileId: activeProfile })
        } catch (err) {
          console.error('[Integrations] OAuth error after key save:', err)
        }
      }
    } catch (err) {
      console.error('[Integrations] Save key error:', err)
    }
  }

  const filtered = available.filter(item => {
    const matchSearch =
      item.name.toLowerCase().includes(search.toLowerCase()) ||
      item.description.toLowerCase().includes(search.toLowerCase())
    const matchCat = selectedCat === 'All' || item.category.toLowerCase() === selectedCat.toLowerCase()
    return matchSearch && matchCat
  })

  if (!open) return null

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.8)',
        backdropFilter: 'blur(16px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 9999,
      }}
      onClick={onClose}
    >
      <div
        style={{
          width: 760,
          maxHeight: '85vh',
          background: '#0d0d12',
          border: '1px solid rgba(124, 107, 255, 0.25)',
          boxShadow: '0 20px 50px rgba(0, 0, 0, 0.8), 0 0 30px rgba(124, 107, 255, 0.15)',
          borderRadius: 16,
          padding: 28,
          display: 'flex',
          flexDirection: 'column',
          color: '#e8e6ff',
          overflow: 'hidden',
        }}
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <div>
            <h2 style={{ margin: 0, fontSize: 20, fontWeight: 600 }}>Integrations & Apps</h2>
            <p style={{ margin: '4px 0 0', fontSize: 13, color: '#9590b8' }}>
              Connect your personal accounts via Composio (Profile: <strong>{activeProfile}</strong>)
            </p>
          </div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <button
              style={{
                background: hasKey ? 'rgba(16, 185, 129, 0.12)' : 'rgba(255,255,255,0.05)',
                border: hasKey ? '1px solid rgba(16, 185, 129, 0.4)' : '1px solid rgba(255,255,255,0.1)',
                color: hasKey ? '#34d399' : '#9590b8',
                borderRadius: 8,
                padding: '6px 12px',
                fontSize: 12,
                fontWeight: 500,
                cursor: 'pointer',
              }}
              onClick={() => setShowKeyModal(true)}
            >
              {hasKey ? '✓ API Key Configured' : '⚙️ Set API Key'}
            </button>
            <button
              style={{
                background: 'rgba(255,255,255,0.06)',
                border: 'none',
                color: '#9590b8',
                borderRadius: 8,
                padding: '6px 12px',
                cursor: 'pointer',
              }}
              onClick={onClose}
            >
              ✕
            </button>
          </div>
        </div>

        {/* Composio API Key Warning Banner */}
        {!hasKey && (
          <div
            style={{
              background: 'rgba(124, 107, 255, 0.12)',
              border: '1px solid rgba(124, 107, 255, 0.3)',
              borderRadius: 10,
              padding: '12px 16px',
              marginBottom: 16,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <span style={{ fontSize: 13, color: '#d8d4ff' }}>
              🔑 Set your Composio API key to connect third-party OAuth apps.
            </span>
            <button
              style={{
                background: '#7c6bff',
                color: '#fff',
                border: 'none',
                borderRadius: 6,
                padding: '6px 12px',
                fontSize: 12,
                fontWeight: 600,
                cursor: 'pointer',
              }}
              onClick={() => setShowKeyModal(true)}
            >
              Add API Key
            </button>
          </div>
        )}

        {/* Search & Categories */}
        <div style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
          <input
            style={{
              flex: 1,
              background: 'rgba(255,255,255,0.05)',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: 8,
              padding: '8px 14px',
              color: '#fff',
              fontSize: 13,
              outline: 'none',
            }}
            placeholder="Search integrations..."
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>

        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 20 }}>
          {CATEGORIES.map(cat => (
            <button
              key={cat}
              style={{
                background: selectedCat === cat ? 'rgba(124, 107, 255, 0.25)' : 'rgba(255,255,255,0.04)',
                border: selectedCat === cat ? '1px solid #7c6bff' : '1px solid rgba(255,255,255,0.08)',
                color: selectedCat === cat ? '#fff' : '#9590b8',
                borderRadius: 20,
                padding: '4px 12px',
                fontSize: 12,
                cursor: 'pointer',
              }}
              onClick={() => setSelectedCat(cat)}
            >
              {cat}
            </button>
          ))}
        </div>

        {/* Integration Tile Grid (App Directory view matching Composio App Store) */}
        <div
          style={{
            flex: 1,
            overflowY: 'auto',
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(104px, 1fr))',
            gap: 12,
            paddingRight: 4,
          }}
        >
          {filtered.map(item => {
            const connectedState = isConnected(item.id)
            return (
              <div
                key={item.id}
                title={`${item.name} — ${item.description}`}
                style={{
                  position: 'relative',
                  background: connectedState ? 'rgba(124, 107, 255, 0.12)' : 'rgba(20, 20, 28, 0.8)',
                  border: connectedState ? '1px solid rgba(124, 107, 255, 0.5)' : '1px solid rgba(255, 255, 255, 0.07)',
                  borderRadius: 14,
                  padding: '14px 10px 10px',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                  userSelect: 'none',
                }}
                onClick={() => {
                  if (connectedState) {
                    setDisconnecting(item.id)
                  } else {
                    handleConnect(item.id)
                  }
                }}
                onMouseEnter={e => {
                  e.currentTarget.style.borderColor = '#7c6bff'
                  e.currentTarget.style.transform = 'translateY(-2px)'
                  e.currentTarget.style.boxShadow = '0 6px 16px rgba(124, 107, 255, 0.2)'
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.borderColor = connectedState ? 'rgba(124, 107, 255, 0.5)' : 'rgba(255, 255, 255, 0.07)'
                  e.currentTarget.style.transform = 'none'
                  e.currentTarget.style.boxShadow = 'none'
                }}
              >
                {/* Connected status indicator dot */}
                {connectedState && (
                  <span
                    style={{
                      position: 'absolute',
                      top: 8,
                      right: 8,
                      width: 8,
                      height: 8,
                      borderRadius: '50%',
                      background: '#10b981',
                      boxShadow: '0 0 8px #10b981',
                    }}
                  />
                )}

                {/* App Icon */}
                <div
                  style={{
                    fontSize: 32,
                    marginBottom: 8,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    width: 48,
                    height: 48,
                    background: 'rgba(255,255,255,0.04)',
                    borderRadius: 12,
                  }}
                >
                  {item.icon}
                </div>

                {/* App Name */}
                <div
                  style={{
                    fontSize: 12,
                    fontWeight: 600,
                    color: '#e4e4e7',
                    textAlign: 'center',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    maxWidth: '100%',
                  }}
                >
                  {item.name}
                </div>

                {/* Status Subtitle */}
                <div
                  style={{
                    fontSize: 10,
                    color: connectedState ? '#34d399' : '#71717a',
                    marginTop: 2,
                    fontWeight: 500,
                  }}
                >
                  {connectedState ? 'Connected' : 'Click to add'}
                </div>
              </div>
            )
          })}
        </div>

        {/* Composio Key Modal */}
        {showKeyModal && (
          <div
            style={{
              position: 'fixed',
              inset: 0,
              background: 'rgba(0,0,0,0.85)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 10000,
            }}
          >
            <div style={{ width: 420, background: '#13131a', border: '1px solid #7c6bff', borderRadius: 12, padding: 24 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                <h3 style={{ margin: 0, fontSize: 16 }}>Composio API Key</h3>
                {hasKey && (
                  <span style={{ fontSize: 11, background: 'rgba(16, 185, 129, 0.15)', color: '#34d399', padding: '2px 8px', borderRadius: 12, border: '1px solid rgba(16, 185, 129, 0.3)', fontWeight: 600 }}>
                    ✓ Configured
                  </span>
                )}
              </div>
              <p style={{ margin: '0 0 16px', fontSize: 12, color: '#9590b8' }}>
                {hasKey
                  ? 'Your Composio API key is active. Enter a new key below if you wish to update or replace it.'
                  : 'Enter your API key from app.composio.dev to connect third-party OAuth apps.'}
              </p>
              <input
                type="password"
                style={{
                  width: '100%',
                  background: 'rgba(255,255,255,0.06)',
                  border: '1px solid rgba(255,255,255,0.15)',
                  borderRadius: 8,
                  padding: '8px 12px',
                  color: '#fff',
                  fontSize: 13,
                  marginBottom: 16,
                }}
                placeholder="ak_..."
                value={composioKey}
                onChange={e => setComposioKeyInput(e.target.value)}
              />
              <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
                <button
                  style={{ background: 'transparent', border: 'none', color: '#9590b8', cursor: 'pointer', padding: '6px 12px' }}
                  onClick={() => setShowKeyModal(false)}
                >
                  Close
                </button>
                <button
                  style={{ background: '#7c6bff', border: 'none', color: '#fff', borderRadius: 6, padding: '6px 16px', fontWeight: 600, cursor: 'pointer' }}
                  onClick={handleSaveComposioKey}
                >
                  {hasKey ? 'Update Key' : 'Save Key'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Disconnect Modal */}
        {disconnecting && (
          <div
            style={{
              position: 'fixed',
              inset: 0,
              background: 'rgba(0,0,0,0.85)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 10000,
            }}
          >
            <div style={{ width: 360, background: '#13131a', border: '1px solid rgba(239,68,68,0.5)', borderRadius: 12, padding: 24 }}>
              <h3 style={{ margin: '0 0 8px', fontSize: 16, color: '#f87171' }}>Disconnect Integration?</h3>
              <p style={{ margin: '0 0 16px', fontSize: 13, color: '#9590b8' }}>
                Are you sure you want to disconnect <strong>{disconnecting}</strong> from profile <strong>{activeProfile}</strong>?
              </p>
              <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
                <button
                  style={{ background: 'transparent', border: 'none', color: '#9590b8', cursor: 'pointer', padding: '6px 12px' }}
                  onClick={() => setDisconnecting(null)}
                >
                  Cancel
                </button>
                <button
                  style={{ background: '#ef4444', border: 'none', color: '#fff', borderRadius: 6, padding: '6px 16px', fontWeight: 600, cursor: 'pointer' }}
                  onClick={() => handleDisconnect(disconnecting)}
                >
                  Disconnect
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
