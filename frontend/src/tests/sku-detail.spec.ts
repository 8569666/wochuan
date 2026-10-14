import { expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import SkuDetail from '../components/SkuMatrix.vue'
it('renders one row per specification with the requested headers and emits receiving quantities',async()=>{
  const colors=[{id:1,code:'RED',name:'红色',status:'ACTIVE' as const}]
  const sizes=[{id:1,code:'S',name:'S',status:'ACTIVE' as const},{id:2,code:'M',name:'M',status:'ACTIVE' as const}]
  const cells=sizes.map(size=>({id:size.id,color_id:1,size_id:size.id,retail_price:'99.00',barcode:`P-RED-${size.code}`}))
  const wrapper=mount(SkuDetail,{props:{colors,sizes,modelValue:cells,productCode:'P',readonlyDimensions:true,allowReceiving:true},global:{plugins:[ElementPlus]}})
  expect(wrapper.findAll('thead th').map(th=>th.text())).toEqual(['颜色','码数','条码','零售价（元）','进货数量'])
  expect(wrapper.findAll('tbody tr')).toHaveLength(2)
  await wrapper.get('input[aria-label="红色S进货数量"]').setValue('12')
  const emitted=wrapper.emitted('update:modelValue')?.[0]?.[0] as {id:number;incoming_quantity:string}[]
  expect(emitted[0]?.incoming_quantity).toBe('12')
  expect(emitted[0]?.id).toBe(1)
  wrapper.unmount()
})
