import type { ApiResponse, Archive, Page } from './types'

export class ApiError extends Error { constructor(message: string, public status: number) { super(message) } }
export async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  let response: Response
  try {
    response = await fetch(`/api/v1${path}`, {credentials:'same-origin', ...options, headers:{'Content-Type':'application/json', ...options.headers}})
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error
    throw new ApiError('无法连接服务，请检查后台是否启动后重试', 0)
  }
  const body = await response.json().catch(() => ({message:'服务返回异常，请稍后重试'})) as ApiResponse<T>
  if (!response.ok) {
    if (response.status === 401 && (options.method||'GET').toUpperCase()==='GET') window.dispatchEvent(new Event('werp:unauthorized'))
    throw new ApiError(body.message || '操作失败，请稍后重试', response.status)
  }
  return body.data
}
export async function allOptions<T extends Archive>(path: string): Promise<T[]> {
  const result: T[] = []
  let page = 1
  while (true) {
    const data = await apiRequest<Page<T>>(`${path}?page=${page}&page_size=100&status=ACTIVE`)
    result.push(...data.items)
    if (result.length >= data.total) return result
    page++
  }
}
