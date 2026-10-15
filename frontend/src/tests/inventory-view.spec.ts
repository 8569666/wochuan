import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import ElementPlus, { ElDialog } from 'element-plus'
import InventoryView from '../views/InventoryView.vue'
import { apiRequest,allOptions } from '../api/client'
import { createPinia,setActivePinia } from 'pinia'
import { useAuthStore } from '../stores/auth'
vi.mock('../api/client',()=>({apiRequest:vi.fn(),allOptions:vi.fn().mockResolvedValue([])}))
beforeEach(()=>{vi.stubGlobal('ResizeObserver',class{observe(){}unobserve(){}disconnect(){}})})
afterEach(()=>{vi.clearAllMocks();vi.unstubAllGlobals()})
it('inventory reader without warehouse-read sees report without unauthorized option fetch',async()=>{
  const pinia=createPinia();setActivePinia(pinia);useAuthStore().user={id:2,username:'reader',display_name:'库存员',role:'STAFF',permissions:['inventory.read'],global_permissions:[]}
  vi.mocked(apiRequest).mockResolvedValue({items:[],total:0,page:1,page_size:20})
  vi.mocked(allOptions).mockRejectedValue(new Error('没有仓库读取权限'))
  const router=createRouter({history:createMemoryHistory(),routes:[{path:'/inventory',component:InventoryView}]});await router.push('/inventory');await router.isReady()
  const view=mount(InventoryView,{props:{mode:'inventory'},global:{plugins:[pinia,ElementPlus,router]}});await flushPromises()
  expect(allOptions).not.toHaveBeenCalled()
  expect(view.find('[role="alert"]').exists()).toBe(false)
  expect(view.text()).toContain('暂无库存记录')
  view.unmount();vi.mocked(allOptions).mockResolvedValue([])
})
it('shows read failure instead of claiming stock is empty',async()=>{
  vi.mocked(apiRequest).mockRejectedValue(new Error('数据库暂时不可用'))
  const router=createRouter({history:createMemoryHistory(),routes:[{path:'/inventory',component:InventoryView}]});await router.push('/inventory');await router.isReady()
  const wrapper=mount(InventoryView,{props:{mode:'inventory'},global:{plugins:[ElementPlus,router]}});await flushPromises()
  expect(wrapper.get('[role="alert"]').text()).toContain('数据库暂时不可用')
  expect(wrapper.text()).not.toContain('暂无库存记录')
  wrapper.unmount()
})
it.each(['success','error'])('ignores an old receipt detail %s after another receipt is opened',async outcome=>{
  let finishA:((value:unknown)=>void)|undefined,rejectA:((reason:Error)=>void)|undefined,finishB:((value:unknown)=>void)|undefined
  vi.mocked(apiRequest).mockImplementation(async path=>{
    if(path==='/purchase-receipts/1')return await new Promise<unknown>((resolve,reject)=>{finishA=resolve;rejectA=reject}) as never
    if(path==='/purchase-receipts/2')return await new Promise<unknown>(resolve=>{finishB=resolve}) as never
    return {items:[{id:1,product_id:1,number:'A'},{id:2,product_id:2,number:'B'}],total:2,page:1,page_size:20} as never
  })
  const router=createRouter({history:createMemoryHistory(),routes:[{path:'/purchase-receipts',component:InventoryView}]});await router.push('/purchase-receipts');await router.isReady()
  const wrapper=mount(InventoryView,{props:{mode:'receipts'},global:{plugins:[ElementPlus,router],stubs:{teleport:true,ElSelect:true,ElPagination:true}}});await flushPromises()
  const buttons=wrapper.findAll('button').filter(button=>button.text()==='查看明细')
  await buttons[0]!.trigger('click');await flushPromises()
  wrapper.findComponent(ElDialog).vm.$emit('update:modelValue',false);await flushPromises()
  await buttons[1]!.trigger('click');await flushPromises()
  finishB?.({number:'CURRENT-B',lines:[],total_quantity:2});await flushPromises()
  if(outcome==='success')finishA?.({number:'STALE-A',lines:[],total_quantity:1});else rejectA?.(new Error('STALE-A-ERROR'))
  await flushPromises()
  expect(wrapper.findComponent(ElDialog).text()).toContain('CURRENT-B')
  expect(wrapper.findComponent(ElDialog).text()).not.toContain('STALE-A')
  wrapper.unmount()
})
