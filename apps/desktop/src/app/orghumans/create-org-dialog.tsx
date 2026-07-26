import { useState } from 'react'

const ORG_TYPES = ['Startup', 'Agency', 'Enterprise', 'Non-profit', 'Project Team']

export function CreateOrgDialog({ open, onClose, onCreated }: { open: boolean; onClose: () => void; onCreated?: () => void }) {
  const [step, setStep] = useState<1 | 2 | 3>(1)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [orgType, setOrgType] = useState('Startup')
  const [creatorUsername, setCreatorUsername] = useState('')
  const [brandDesc, setBrandDesc] = useState('')
  const [tone, setTone] = useState('')
  const [audience, setAudience] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [createdOrg, setCreatedOrg] = useState<{ invite_key: string; name: string } | null>(null)
  const [copied, setCopied] = useState(false)

  if (!open) return null

  const handleNext = async () => {
    if (step === 1) {
      setStep(2)
      return
    }
    if (step === 2) {
      setLoading(true)
      setError('')
      try {
        const res = await window.hermesDesktop?.orghumans?.createOrg({
          name: name.trim(),
          description: description.trim(),
          orgType,
          creatorUsername: creatorUsername.trim(),
          brandIdentity: {
            brand_description: brandDesc.trim(),
            tone: tone.trim(),
            target_audience: audience.trim(),
          },
        })

        if (res?.ok && res.org) {
          setCreatedOrg({ invite_key: res.org.invite_key, name: res.org.name })
          setStep(3)
          if (onCreated) onCreated()
        } else {
          setError(res?.error || 'Failed to create organisation')
        }
      } catch (err) {
        setError(String(err))
      } finally {
        setLoading(false)
      }
    }
  }

  const handleCopyKey = () => {
    if (createdOrg?.invite_key) {
      navigator.clipboard.writeText(createdOrg.invite_key)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
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
          width: 500,
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
            {step === 3 ? 'Organisation Created!' : 'Create Organisation'}
          </h2>
          <button style={{ background: 'none', border: 'none', color: '#9590b8', cursor: 'pointer' }} onClick={onClose}>
            ✕
          </button>
        </div>

        {step === 1 && (
          <div>
            <div style={{ marginBottom: 14 }}>
              <label style={{ display: 'block', fontSize: 12, color: '#9590b8', marginBottom: 4 }}>Org Name</label>
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
                placeholder="e.g. Acme Corp"
                value={name}
                onChange={e => setName(e.target.value)}
              />
            </div>

            <div style={{ marginBottom: 14 }}>
              <label style={{ display: 'block', fontSize: 12, color: '#9590b8', marginBottom: 4 }}>Description</label>
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
                placeholder="Brief summary"
                value={description}
                onChange={e => setDescription(e.target.value)}
              />
            </div>

            <div style={{ marginBottom: 14 }}>
              <label style={{ display: 'block', fontSize: 12, color: '#9590b8', marginBottom: 4 }}>Your Handle in Org (@username)</label>
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
                placeholder="e.g. alex"
                value={creatorUsername}
                onChange={e => setCreatorUsername(e.target.value)}
              />
            </div>

            <div style={{ marginBottom: 20 }}>
              <label style={{ display: 'block', fontSize: 12, color: '#9590b8', marginBottom: 6 }}>Org Type</label>
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                {ORG_TYPES.map(t => (
                  <button
                    key={t}
                    style={{
                      background: orgType === t ? 'rgba(124, 107, 255, 0.3)' : 'rgba(255,255,255,0.04)',
                      border: orgType === t ? '1px solid #7c6bff' : '1px solid rgba(255,255,255,0.1)',
                      color: orgType === t ? '#fff' : '#9590b8',
                      borderRadius: 6,
                      padding: '4px 10px',
                      fontSize: 12,
                      cursor: 'pointer',
                    }}
                    onClick={() => setOrgType(t)}
                  >
                    {t}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {step === 2 && (
          <div>
            <div style={{ marginBottom: 14 }}>
              <label style={{ display: 'block', fontSize: 12, color: '#9590b8', marginBottom: 4 }}>Brand Description (Optional)</label>
              <textarea
                style={{
                  width: '100%',
                  height: 60,
                  background: 'rgba(255,255,255,0.05)',
                  border: '1px solid rgba(255,255,255,0.1)',
                  borderRadius: 8,
                  padding: '8px 12px',
                  color: '#fff',
                  fontSize: 13,
                  resize: 'none',
                }}
                placeholder="What does your company do?"
                value={brandDesc}
                onChange={e => setBrandDesc(e.target.value)}
              />
            </div>

            <div style={{ marginBottom: 14 }}>
              <label style={{ display: 'block', fontSize: 12, color: '#9590b8', marginBottom: 4 }}>Brand Tone</label>
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
                placeholder="e.g. Professional, concise"
                value={tone}
                onChange={e => setTone(e.target.value)}
              />
            </div>

            <div style={{ marginBottom: 20 }}>
              <label style={{ display: 'block', fontSize: 12, color: '#9590b8', marginBottom: 4 }}>Target Audience</label>
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
                placeholder="e.g. B2B Software teams"
                value={audience}
                onChange={e => setAudience(e.target.value)}
              />
            </div>

            {error && <div style={{ color: '#f87171', fontSize: 12, marginBottom: 12 }}>{error}</div>}
          </div>
        )}

        {step === 3 && createdOrg && (
          <div style={{ textAlign: 'center', padding: '10px 0' }}>
            <p style={{ fontSize: 14, color: '#9590b8', margin: '0 0 16px' }}>
              Share this invite key with members to join <strong>{createdOrg.name}</strong>:
            </p>
            <div
              style={{
                fontFamily: 'monospace',
                fontSize: 22,
                letterSpacing: 2,
                color: '#7c6bff',
                background: 'rgba(124, 107, 255, 0.1)',
                border: '1px solid #7c6bff',
                borderRadius: 10,
                padding: '12px 20px',
                marginBottom: 16,
              }}
            >
              {createdOrg.invite_key}
            </div>
            <button
              style={{
                background: 'rgba(255,255,255,0.06)',
                border: '1px solid rgba(255,255,255,0.15)',
                color: '#fff',
                borderRadius: 6,
                padding: '6px 14px',
                fontSize: 12,
                cursor: 'pointer',
                marginBottom: 20,
              }}
              onClick={handleCopyKey}
            >
              {copied ? '✓ Copied!' : '📋 Copy Key'}
            </button>
          </div>
        )}

        {/* Actions */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
          {step < 3 && (
            <button
              style={{ background: 'transparent', border: 'none', color: '#9590b8', cursor: 'pointer', padding: '6px 14px' }}
              onClick={onClose}
            >
              Cancel
            </button>
          )}

          {step === 1 && (
            <button
              style={{ background: '#7c6bff', border: 'none', color: '#fff', borderRadius: 6, padding: '6px 16px', fontWeight: 600, cursor: 'pointer' }}
              disabled={!name.trim() || !creatorUsername.trim()}
              onClick={handleNext}
            >
              Continue →
            </button>
          )}

          {step === 2 && (
            <button
              style={{ background: '#7c6bff', border: 'none', color: '#fff', borderRadius: 6, padding: '6px 16px', fontWeight: 600, cursor: 'pointer' }}
              disabled={loading}
              onClick={handleNext}
            >
              {loading ? 'Creating...' : 'Create Org 🎉'}
            </button>
          )}

          {step === 3 && (
            <button
              style={{ background: '#7c6bff', border: 'none', color: '#fff', borderRadius: 6, padding: '6px 16px', fontWeight: 600, cursor: 'pointer' }}
              onClick={onClose}
            >
              Enter Workspace →
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
