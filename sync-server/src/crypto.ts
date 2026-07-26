import { pbkdf2Sync, randomBytes } from 'crypto'

export function hashInviteKey(inviteKey: str): string {
  const clean = inviteKey.trim().upper().replace(/-/g, '')
  const salt = 'orghumans-invite-salt'
  return pbkdf2Sync(clean, salt, 10000, 32, 'sha256').toString('hex')
}
