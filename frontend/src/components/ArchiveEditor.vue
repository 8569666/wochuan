<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { allOptions, apiRequest } from '../api/client'
import type { Archive, FieldSpec, FormValues } from '../api/types'
const props=defineProps<{modelValue:boolean;record:Archive|null;path:string;label:string;fields:FieldSpec[];readonly?:boolean}>()
const emit=defineEmits<{ 'update:modelValue':[boolean]; saved:[] }>()
const form=ref<FormValues>({}); const formRef=ref<FormInstance>(); const busy=ref(false); const error=ref(''); const initial=ref(''); const optionMap=ref<Record<string,{label:string;value:string|number}[]>>({})
const visibleFields=computed(()=>props.fields.filter(f=>f.key!=='store_id'||form.value.type==='STORE'))
const rules=computed<FormRules>(()=>Object.fromEntries(visibleFields.value.map(field=>[field.key,[{required:field.required,message:`请填写${field.label}`,trigger:'blur'}]])))
watch(()=>props.modelValue,async open=>{
  if(!open)return
  form.value={};error.value=''
  for(const field of props.fields){
    const raw=props.record?.[field.key]
    form.value[field.key]=field.kind==='sizes'&&Array.isArray(raw) ? raw.map(s=>String(s.code)).join(',') : typeof raw==='string'||typeof raw==='number' ? raw : field.kind==='select' ? field.options?.[0]?.value??null : ''
    if(field.endpoint){try{optionMap.value[field.key]=(await allOptions<Archive>(field.endpoint)).map(item=>({label:`${item.name} · ${item.code}`,value:item.id}))}catch(e){error.value=(e as Error).message}}
  }
  initial.value=JSON.stringify(form.value); await nextTick(); formRef.value?.clearValidate()
})
watch(()=>form.value.type,value=>{if(value&&value!=='STORE'&&'store_id'in form.value)form.value.store_id=null})
async function close(done?:()=>void){
  if(busy.value)return
  if(JSON.stringify(form.value)!==initial.value){try{await ElMessageBox.confirm('已填写的内容尚未保存，关闭后将丢失。','放弃修改？',{confirmButtonText:'放弃修改',cancelButtonText:'继续编辑',type:'warning'})}catch{return}}
  if(done)done();emit('update:modelValue',false)
}
async function save(){
  if(busy.value||props.readonly)return
  if(!(await formRef.value?.validate().catch(()=>false))){await nextTick();document.querySelector<HTMLInputElement>('.el-dialog .is-error input')?.focus();return}
  error.value='';busy.value=true
  const original=JSON.parse(initial.value) as FormValues
  const values:Record<string,unknown>=Object.fromEntries(Object.entries(form.value).filter(([key,value])=>!props.record||value!==original[key]))
  for(const field of props.fields){if(!field.required&&values[field.key]==='')values[field.key]=null}
  if('sizes'in values){values.sizes=String(form.value.sizes||'').split(',').map(s=>s.trim()).filter(Boolean).map(code=>({code,name:code}))}
  try{await apiRequest(props.path+(props.record?`/${props.record.id}`:''),{method:props.record?'PATCH':'POST',body:JSON.stringify(values)});ElMessage.success('档案已保存');emit('update:modelValue',false);emit('saved')}
  catch(e){error.value=(e as Error).message}finally{busy.value=false}
}
</script>
<template><el-dialog :model-value="modelValue" :title="`${record?'编辑':'新建'}${label}`" width="620px" :before-close="close" :close-on-click-modal="false" :close-on-press-escape="!busy" @update:model-value="emit('update:modelValue',$event)">
  <el-form ref="formRef" :model="form" :rules="rules" :disabled="readonly" label-position="top" novalidate @submit.prevent="save">
    <div class="form-grid"><el-form-item v-for="field in visibleFields" :key="field.key" :label="field.label" :prop="field.key" :for="`archive-${field.key}`" :class="{'span-full':field.kind==='textarea'||field.kind==='sizes'}">
      <el-select v-if="field.kind==='select'" :id="`archive-${field.key}`" v-model="form[field.key]" filterable clearable :placeholder="`请选择${field.label}`"><el-option v-for="option in field.options||optionMap[field.key]||[]" :key="option.value" :value="option.value" :label="option.label" /></el-select>
      <el-input v-else :id="`archive-${field.key}`" v-model="form[field.key]" :type="field.kind==='textarea'?'textarea':'text'" :rows="3" :maxlength="field.maxLength||(field.key==='code'?64:field.key==='name'?128:255)" :placeholder="field.placeholder||`请输入${field.label}`" :style="field.kind==='textarea'?{resize:'none'}:{}" />
    </el-form-item></div>
    <p v-if="error" class="inline-error" role="alert">{{error}} <a v-if="error.includes('登录')" href="/login" target="_blank" rel="noopener">在新标签页登录后重试</a></p>
  </el-form><template #footer><el-button :disabled="busy" @click="close()">取消</el-button><el-button v-if="!readonly" type="primary" :loading="busy" @click="save">保存档案</el-button></template>
</el-dialog></template>
