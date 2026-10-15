import { createPinia,setActivePinia } from 'pinia'
import { useAuthStore } from '../stores/auth'
import { afterEach, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import ElementPlus from 'element-plus'
import { defineComponent } from 'vue'
import ProductEditor from '../views/ProductEditorView.vue'
import ChoiceList from '../components/ChoiceList.vue'
import { allOptions, apiRequest } from '../api/client'
vi.mock('../api/client',()=>({apiRequest:vi.fn(),allOptions:vi.fn()}))
const categories=[{id:1,code:'DRESS',name:'裙装',status:'ACTIVE',last_fabric_id:2}]
const fabrics=[{id:1,code:'C',name:'棉',composition:'100%棉',status:'ACTIVE'},{id:2,code:'W',name:'羊毛',composition:'100%羊毛',status:'ACTIVE'}]
const colors=[{id:1,code:'RED',name:'红色',status:'ACTIVE'},{id:2,code:'BLUE',name:'蓝色',status:'ACTIVE'}]
const sizes=[{id:1,code:'S',name:'S',status:'ACTIVE'},{id:2,code:'M',name:'M',status:'ACTIVE'}]
const product={id:1,code:'P1',name:'测试商品',category:'裙装',category_id:1,fabric_id:1,fabric_composition:'100%棉',year:2026,season:'春夏',tag_price:'99.00',size_group_id:1,skus:sizes.map(size=>({id:size.id,color_id:1,size_id:size.id,retail_price:'88.00',barcode:`P1-RED-${size.code}`,code:`P1-RED-${size.code}`,color:colors[0],size}))}
// Exercise form state here; actual Element Plus selects are covered in browser QA.
const SelectStub=defineComponent({name:'ElSelect',props:['modelValue','id'],emits:['update:modelValue'],template:'<select :id="id" :value="modelValue"><slot /></select>'})
let wrapper:ReturnType<typeof mount>|undefined
afterEach(()=>{wrapper?.unmount();vi.clearAllMocks();vi.unstubAllGlobals();document.body.innerHTML=''})
async function open(editing=false,staff=false,receivingOptions=true){
  setActivePinia(createPinia());useAuthStore().user=staff?{id:2,username:'receiver',display_name:'收货员',role:'STAFF',permissions:['catalog.read','purchase.receive',...(receivingOptions?['supplier.read','warehouse.read']:[])],global_permissions:[]}:{id:1,username:'admin',display_name:'管理员',role:'ADMIN'}
  vi.stubGlobal('ResizeObserver',class{observe(){}unobserve(){}disconnect(){}})
  vi.mocked(allOptions).mockImplementation(async path=>({'/categories':categories,'/fabrics':fabrics,'/colors':colors,'/size-groups':[{id:1,code:'STD',name:'标准尺码',status:'ACTIVE',sizes}]}[path]||[]) as never)
  vi.mocked(apiRequest).mockImplementation(async(path,options)=>{if(options?.method)return product as never;if(path==='/products/1')return product as never;return {ids:[1,2]} as never})
  const router=createRouter({history:createMemoryHistory(),routes:[{path:'/products',component:{template:'<div>列表</div>'}},{path:'/products/new',component:ProductEditor},{path:'/products/:id',component:ProductEditor},...['categories','fabrics','colors','size-groups'].map(path=>({path:`/${path}`,component:{template:'<div />'}}))]})
  await router.push(editing?'/products/1':'/products/new');await router.isReady()
  wrapper=mount({template:'<router-view />'},{global:{plugins:[ElementPlus,router],stubs:{teleport:true,ElSelect:SelectStub,ElOption:{props:['value','label'],template:'<option :value="value">{{label}}</option>'}}},attachTo:document.body});await flushPromises();return wrapper
}
it('uses the category shared default after selection and keeps existing product fabric on load',async()=>{
  const editor=await open(true)
  const selects=editor.findAllComponents({name:'ElSelect'})
  expect(selects.find(select=>select.attributes('id')==='product-fabric')?.props('modelValue')).toBe(1)
  selects.find(select=>select.attributes('id')==='product-category')!.vm.$emit('update:modelValue',1)
  await flushPromises()
  expect(selects.find(select=>select.attributes('id')==='product-fabric')?.props('modelValue')).toBe(2)
  expect(editor.text()).toContain('100%羊毛')
})
it('allows receiver quantities while keeping all product prices read only and sends receiving only',async()=>{
  const editor=await open(true,true)
  expect(editor.get('#price-1-1').attributes('readonly')).toBeDefined()
  expect(editor.find('#product-purchase-price').exists()).toBe(false)
  await editor.get('input[aria-label="红色S进货数量"]').setValue('2')
  const vm=editor.findComponent(ProductEditor).vm as unknown as {receiving:{supplier_id:number;warehouse_id:number;unit_cost:string}}
  vm.receiving.supplier_id=1;vm.receiving.warehouse_id=2;vm.receiving.unit_cost='10.00'
  await editor.findAll('button').find(button=>button.text()==='保存商品')!.trigger('click');await flushPromises()
  const call=vi.mocked(apiRequest).mock.calls.find(([,options])=>options?.method==='PATCH')!
  expect(Object.keys(JSON.parse(String(call[1]?.body)))).toEqual(['receiving'])
})
it('catalog writer without cost permission omits purchase price from product PATCH',async()=>{
  const editor=await open(true,true)
  useAuthStore().user={id:2,username:'writer',display_name:'商品员',role:'STAFF',permissions:['catalog.read','catalog.write'],global_permissions:['catalog.write']}
  await flushPromises()
  expect(editor.find('#product-purchase-price').exists()).toBe(false)
  await editor.findAll('button').find(button=>button.text()==='保存商品')!.trigger('click');await flushPromises()
  const call=vi.mocked(apiRequest).mock.calls.find(([,options])=>options?.method==='PATCH')!
  expect(call).toBeDefined()
  expect(JSON.parse(String(call[1]?.body))).not.toHaveProperty('purchase_base_price')
})
it('receiver missing option-read rights sees an explanation without forbidden option requests',async()=>{
  const editor=await open(true,true,false)
  expect(editor.text()).toContain('采购进货需要供应商读取与仓库读取权限')
  expect(vi.mocked(allOptions).mock.calls.some(([path])=>path==='/suppliers'||path==='/warehouses')).toBe(false)
})
it('adds new color cells and submits only additions while preserving old sku identities',async()=>{
  const editor=await open(true)
  const colorList=editor.findAllComponents(ChoiceList).find(list=>list.props('kind')==='colors')!
  colorList.vm.$emit('update:modelValue',[1,2]);await flushPromises()
  expect(editor.findAll('.matrix-cell')).toHaveLength(4)
  expect(editor.get('#barcode-1-1').attributes('readonly')).toBeDefined()
  expect(editor.get('#barcode-2-1').attributes('readonly')).toBeUndefined()
  await editor.findAll('button').find(button=>button.text()==='保存商品')!.trigger('click');await flushPromises()
  const call=vi.mocked(apiRequest).mock.calls.find(([,options])=>options?.method==='PATCH')!
  const body=JSON.parse(String(call[1]?.body))
  expect(body.new_skus).toHaveLength(2)
  expect(body.new_skus.every((sku:{color_id:number})=>sku.color_id===2)).toBe(true)
  expect(body.sku_prices).toEqual([{id:1,retail_price:'88.00'},{id:2,retail_price:'88.00'}])
})
it('refreshes changed size definitions without losing draft values',async()=>{
  const editor=await open(false)
  const lists=editor.findAllComponents(ChoiceList)
  lists.find(list=>list.props('kind')==='colors')!.vm.$emit('update:modelValue',[1])
  lists.find(list=>list.props('kind')==='size-groups')!.vm.$emit('update:modelValue',[1])
  await flushPromises()
  await editor.get('#product-name').setValue('保留款名')
  await editor.get('#price-1-1').setValue('123.00')
  await editor.get('#barcode-1-1').setValue('CUSTOM-BARCODE')
  const original=vi.mocked(allOptions).getMockImplementation()!
  vi.mocked(allOptions).mockImplementation(async path=>path==='/size-groups'?[{id:1,code:'STD',name:'标准尺码',status:'ACTIVE',sizes:[...sizes,{id:3,code:'L',name:'L',status:'ACTIVE'}]}] as never:original(path))
  await editor.findAll('button').find(button=>button.text()==='刷新字典')!.trigger('click');await flushPromises()
  expect(editor.findAll('tbody tr')).toHaveLength(3)
  expect((editor.get('#price-1-1').element as HTMLInputElement).value).toBe('123.00')
  expect((editor.get('#barcode-1-1').element as HTMLInputElement).value).toBe('CUSTOM-BARCODE')
  expect((editor.get('#product-name').element as HTMLInputElement).value).toBe('保留款名')
})
it('requires purchase fields after quantity entry then sends one atomic receiving payload',async()=>{
  const editor=await open(true)
  await editor.get('input[aria-label="红色S进货数量"]').setValue('10')
  const save=editor.findAll('button').find(button=>button.text()==='保存商品')!
  await save.trigger('click');await flushPromises()
  expect(editor.get('[role="alert"]').text()).toContain('供应商')
  expect(vi.mocked(apiRequest).mock.calls.some(([,options])=>options?.method==='PATCH')).toBe(false)
  const selects=editor.findAllComponents({name:'ElSelect'})
  selects.find(select=>select.attributes('id')==='receiving-supplier')!.vm.$emit('update:modelValue',1)
  selects.find(select=>select.attributes('id')==='receiving-warehouse')!.vm.$emit('update:modelValue',2)
  await editor.get('#receiving-cost').setValue('100.00')
  await save.trigger('click');await flushPromises()
  const call=vi.mocked(apiRequest).mock.calls.find(([,options])=>options?.method==='PATCH')!
  const body=JSON.parse(String(call[1]?.body))
  expect(body.receiving.quantities).toEqual([{color_id:1,size_id:1,quantity:10}])
  expect(body.receiving.unit_cost).toBe('100.00')
  expect(body.receiving.supplier_id).toBe(1)
  expect(body.receiving.warehouse_id).toBe(2)
})
