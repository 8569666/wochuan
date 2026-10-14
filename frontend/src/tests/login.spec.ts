import { afterEach, expect, it, vi } from 'vitest'
import { createPinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import LoginView from '../views/LoginView.vue'

vi.mock('../api/client',()=>({apiRequest:vi.fn().mockRejectedValue(new Error('用户名或密码不正确'))}))
afterEach(()=>{document.body.innerHTML='';vi.unstubAllGlobals()})
it('shows login error without clearing entered credentials',async()=>{
  const router=createRouter({history:createMemoryHistory(),routes:[{path:'/login',component:LoginView}]});await router.push('/login');await router.isReady()
  const wrapper=mount(LoginView,{global:{plugins:[createPinia(),ElementPlus,router]},attachTo:document.body})
  await flushPromises()
  await wrapper.get('#login-username').setValue('admin');await wrapper.get('#login-password').setValue('WrongPassword')
  await wrapper.get('form').trigger('submit');await flushPromises()
  expect(wrapper.get('[role="alert"]').text()).toContain('用户名或密码不正确')
  expect((wrapper.get('#login-username').element as HTMLInputElement).value).toBe('admin')
  wrapper.unmount()
})
