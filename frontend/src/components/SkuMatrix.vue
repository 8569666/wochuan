<script setup lang="ts">
import { computed } from 'vue'
import type { Dictionary, MatrixCell } from '../api/types'
const props=defineProps<{colors:Dictionary[];sizes:Dictionary[];modelValue:MatrixCell[];productCode:string;readonlyDimensions?:boolean}>()
const emit=defineEmits<{ 'update:modelValue':[MatrixCell[]] }>()
const map=computed(()=>new Map(props.modelValue.map(c=>[`${c.color_id}:${c.size_id}`,c])))
function value(color:number,size:number){return map.value.get(`${color}:${size}`)}
function change(color:number,size:number,field:'retail_price'|'barcode',newValue:string){emit('update:modelValue',props.modelValue.map(c=>c.color_id===color&&c.size_id===size?{...c,[field]:newValue}:c))}
</script>
<template><div class="matrix-scroll"><table class="matrix-table"><thead><tr><th scope="col">颜色</th><th v-for="size in sizes" :key="size.id" scope="col">{{size.name}}</th></tr></thead><tbody><tr v-for="color in colors" :key="color.id"><th scope="row"><span class="color-swatch" :style="{backgroundColor:color.hex_value||'#cbd5e1'}" />{{color.name}}</th><td v-for="size in sizes" :key="size.id"><div v-if="value(color.id,size.id)" class="matrix-cell"><label :for="`barcode-${color.id}-${size.id}`">内部条码</label><el-input :id="`barcode-${color.id}-${size.id}`" :model-value="value(color.id,size.id)?.barcode||''" :placeholder="`${productCode||'款号'}-${color.code}-${size.code}`" :readonly="readonlyDimensions" maxlength="64" :aria-label="`${color.name}${size.name}条码`" @update:model-value="change(color.id,size.id,'barcode',$event)" /><label :for="`price-${color.id}-${size.id}`">零售价（元）</label><el-input :id="`price-${color.id}-${size.id}`" :model-value="value(color.id,size.id)?.retail_price" inputmode="decimal" :aria-label="`${color.name}${size.name}零售价`" @update:model-value="change(color.id,size.id,'retail_price',$event)" /></div></td></tr></tbody></table></div></template>
