<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance } from 'element-plus'
import { apiRequest, allOptions } from '../api/client'
import type { Dictionary, MatrixCell, Product } from '../api/types'
import { buildMatrix } from '../components/matrix'
import SkuMatrix from '../components/SkuMatrix.vue'
const route=useRoute();const router=useRouter();const editing=Boolean(route.params.id)
const form=reactive({code:'',name:'',category:'',year:new Date().getFullYear(),season:'春夏',wave_band:'',fabric_composition:'',safety_category:'B类',tag_price:'',purchase_base_price:'',min_retail_price:''})
const colorIds=ref<number[]>([]);const groupId=ref<number|null>(null);const colors=ref<Dictionary[]>([]);const groups=ref<Dictionary[]>([]);const existingSizes=ref<Dictionary[]>([]);const cells=ref<MatrixCell[]>([]);const bulkPrice=ref('');const error=ref('');const loading=ref(false);const busy=ref(false);const formRef=ref<FormInstance>();const saved=ref(false);let initial=''
const selectedColors=computed(()=>colorIds.value.map(id=>colors.value.find(color=>color.id===id)).filter((color):color is Dictionary=>Boolean(color)))
const sizes=computed(()=>editing?existingSizes.value:groups.value.find(group=>group.id===groupId.value)?.sizes?.filter(size=>size.status==='ACTIVE')||[])
const rules={code:[{required:true,message:'请输入款号',trigger:'blur'}],name:[{required:true,message:'请输入款名',trigger:'blur'}],category:[{required:true,message:'请输入品类',trigger:'blur'}],year:[{required:true,message:'请输入年份',trigger:'blur'}],tag_price:[{required:true,message:'请输入吊牌价',trigger:'blur'}]}
const returnTo=typeof route.query.returnTo==='string'&&/^\/products(?:\?|$)/.test(route.query.returnTo)?route.query.returnTo:'/products'
function snapshot(){return JSON.stringify({form,colorIds:colorIds.value,groupId:groupId.value,cells:cells.value})}
watch([colorIds,groupId],()=>{if(!editing)cells.value=buildMatrix(selectedColors.value,sizes.value,cells.value,form.tag_price||'0.00')},{deep:true})
async function load(){
  loading.value=true;error.value=''
  try{
    const [colorData,groupData]=await Promise.all([allOptions<Dictionary>('/colors'),allOptions<Dictionary>('/size-groups')]);colors.value=colorData;groups.value=groupData
    if(editing){const product=await apiRequest<Product>(`/products/${route.params.id}`);for(const key of Object.keys(form) as (keyof typeof form)[]){if(key==='year')form.year=product.year;else (form[key] as string)=String(product[key]??'')}
      const colorMap=new Map(product.skus.map(cell=>[cell.color.id,cell.color]));colors.value=[...colorMap.values()];colorIds.value=[...colorMap.keys()];existingSizes.value=[...new Map(product.skus.map(cell=>[cell.size.id,cell.size])).values()];groupId.value=product.size_group_id;cells.value=product.skus.map(cell=>({id:cell.id,color_id:cell.color_id,size_id:cell.size_id,retail_price:cell.retail_price,barcode:cell.barcode,code:cell.code}))
    }
    await nextTick();initial=snapshot()
  }catch(e){error.value=(e as Error).message}finally{loading.value=false}
}
function fill(){if(!/^\d+(\.\d{1,2})?$/.test(bulkPrice.value)){ElMessage.error('请填写非负金额，最多两位小数');return}cells.value=cells.value.map(cell=>({...cell,retail_price:bulkPrice.value}))}
async function save(){
  if(busy.value||loading.value)return
  if(!(await formRef.value?.validate().catch(()=>false))){await nextTick();document.querySelector<HTMLInputElement>('.is-error input')?.focus();return}
  if(!cells.value.length){error.value='请选择颜色和尺码组，生成商品规格';return}
  const prices=[form.tag_price,...cells.value.map(c=>c.retail_price),...(form.purchase_base_price?[form.purchase_base_price]:[]),...(form.min_retail_price?[form.min_retail_price]:[])]
  if(prices.some(p=>!/^\d+(\.\d{1,2})?$/.test(p))){error.value='价格必须为非负金额，最多两位小数';return}
  busy.value=true;error.value=''
  const base={...form,purchase_base_price:form.purchase_base_price||null,min_retail_price:form.min_retail_price||null}
  const body=editing?{...base,sku_prices:cells.value.map(c=>({id:c.id,retail_price:c.retail_price}))}:{...base,color_ids:colorIds.value,size_group_id:groupId.value,skus:cells.value.map(c=>({color_id:c.color_id,size_id:c.size_id,retail_price:c.retail_price,...(c.barcode?{barcode:c.barcode}:{})}))}
  try{await apiRequest(`/products${editing?`/${route.params.id}`:''}`,{method:editing?'PATCH':'POST',body:JSON.stringify(body)});saved.value=true;ElMessage.success('商品已保存');await router.push(returnTo)}
  catch(e){error.value=(e as Error).message}finally{busy.value=false}
}
onBeforeRouteLeave(async()=>{if(saved.value)return true;if(busy.value)return false;if(!initial||snapshot()===initial)return true;try{await ElMessageBox.confirm('商品信息尚未保存，离开后将丢失。','放弃修改？',{confirmButtonText:'放弃修改',cancelButtonText:'继续编辑',type:'warning'});return true}catch{return false}})
function beforeUnload(event:BeforeUnloadEvent){if(initial&&!saved.value&&snapshot()!==initial){event.preventDefault();event.returnValue=''}}
onMounted(()=>{void load();window.addEventListener('beforeunload',beforeUnload)});onBeforeUnmount(()=>window.removeEventListener('beforeunload',beforeUnload))
</script>
<template><section v-loading="loading"><div class="page-heading"><div><h1>{{editing?'编辑商品':'新建商品'}}</h1><p>建立款号与颜色尺码规格。</p></div><div class="heading-actions"><el-button :disabled="busy" @click="router.push(returnTo)">取消</el-button><el-button type="primary" :loading="busy" :disabled="loading" @click="save">保存商品</el-button></div></div>
<div v-if="error" class="inline-error" role="alert">{{error}} <a v-if="error.includes('登录')" href="/login" target="_blank" rel="noopener">在新标签页登录后重试</a><el-button v-if="!initial" text @click="load">重试加载</el-button></div>
<el-form ref="formRef" :model="form" :rules="rules" label-position="top" novalidate @submit.prevent="save">
<div class="panel editor-panel"><h2>基本信息</h2><div class="form-grid product-fields">
<el-form-item label="款号" prop="code" for="product-code"><el-input id="product-code" v-model="form.code" :readonly="editing" maxlength="64" placeholder="例如 2026S-DR088" /></el-form-item>
<el-form-item label="款名" prop="name" for="product-name"><el-input id="product-name" v-model="form.name" maxlength="128" placeholder="请输入商品款名" /></el-form-item>
<el-form-item label="品类" prop="category" for="product-category"><el-input id="product-category" v-model="form.category" maxlength="64" placeholder="例如 连衣裙" /></el-form-item>
<el-form-item label="年份" prop="year" for="product-year"><el-input-number id="product-year" v-model="form.year" :min="1900" :max="2100" :precision="0" controls-position="right" /></el-form-item>
<el-form-item label="季节" for="product-season"><el-select id="product-season" v-model="form.season"><el-option v-for="season in ['春夏','秋冬','春季','夏季','秋季','冬季','四季']" :key="season" :label="season" :value="season" /></el-select></el-form-item>
<el-form-item label="吊牌价（元）" prop="tag_price" for="product-tag-price"><el-input id="product-tag-price" v-model="form.tag_price" inputmode="decimal" placeholder="例如 599.00" /></el-form-item>
<el-form-item label="采购基准价（元）" for="product-purchase-price"><el-input id="product-purchase-price" v-model="form.purchase_base_price" inputmode="decimal" placeholder="可选，作为参考价格" /></el-form-item>
<el-form-item label="最低零售价（元）" for="product-min-price"><el-input id="product-min-price" v-model="form.min_retail_price" inputmode="decimal" placeholder="可选" /></el-form-item>
<el-form-item label="波段" for="product-wave"><el-input id="product-wave" v-model="form.wave_band" maxlength="32" placeholder="例如 第2波段" /></el-form-item>
<el-form-item label="安全类别" for="product-safety"><el-select id="product-safety" v-model="form.safety_category"><el-option v-for="category in ['A类','B类','C类']" :key="category" :label="category" :value="category" /></el-select></el-form-item>
<el-form-item class="span-two" label="面料成分" for="product-fabric"><el-input id="product-fabric" v-model="form.fabric_composition" maxlength="2000" placeholder="可选，填写面料与成分" /></el-form-item>
</div></div>
<div class="panel editor-panel"><h2>颜色尺码矩阵</h2><div class="matrix-selectors"><div><label for="product-colors">选择颜色</label><el-select id="product-colors" v-model="colorIds" multiple filterable :disabled="editing" placeholder="请选择颜色"><el-option v-for="color in colors" :key="color.id" :label="color.name" :value="color.id" /></el-select><router-link v-if="!editing" to="/colors" class="small-link">管理颜色</router-link></div><div><label for="product-size-group">尺码组</label><el-select id="product-size-group" v-model="groupId" :disabled="editing" placeholder="请选择尺码组"><el-option v-for="group in groups" :key="group.id" :label="group.name" :value="group.id" /></el-select><router-link v-if="!editing" to="/size-groups" class="small-link">管理尺码组</router-link></div></div>
<div v-if="cells.length" class="matrix-toolbar"><label for="bulk-price">批量填充零售价</label><el-input id="bulk-price" v-model="bulkPrice" inputmode="decimal" placeholder="例如 599.00" /><el-button type="primary" @click="fill">填充</el-button><span role="status">已生成 {{cells.length}} 个规格</span></div>
<SkuMatrix v-if="cells.length" v-model="cells" :colors="selectedColors" :sizes="sizes" :product-code="form.code" :readonly-dimensions="editing" />
<el-empty v-else description="选择颜色和尺码组后，在这里生成规格矩阵。" :image-size="70" />
<p class="matrix-note">{{editing?'款号、条码和颜色尺码组合已固定，可以调整价格。':'内部条码默认使用规格编码；留空即可自动生成。'}}</p>
</div></el-form></section></template>
