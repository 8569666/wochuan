import { expect, it } from 'vitest'
import { buildReceiving } from '../components/receiving'
const cell={color_id:1,size_id:2,retail_price:'399.00'}
const details={supplier_id:1,warehouse_id:2,unit_cost:'100.00'}
it('does not create a purchase when every quantity is blank or zero',()=>{
  expect(buildReceiving([{...cell,incoming_quantity:''},{...cell,size_id:3,incoming_quantity:'0'}],{supplier_id:null,warehouse_id:null,unit_cost:''},'id')).toBeUndefined()
})
it('uses receiving cost rather than retail price and only sends positive rows',()=>{
  expect(buildReceiving([{...cell,incoming_quantity:'12'},{...cell,size_id:3,incoming_quantity:''}],details,'id')).toEqual({...details,request_id:'id',quantities:[{color_id:1,size_id:2,quantity:12}]})
})
it('rejects fractions negative quantities and missing purchase fields',()=>{
  for(const quantity of ['1.5','-1','1000001','abc'])expect(()=>buildReceiving([{...cell,incoming_quantity:quantity}],details,'id')).toThrow('进货数量')
  expect(()=>buildReceiving([{...cell,incoming_quantity:'1'}],{...details,warehouse_id:null},'id')).toThrow('仓库')
  expect(()=>buildReceiving([{...cell,incoming_quantity:'1'}],{...details,supplier_id:null},'id')).toThrow('供应商')
  expect(()=>buildReceiving([{...cell,incoming_quantity:'1'}],{...details,unit_cost:''},'id')).toThrow('单价')
})
