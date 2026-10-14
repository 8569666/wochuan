import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import ArchiveEditor from '../components/ArchiveEditor.vue'
import { apiRequest } from '../api/client'
import { createMemoryHistory, createRouter } from 'vue-router'
import ArchiveTable from '../components/ArchiveTable.vue'

vi.mock('../api/client',()=>({apiRequest:vi.fn(),allOptions:vi.fn().mockResolvedValue([])}))
let wrapper: ReturnType<typeof mount>|undefined
beforeEach(()=>{vi.clearAllMocks();vi.stubGlobal('ResizeObserver',class {observe(){}unobserve(){}disconnect(){}})})
afterEach(()=>{wrapper?.unmount();document.body.innerHTML='';vi.unstubAllGlobals()})
async function openEditor(){
  wrapper=mount(ArchiveEditor,{props:{modelValue:false,record:null,path:'/stores',label:'门店',fields:[{key:'code',label:'门店编码',required:true},{key:'name',label:'门店名称',required:true}]},global:{plugins:[ElementPlus],stubs:{teleport:true}},attachTo:document.body})
  await wrapper.setProps({modelValue:true});await flushPromises()
  await wrapper.get('#archive-code').setValue('S1');await wrapper.get('#archive-name').setValue('测试门店')
  return wrapper
}
it('retains fields and displays inline failure after rejected save',async()=>{
  vi.mocked(apiRequest).mockRejectedValue(new Error('编码重复，请检查后重试'))
  const editor=await openEditor()
  const button=editor.findAll('button').find(b=>b.text()==='保存档案')!
  await button.trigger('click');await flushPromises()
  expect(editor.get('[role="alert"]').text()).toContain('编码重复')
  expect((editor.get('#archive-name').element as HTMLInputElement).value).toBe('测试门店')
  expect(editor.emitted('saved')).toBeUndefined()
})
it('prevents duplicate submit while the first save is pending',async()=>{
  let finish:((value:unknown)=>void)|undefined
  vi.mocked(apiRequest).mockImplementation(()=>new Promise(resolve=>{finish=resolve}))
  const editor=await openEditor();const button=editor.findAll('button').find(b=>b.text()==='保存档案')!
  await button.trigger('click');await flushPromises();await button.trigger('click');await flushPromises()
  expect(apiRequest).toHaveBeenCalledTimes(1)
  finish?.({});await flushPromises();expect(editor.emitted('saved')).toHaveLength(1)
})

it('exposes a keyboard accessible clear-search button',async()=>{
  vi.mocked(apiRequest).mockResolvedValue({items:[],total:0,page:1,page_size:20})
  const router=createRouter({history:createMemoryHistory(),routes:[{path:'/stores',component:ArchiveTable}]})
  await router.push('/stores');await router.isReady()
  wrapper=mount(ArchiveTable,{props:{path:'/stores',title:'门店管理',label:'门店',description:'门店',fields:[],columns:[]},global:{plugins:[ElementPlus,router]}})
  await flushPromises();await wrapper.get('input[aria-label="搜索编码或名称"]').setValue('ABC')
  const clear=wrapper.get('button[aria-label="清除搜索"]');await clear.trigger('click');await flushPromises()
  expect((wrapper.get('input[aria-label="搜索编码或名称"]').element as HTMLInputElement).value).toBe('')
})
