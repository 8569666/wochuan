import { afterEach,expect,it,vi } from 'vitest'
import { defineComponent } from 'vue'
import { createPinia,setActivePinia } from 'pinia'
import { mount,flushPromises } from '@vue/test-utils'
import { createMemoryHistory,createRouter } from 'vue-router'
import ElementPlus, { ElMessageBox } from 'element-plus'
import { useAuthStore } from '../stores/auth'
import PeopleView from '../views/PeopleView.vue'
import MyProfileView from '../views/MyProfileView.vue'
import EmployeeProfile from '../components/EmployeeProfile.vue'
import { apiRequest,allOptions } from '../api/client'
vi.mock('../api/client',()=>({apiRequest:vi.fn(),allOptions:vi.fn()}))
let wrapper:ReturnType<typeof mount>|undefined
afterEach(()=>{wrapper?.unmount();vi.clearAllMocks();vi.unstubAllGlobals();document.body.innerHTML=''})
async function open(admin=false){
  vi.stubGlobal('ResizeObserver',class{observe(){}unobserve(){}disconnect(){}})
  const pinia=createPinia();setActivePinia(pinia);useAuthStore().user={id:1,username:'test',display_name:'测试',role:admin?'ADMIN':'STAFF',permissions:['employee.read'],global_permissions:[]}
  vi.mocked(allOptions).mockResolvedValue([])
  vi.mocked(apiRequest).mockImplementation(async path=>path==='/people/permissions'?{permissions:[{code:'employee.read',name:'查看员工',group:'人员'}],scope_types:[]} as never:{items:[{id:1,code:'E1',name:'小王',status:'ACTIVE'}],total:1,page:1,page_size:20} as never)
  const router=createRouter({history:createMemoryHistory(),routes:[{path:'/people/:section',component:PeopleView}]});await router.push('/people/employees');await router.isReady()
  wrapper=mount(PeopleView,{global:{plugins:[pinia,ElementPlus,router],stubs:{teleport:true,ElSelect:defineComponent({props:['modelValue'],template:'<select><slot/></select>'}),ElOption:{props:['label'],template:'<option>{{label}}</option>'},ElTable:defineComponent({props:['data'],template:'<div><span v-for="row in data" :key="row.id">{{row.name}}</span><slot/></div>'}),ElTableColumn:{template:'<span />'}}},attachTo:document.body});await flushPromises();return wrapper
}
it('read-only employees can browse but cannot create, edit or configure accounts',async()=>{
  const view=await open()
  expect(view.text()).toContain('小王')
  expect(view.text()).not.toContain('新建员工')
  expect(view.findAll('button').some(button=>button.text()==='编辑')).toBe(false)
  expect(view.text()).not.toContain('绑定账号')
})
it('non-admin employee details do not imply an absent account is unbound',async()=>{
  const view=await open()
  const vm=view.vm as unknown as {detail:Record<string,unknown>;detailOpen:boolean}
  vm.detail={id:1,code:'E1',name:'小王',status:'ACTIVE',personnel_type:'EMPLOYEE'};vm.detailOpen=true
  await flushPromises()
  expect(view.findComponent(EmployeeProfile).exists()).toBe(true)
  expect(view.text()).not.toContain('登录账号')
  expect(view.text()).not.toContain('尚未绑定账号')
})
it('preserves employee inputs and shows inline server validation on create failure',async()=>{
  const view=await open(true)
  await view.findAll('button').find(button=>button.text()==='新建员工')!.trigger('click');await flushPromises()
  await view.get('#people-code').setValue('E2');await view.get('#people-name').setValue('小李')
  const vm=view.vm as unknown as {form:{org_unit_id:number;position_id:number}}
  vm.form.org_unit_id=1;vm.form.position_id=2
  vi.mocked(apiRequest).mockRejectedValue(new Error('工号已存在'))
  await view.findAll('button').find(button=>button.text()==='保存')!.trigger('click');await flushPromises()
  expect(view.get('[role="alert"]').text()).toContain('工号已存在')
  expect((view.get('#people-name').element as HTMLInputElement).value).toBe('小李')
})
it('my profile displays an actionable failure instead of an empty employee',async()=>{
  vi.mocked(apiRequest).mockRejectedValue(new Error('当前账号尚未关联员工档案'))
  wrapper=mount(MyProfileView,{global:{plugins:[ElementPlus]}});await flushPromises()
  expect(wrapper.get('[role="alert"]').text()).toContain('尚未关联')
  expect(wrapper.text()).toContain('重试')
})
it('onboarding submits no assignment fields while transfer retains them',async()=>{
  const view=await open(true)
  vi.spyOn(ElMessageBox,'confirm').mockResolvedValue('confirm' as never)
  const vm=view.vm as unknown as {detail:Record<string,unknown>;form:Record<string,unknown>;event:()=>void;save:()=>Promise<void>}
  vm.detail={id:1,status:'PENDING',org_unit_id:2,position_id:3,manager_id:4}
  vm.event();vm.form.kind='ONBOARD';vm.form.reason='办理入职'
  await vm.save();await flushPromises()
  const call=vi.mocked(apiRequest).mock.calls.find(([path,options])=>path==='/people/employees/1/events'&&options?.method==='POST')!
  const body=JSON.parse(String(call[1]?.body))
  expect(body).not.toHaveProperty('org_unit_id');expect(body).not.toHaveProperty('position_id');expect(body).not.toHaveProperty('manager_id')
  vi.mocked(apiRequest).mockClear()
  vm.detail={id:1,status:'ACTIVE',org_unit_id:2,position_id:3,manager_id:4}
  vm.event();vm.form.reason='调往新岗位';vm.form.manager_id=null
  await vm.save();await flushPromises()
  const transfer=vi.mocked(apiRequest).mock.calls.find(([path,options])=>path==='/people/employees/1/events'&&options?.method==='POST')!
  expect(JSON.parse(String(transfer[1]?.body))).toMatchObject({org_unit_id:2,position_id:3,manager_id:null})
})
it('grant editing clones only write fields and PUT strips response metadata',async()=>{
  const view=await open(true)
  vi.spyOn(ElMessageBox,'confirm').mockResolvedValue('confirm' as never)
  const original={id:20,user_id:5,role_id:3,role_name:'店长',scope_type:'STORES',scope_ids:[7]}
  const vm=view.vm as unknown as {detail:Record<string,unknown>;form:{grants:Record<string,any>[]};grants:()=>void;save:()=>Promise<void>}
  vm.detail={id:1,status:'ACTIVE',account:{id:5,grants:[original]}}
  vm.grants()
  expect(vm.form.grants).toEqual([{role_id:3,scope_type:'STORES',scope_ids:[7]}])
  vm.form.grants[0]!.scope_ids.push(8)
  expect(original.scope_ids).toEqual([7])
  vm.form.grants[0]!.id=20
  await vm.save();await flushPromises()
  const call=vi.mocked(apiRequest).mock.calls.find(([path,options])=>path==='/people/accounts/5/grants'&&options?.method==='PUT')!
  expect(JSON.parse(String(call[1]?.body))).toEqual({grants:[{role_id:3,scope_type:'STORES',scope_ids:[7,8]}]})
})
