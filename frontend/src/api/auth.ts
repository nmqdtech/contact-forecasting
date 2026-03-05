import client from './client'

export interface UserOut {
  id: string
  username: string
  email: string
  is_admin: boolean
  is_active: boolean
  must_change_password: boolean
  totp_enabled: boolean
  created_at: string
}

export interface LoginSuccess {
  access_token: string
  token_type: string
}

export interface LoginTwoFactor {
  requires_2fa: true
  temp_token: string
}

export type LoginResponse = LoginSuccess | LoginTwoFactor

export async function login(username: string, password: string): Promise<LoginResponse> {
  const form = new URLSearchParams({ username, password })
  const res = await client.post<LoginResponse>('/auth/login', form, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  })
  return res.data
}

export async function verifyTotp(tempToken: string, code: string): Promise<LoginSuccess> {
  const res = await client.post<LoginSuccess>('/auth/totp', {
    temp_token: tempToken,
    code,
  })
  return res.data
}

export async function getMe(): Promise<UserOut> {
  const res = await client.get<UserOut>('/auth/me')
  return res.data
}

export async function listUsers(): Promise<UserOut[]> {
  const res = await client.get<UserOut[]>('/auth/users')
  return res.data
}

export async function createUser(body: {
  username: string
  email: string
  password: string
  is_admin: boolean
}): Promise<UserOut> {
  const res = await client.post<UserOut>('/auth/users', body)
  return res.data
}

export async function updateUser(
  id: string,
  body: { is_active?: boolean; is_admin?: boolean }
): Promise<UserOut> {
  const res = await client.patch<UserOut>(`/auth/users/${id}`, body)
  return res.data
}

export async function deleteUser(id: string): Promise<void> {
  await client.delete(`/auth/users/${id}`)
}

export async function changePassword(currentPassword: string, newPassword: string): Promise<void> {
  await client.post('/auth/me/password', {
    current_password: currentPassword,
    new_password: newPassword,
  })
}

export interface TotpSetupResponse {
  secret: string
  otpauth_url: string
}

export async function setupTotp(): Promise<TotpSetupResponse> {
  const res = await client.post<TotpSetupResponse>('/auth/me/totp/setup')
  return res.data
}

export async function enableTotp(code: string): Promise<void> {
  await client.post('/auth/me/totp/enable', { code })
}

export async function disableTotp(): Promise<void> {
  await client.post('/auth/me/totp/disable')
}
