import type { MatrixCell } from '../api/types'
export interface ReceivingDetails { supplier_id:number|null;warehouse_id:number|null;unit_cost:string }
export function buildReceiving(cells:MatrixCell[],details:ReceivingDetails,requestId:string){
  const quantities:{color_id:number;size_id:number;quantity:number}[]=[]
  for(const cell of cells){
    const text=(cell.incoming_quantity||'').trim()
    if(!text)continue
    if(!/^\d+$/.test(text)||!Number.isSafeInteger(Number(text))||Number(text)>1000000)throw new Error('进货数量必须为0至1000000的整数，留空表示不进货')
    const quantity=Number(text)
    if(quantity>0)quantities.push({color_id:cell.color_id,size_id:cell.size_id,quantity})
  }
  if(!quantities.length)return undefined
  if(!details.supplier_id)throw new Error('填写进货数量后请选择供应商')
  if(!details.warehouse_id)throw new Error('填写进货数量后请选择收货仓库')
  if(!/^\d+(\.\d{1,2})?$/.test(details.unit_cost))throw new Error('请填写非负进货单价，最多两位小数')
  return {request_id:requestId,supplier_id:details.supplier_id,warehouse_id:details.warehouse_id,unit_cost:details.unit_cost,quantities}
}
