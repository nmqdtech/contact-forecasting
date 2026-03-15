import client from './client'
import type { PasskeyOut } from '../types'

export const passkeyRegisterBegin = async (): Promise<{ options: object; challenge_token: string }> => {
  const { data } = await client.post('/auth/me/passkeys/register/begin')
  return data
}

export const passkeyRegisterComplete = async (body: {
  credential: object
  challenge_token: string
  name: string
}): Promise<PasskeyOut> => {
  const { data } = await client.post('/auth/me/passkeys/register/complete', body)
  return data
}

export const passkeyAuthBegin = async (): Promise<{ options: object; challenge_token: string }> => {
  const { data } = await client.post('/auth/passkeys/authenticate/begin')
  return data
}

export const passkeyAuthComplete = async (body: {
  credential: object
  challenge_token: string
}): Promise<{ access_token: string }> => {
  const { data } = await client.post('/auth/passkeys/authenticate/complete', body)
  return data
}

export const listPasskeys = async (): Promise<PasskeyOut[]> => {
  const { data } = await client.get('/auth/me/passkeys')
  return data
}

export const deletePasskey = async (id: string): Promise<void> => {
  await client.delete(`/auth/me/passkeys/${id}`)
}
