import { afterEach, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import ChoiceList from '../components/ChoiceList.vue'
import { apiRequest } from '../api/client'

vi.mock('../api/client',()=>({apiRequest:vi.fn()}))
const items=Array.from({length:12},(_,i)=>({id:i+1,code:`C${i+1}`,name:`颜色${i+1}`,status:'ACTIVE' as const}))
let wrapper:ReturnType<typeof mount>|undefined
afterEach(()=>{wrapper?.unmount();vi.clearAllMocks();document.body.innerHTML=''})
it('renders ten common colors as buttons and protects existing selections',async()=>{
  wrapper=mount(ChoiceList,{props:{label:'颜色',kind:'colors',items,commonIds:items.slice(0,10).map(i=>i.id),modelValue:[1],lockedIds:[1],multiple:true},global:{plugins:[ElementPlus],stubs:{teleport:true}}})
  expect(wrapper.findAll('.choice-item')).toHaveLength(10)
  expect(wrapper.get('button[aria-label="颜色1"]').attributes('disabled')).toBeDefined()
  await wrapper.get('button[aria-label="颜色2"]').trigger('click')
  expect(wrapper.emitted('update:modelValue')?.[0]?.[0]).toEqual([1,2])
  expect(wrapper.find('select').exists()).toBe(false)
})
it('failed common-list save preserves edits and displays the error',async()=>{
  vi.mocked(apiRequest).mockRejectedValue(new Error('保存失败'))
  wrapper=mount(ChoiceList,{props:{label:'颜色',kind:'colors',items,commonIds:[1],modelValue:[],multiple:true},global:{plugins:[ElementPlus],stubs:{teleport:true}}})
  await wrapper.get('button[aria-label="编辑常用颜色"]').trigger('click');await flushPromises()
  await wrapper.get('button[aria-label="常用颜色2"]').trigger('click')
  await wrapper.get('button[aria-label="保存常用颜色"]').trigger('click');await flushPromises()
  expect(wrapper.get('[role="alert"]').text()).toContain('保存失败')
  expect(wrapper.get('button[aria-label="常用颜色2"]').attributes('aria-pressed')).toBe('true')
})
