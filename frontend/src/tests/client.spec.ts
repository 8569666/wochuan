import { afterEach, describe, expect, it, vi } from 'vitest'
import { apiRequest } from '../api/client'

afterEach(() => vi.unstubAllGlobals())
describe('request outcomes', () => {
  it('returns real response data', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({code:200,data:{total:3}}))))
    expect(await apiRequest('/stores')).toEqual({total:3})
  })
  it('does not turn server failure into empty data', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({message:'数据库暂时不可用'}), {status:503})))
    await expect(apiRequest('/stores')).rejects.toThrow('数据库暂时不可用')
  })
  it('announces expired sessions', async () => {
    const listener = vi.fn(); window.addEventListener('werp:unauthorized', listener)
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({message:'请先登录'}), {status:401})))
    await expect(apiRequest('/stores')).rejects.toThrow('请先登录')
    expect(listener).toHaveBeenCalledOnce(); window.removeEventListener('werp:unauthorized', listener)
  })
  it('keeps editable page in place when a write requires reauthentication', async () => {
    const listener=vi.fn();window.addEventListener('werp:unauthorized',listener)
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response(JSON.stringify({message:'请先登录'}),{status:401})))
    await expect(apiRequest('/stores',{method:'POST',body:'{}'})).rejects.toThrow('请先登录')
    expect(listener).not.toHaveBeenCalled();window.removeEventListener('werp:unauthorized',listener)
  })
})
