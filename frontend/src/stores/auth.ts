import { defineStore } from 'pinia'
import { ref } from 'vue'
import { apiRequest } from '../api/client'
import type { User } from '../api/types'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User|null>(null)
  async function loadSession() { user.value = await apiRequest<User>('/auth/me'); return user.value }
  async function login(username:string,password:string) { user.value = await apiRequest<User>('/auth/login', {method:'POST',body:JSON.stringify({username,password})}) }
  async function logout() { await apiRequest('/auth/logout', {method:'POST'}); user.value = null }
  function clear() { user.value = null }
  return {user,loadSession,login,logout,clear}
})
