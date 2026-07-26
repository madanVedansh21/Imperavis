import { useState } from 'react'

export function JoinOrgDialog({ open, onClose, onJoined }: { open: boolean; onClose: () => void; onJoined?: () => void }) {
  const [inviteKey, setInviteKey] = useState('')
  const [username, setUsername] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [joined, setJoined] = useState<{ name: string; role: string } | null>(null)

  if (!open) return null

  const handleJoin = async () => {
    if (!inviteKey.trim() || !username.trim()) return
    setLoading(true)
    setError('')
    try {
      const res = await window.hermesDesktop?.orghumans?.joinOrg({
        inviteKey: inviteKey.trim(),
        username: username.trim(),
      })
      if (res?.ok && res.joined) {
        setJoined({ name: res.joined.name, role: res.joined.role })
        if (onJoined) onJoined()
      } else {
        setError(res?.error || 'Invalid invite key')
      }
    } catch (err) {
      setError(String(err))
    } finally {
      setLoading(false)
    }
  }

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
          width: 420,
          background: '#0d0d12',
          border: '1px solid rgba(124, 107, 255, 0.3)',
          borderRadius: 16,
          padding: 28,
          color: '#e8e6ff',
          boxShadow: '0 20px 50px rgba(0, 0, 0, 0.8), 0 0 30px rgba(124, 107, 255, 0.15)',
        }}
        onClick={e => e.stopPropagation()}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 20 }}>
          <h2 style={{ margin: 0, fontSize: 18, fontWeight: 600 }}>
            {joined ? `Joined ${joined.name}!` : 'Join an Organisation'}
          </h2>
          <button style={{ background: 'none', border: 'none', color: '#9590b8', cursor: 'pointer' }} onClick={onClose}>
            ✕
          </button>
        </div>

        {!joined ? (
          <div>
            <div style={{ marginBottom: 14 }}>
              <label style={{ display: 'block', fontSize: 12, color: '#9590b8', marginBottom: 4 }}>Invite Key</label>
              <input
                style={{
                  width: '100%',
                  fontFamily: 'monospace',
                  background: 'rgba(255,255,255,0.05)',
                  border: '1px solid rgba(255,255,255,0.1)',
                  borderRadius: 8,
                  padding: '8px 12px',
                  color: '#fff',
                  fontSize: 13,
                  letterSpacing: 1,
                }}
                placeholder="XXXX-XXXX-XXXX"
                value={inviteKey}
                onChange={e => setInviteKey(e.target.value.toUpperCase())}
              />
            </div>

            <div style={{ marginBottom: 20 }}>
              <label style={{ display: 'block', fontSize: 12, color: '#9590b8', marginBottom: 4 }}>Choose Your Handle (@username)</label>
              <input
                style={{
                  width: '100%',
                  background: 'rgba(255,255,255,0.05)',
                  border: '1px solid rgba(255,255,255,0.1)',
                  borderRadius: 8,
                  padding: '8px 12px',
                  color: '#fff',
                  fontSize: 13,
                }}
                placeholder="e.g. jordan"
                value={username}
                onChange={e => setUsername(e.target.value)}
              />
            </div>

            {error && <div style={{ color: '#f87171', fontSize: 12, marginBottom: 12 }}>{error}</div>}

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
              <button style={{ background: 'transparent', border: 'none', color: '#9590b8', cursor: 'pointer', padding: '6px 14px' }} onClick={onClose}>
                Cancel
              </button>
              <button
                style={{ background: '#7c6bff', border: 'none', color: '#fff', borderRadius: 6, padding: '6px 16px', fontWeight: 600, cursor: 'pointer' }}
                disabled={!inviteKey.trim() || !username.trim() || loading}
                onClick={handleJoin}
              >
                {loading ? 'Joining...' : 'Join Organisation →'}
              </button>
            </div>
          </div>
        ) : (
          <div style={{ textAlign: 'center', padding: '10px 0' }}>
            <div style={{ fontSize: 36, marginBottom: 12 }}>🏢</div>
            <p style={{ margin: '0 0 20px', color: '#9590b8' }}>
              Joined <strong>{joined.name}</strong> as a <strong>{joined.role}</strong>.
            </p>
            <button
              style={{ background: '#7c6bff', border: 'none', color: '#fff', borderRadius: 6, padding: '8px 20px', fontWeight: 600, cursor: 'pointer' }}
              onClick={onClose}
            >
              Enter Workspace →
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
