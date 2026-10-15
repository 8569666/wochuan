<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAccess } from '../access'
import { allOptions, apiRequest } from '../api/client'
import type { Dictionary, Page } from '../api/types'
type ReportRow=Record<string,unknown> & {id:number;product_id:number}
const props=defineProps<{mode:'inventory'|'receipts'|'movements'}>()
const access=useAccess();const route=useRoute(),router=useRouter()
const title=computed(()=>props.mode==='inventory'?'库存查询':props.mode==='receipts'?'采购进货':'库存流水')
const path=computed(()=>props.mode==='inventory'?'/inventory':props.mode==='receipts'?'/purchase-receipts':'/inventory/movements')
const rows=ref<ReportRow[]>([]),total=ref(0),loading=ref(false),error=ref(''),warehouses=ref<Dictionary[]>([])
const search=ref(String(route.query.keyword||'')),composing=ref(false)
let searchTimer:ReturnType<typeof setTimeout>|undefined,controller:AbortController|undefined
const page=computed(()=>Math.max(1,Number(route.query.page)||1))
const pageSize=computed(()=>[20,50,100].includes(Number(route.query.page_size))?Number(route.query.page_size):20)
const warehouseId=computed(()=>Number(route.query.warehouse_id)||undefined)
async function queryChange(values:Record<string,string|number|undefined>){const query={...route.query,...values};for(const key of Object.keys(query))if(query[key]===undefined||query[key]==='')delete query[key];await router.replace({query})}
function searchChange(value:string){search.value=value;if(composing.value)return;if(searchTimer)clearTimeout(searchTimer);searchTimer=setTimeout(()=>void queryChange({keyword:value,page:1}),300)}
async function load(){
  controller?.abort();const current=new AbortController();controller=current;loading.value=true;error.value=''
  const query=new URLSearchParams({page:String(page.value),page_size:String(pageSize.value)})
  if(warehouseId.value)query.set('warehouse_id',String(warehouseId.value))
  if(props.mode!=='movements'&&route.query.keyword)query.set('keyword',String(route.query.keyword))
  try{const data=await apiRequest<Page<ReportRow>>(`${path.value}?${query}`,{signal:current.signal});if(current.signal.aborted)return;rows.value=data.items;total.value=data.total}
  catch(e){if(!current.signal.aborted)error.value=(e as Error).message}finally{if(!current.signal.aborted)loading.value=false}
}
watch(()=>route.query,()=>{search.value=String(route.query.keyword||'');void load()},{immediate:true})
onMounted(async()=>{if(!access.has('warehouse.read'))return;try{warehouses.value=await allOptions<Dictionary>('/warehouses')}catch(e){error.value=(e as Error).message}})
onBeforeUnmount(()=>{controller?.abort();if(searchTimer)clearTimeout(searchTimer)})
const detailOpen=ref(false),detailLoading=ref(false),detailError=ref(''),detail=ref<Record<string,unknown>|null>(null),detailLines=ref<Record<string,unknown>[]>([])
let detailId=0
let detailVersion=0
watch(detailOpen,open=>{if(!open){detailVersion++;detailLoading.value=false}})
onBeforeUnmount(()=>{detailVersion++})
async function showDetail(id:number){const version=++detailVersion;detailId=id;detailOpen.value=true;detailLoading.value=true;detailError.value='';detail.value=null;detailLines.value=[];try{const data=await apiRequest<Record<string,unknown>&{lines:Record<string,unknown>[]}>(`/purchase-receipts/${id}`);if(version!==detailVersion)return;detail.value=data;detailLines.value=data.lines}catch(e){if(version===detailVersion)detailError.value=(e as Error).message}finally{if(version===detailVersion)detailLoading.value=false}}
function localTime(value:unknown){return typeof value==='string'?new Date(value).toLocaleString('zh-CN',{timeZone:'Asia/Shanghai',hour12:false}):''}
</script>
<template><section><div class="page-heading"><div><h1>{{title}}</h1><p>{{mode==='receipts'?'在商品资料页填写数量并保存，生成已入库采购单。':mode==='inventory'?'库存来源于已入库单据，按仓库和商品规格查询。':'每笔进货均保留单据、变化前数量、增量和变化后数量。'}}</p></div><div class="heading-actions"><router-link to="/products"><el-button>商品中心</el-button></router-link><router-link v-if="mode!=='receipts'&&access.has('purchase.read')" to="/purchase-receipts"><el-button>采购进货</el-button></router-link><router-link v-if="mode!=='inventory'&&access.has('inventory.read')" to="/inventory"><el-button>库存查询</el-button></router-link><router-link v-if="mode!=='movements'&&access.has('inventory.read')" to="/inventory/movements"><el-button>库存流水</el-button></router-link></div></div>
<div class="panel"><div class="table-toolbar"><el-input v-if="mode!=='movements'" :model-value="search" :aria-label="mode==='receipts'?'搜索入库单、款号或供应商':'搜索款号、款名或条码'" :placeholder="mode==='receipts'?'搜索入库单、款号或供应商':'搜索款号、款名或条码'" @update:model-value="searchChange" @compositionstart="composing=true" @compositionend="composing=false;searchChange(search)"/><el-button v-if="search&&mode!=='movements'" aria-label="清除搜索" @click="searchChange('')">清除</el-button><el-select v-if="access.has('warehouse.read')" :model-value="warehouseId" clearable filterable aria-label="筛选仓库" placeholder="全部仓库" @update:model-value="queryChange({warehouse_id:$event||undefined,page:1})"><el-option v-for="warehouse in warehouses" :key="warehouse.id" :label="warehouse.name" :value="warehouse.id"/></el-select><el-button @click="load">刷新</el-button></div>
<div v-if="error" class="inline-error" role="alert">{{error}} <el-button text @click="load">重试</el-button></div>
<el-table v-else v-loading="loading" :data="rows" :empty-text="loading?'正在加载…':mode==='inventory'?'暂无库存记录':mode==='receipts'?'暂无采购入库记录':'暂无库存流水'" style="width:100%">
<el-table-column v-if="mode==='receipts'" prop="number" label="入库单号" min-width="260"/>
<el-table-column v-if="mode==='movements'" prop="receipt_number" label="入库单号" min-width="260"/>
<el-table-column prop="warehouse_name" label="仓库" min-width="140"/>
<el-table-column v-if="mode==='receipts'" prop="supplier_name" label="供应商" min-width="160"/>
<el-table-column prop="product_code" label="款号" min-width="150"/><el-table-column prop="product_name" label="款名" min-width="180"/>
<template v-if="mode!=='receipts'"><el-table-column prop="color_name" label="颜色" min-width="100"/><el-table-column prop="size_name" label="码数" min-width="80"/><el-table-column prop="barcode" label="条码" min-width="200"/></template>
<template v-if="mode==='inventory'"><el-table-column prop="quantity" label="库存数量" min-width="110"/><el-table-column v-if="access.has('catalog.cost')&&rows.some(r=>r.average_cost!==undefined)" prop="average_cost" label="单位成本（元）" min-width="150"/><el-table-column v-if="access.has('catalog.cost')&&rows.some(r=>r.total_cost!==undefined)" prop="total_cost" label="存货金额（元）" min-width="150"/></template>
<template v-if="mode==='receipts'"><el-table-column prop="total_quantity" label="进货数量" min-width="110"/><el-table-column v-if="access.has('catalog.cost')&&(detailOpen?detailLines:rows).some(r=>r.unit_cost!==undefined)" prop="unit_cost" label="进货单价（元）" min-width="150"/><el-table-column v-if="access.has('catalog.cost')&&rows.some(r=>r.total_amount!==undefined)" prop="total_amount" label="金额（元）" min-width="140"/><el-table-column label="状态" width="100"><template #default>已入库</template></el-table-column></template>
<template v-if="mode==='movements'"><el-table-column prop="before_quantity" label="变化前" min-width="100"/><el-table-column prop="quantity" label="进货数量" min-width="110"/><el-table-column prop="after_quantity" label="变化后" min-width="100"/></template>
<el-table-column label="时间" min-width="180"><template #default="{row}">{{localTime(mode==='inventory'?row.updated_at:row.created_at)}}</template></el-table-column>
<el-table-column label="操作" min-width="130" fixed="right"><template #default="{row}"><el-button v-if="mode==='receipts'" link type="primary" @click="showDetail(row.id)">查看明细</el-button><router-link v-else :to="`/products/${row.product_id}`">查看商品</router-link></template></el-table-column>
</el-table><div class="pagination"><span>共 {{total}} 条记录</span><el-pagination :current-page="page" :page-size="pageSize" :total="total" :page-sizes="[20,50,100]" layout="sizes,prev,pager,next" @update:current-page="queryChange({page:$event})" @update:page-size="queryChange({page_size:$event,page:1})"/></div></div>
<el-dialog v-model="detailOpen" title="采购入库明细" width="840px"><div v-loading="detailLoading"><div v-if="detailError" role="alert" class="inline-error">{{detailError}} <el-button @click="showDetail(detailId)">重试</el-button></div><template v-if="detail"><p>{{detail.number}} · 已入库</p><p>{{detail.supplier_name}} → {{detail.warehouse_name}}</p><p>合计 {{detail.total_quantity}} 件<span v-if="access.has('catalog.cost')&&detail.total_amount!==undefined">，金额 {{detail.total_amount}} 元</span></p><el-table :data="detailLines"><el-table-column prop="color_name" label="颜色"/><el-table-column prop="size_name" label="码数"/><el-table-column prop="barcode" label="条码" min-width="200"/><el-table-column prop="quantity" label="数量"/><el-table-column v-if="access.has('catalog.cost')&&(detailOpen?detailLines:rows).some(r=>r.unit_cost!==undefined)" prop="unit_cost" label="单价（元）"/><el-table-column v-if="access.has('catalog.cost')&&detailLines.some(r=>r.amount!==undefined)" prop="amount" label="金额（元）"/></el-table></template></div></el-dialog>
</section></template>
