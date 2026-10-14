<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { InputInstance } from 'element-plus'
import { Search, Plus } from '@element-plus/icons-vue'
import { apiRequest } from '../api/client'
import type { Archive, FieldSpec, Page } from '../api/types'
import ArchiveEditor from './ArchiveEditor.vue'
const props=defineProps<{path:string;title:string;label:string;description:string;fields:FieldSpec[];columns:FieldSpec[];productRoute?:boolean;searchPlaceholder?:string}>()
const route=useRoute();const router=useRouter()
const keyword=ref(String(route.query.keyword||''));const status=ref(String(route.query.status||''));const page=ref(Math.max(1,Number(route.query.page)||1));const pageSize=ref([20,50,100].includes(Number(route.query.page_size))?Number(route.query.page_size):20)
const rows=ref<Archive[]>([]);const total=ref(0);const loading=ref(false);const error=ref('');const dialog=ref(false);const current=ref<Archive|null>(null);const rowBusy=ref<number|null>(null)
const searchRef=ref<InputInstance>()
let controller:AbortController|null=null;let revision=0;let timer:ReturnType<typeof setTimeout>|undefined;const composing=ref(false)
async function load(){
  const seq=++revision;controller?.abort();controller=new AbortController();loading.value=true;error.value=''
  const params=new URLSearchParams({page:String(page.value),page_size:String(pageSize.value)});if(keyword.value)params.set('keyword',keyword.value);if(status.value)params.set('status',status.value)
  await router.replace({query:Object.fromEntries(params)})
  try{const data=await apiRequest<Page<Archive>>(`${props.path}?${params}`,{signal:controller.signal});if(seq!==revision)return;rows.value=data.items;total.value=data.total;if(page.value>1&&rows.value.length===0){page.value=Math.max(1,Math.ceil(data.total/pageSize.value));void load()}}
  catch(e){if(seq===revision&&(e as Error).name!=='AbortError')error.value=(e as Error).message}finally{if(seq===revision)loading.value=false}
}
function search(){clearTimeout(timer);if(composing.value)return;if(!keyword.value){page.value=1;void load();return}timer=setTimeout(()=>{page.value=1;void load()},300)}
function clearSearch(){clearTimeout(timer);page.value=1;void load()}
function edit(row:Archive|null){if(props.productRoute){void router.push({path:row?`/products/${row.id}`:'/products/new',query:{returnTo:route.fullPath}});return}current.value=row;dialog.value=true}
async function toggle(row:Archive){
  if(rowBusy.value!==null)return
  const disabling=row.status==='ACTIVE'
  if(disabling){try{await ElMessageBox.confirm(`停用“${row.name}”后，新业务将不能选择此档案，历史记录仍保留。`,'停用档案',{confirmButtonText:'停用',cancelButtonText:'取消',type:'warning'})}catch{return}}
  rowBusy.value=row.id
  try{await apiRequest(`${props.path}/${row.id}`,{method:'PATCH',body:JSON.stringify({status:disabling?'INACTIVE':'ACTIVE'})});ElMessage.success(disabling?'档案已停用':'档案已启用');await load()}catch(e){ElMessage.error((e as Error).message)}finally{rowBusy.value=null}
}
function display(row:Archive,field:FieldSpec){const value=row[field.key];if(field.kind==='sizes'&&Array.isArray(value))return value.map(v=>v.name).join(' / ');return field.options?.find(option=>option.value===value)?.label||String(value??'—')}
watch(keyword,search);watch(status,()=>{page.value=1;void load()});onMounted(load);onBeforeUnmount(()=>{revision++;controller?.abort();clearTimeout(timer)})
</script>
<template><section><div class="page-heading"><div><h1>{{title}}</h1><p>{{description}}</p></div><div class="heading-actions"><slot name="actions"/><el-button type="primary" :icon="Plus" @click="edit(null)">新建{{label}}</el-button></div></div>
<div class="panel"><div class="table-toolbar"><el-input ref="searchRef" v-model="keyword" :prefix-icon="Search" :placeholder="searchPlaceholder||'搜索编码或名称'" :aria-label="searchPlaceholder||'搜索编码或名称'" @keyup.enter="clearSearch" @compositionstart="composing=true" @compositionend="composing=false;search()" /><el-button v-if="keyword" text aria-label="清除搜索" @click="keyword='';searchRef?.focus()">清除</el-button><el-select v-model="status" aria-label="筛选档案状态" clearable placeholder="全部状态"><el-option label="启用" value="ACTIVE"/><el-option label="停用" value="INACTIVE"/></el-select><el-button :loading="loading" @click="load">刷新</el-button></div>
<div v-if="error" class="error-state" role="alert"><p>{{error}}</p><el-button @click="load">重试</el-button></div>
<el-table v-else :data="rows" v-loading="loading" class="archive-table" :empty-text="loading?'正在加载…':keyword||status?'没有匹配的档案，请调整筛选条件':'暂无档案，点击右上角新建'" row-key="id">
  <el-table-column v-for="column in columns" :key="column.key" :label="column.label" :min-width="column.key==='name'?180:140"><template #default="{row}"><span :class="{code:column.key==='code'}">{{display(row,column)}}</span></template></el-table-column>
  <el-table-column label="状态" width="100"><template #default="{row}"><span class="state-label" :class="{inactive:row.status==='INACTIVE'}">{{row.status==='ACTIVE'?'启用':'停用'}}</span></template></el-table-column>
  <el-table-column label="操作" width="155" fixed="right"><template #default="{row}"><el-button text type="primary" @click="edit(row)">编辑</el-button><el-button text :type="row.status==='ACTIVE'?'danger':'primary'" :loading="rowBusy===row.id" :disabled="rowBusy!==null&&rowBusy!==row.id" @click="toggle(row)">{{row.status==='ACTIVE'?'停用':'启用'}}</el-button></template></el-table-column>
</el-table>
<div class="pagination"><span role="status">共 {{total}} 条档案</span><el-pagination v-model:current-page="page" v-model:page-size="pageSize" :page-sizes="[20,50,100]" layout="sizes, prev, pager, next" :total="total" @current-change="load" @size-change="page=1;load()" /></div></div>
<ArchiveEditor v-model="dialog" :record="current" :path="path" :label="label" :fields="fields" @saved="load" />
</section></template>
