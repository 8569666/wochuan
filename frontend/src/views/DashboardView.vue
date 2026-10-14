<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { apiRequest } from '../api/client'
const data = ref<Record<string,number>|null>(null); const loading=ref(false); const error=ref('')
const stats=[{key:'stores',label:'门店',path:'/stores'},{key:'warehouses',label:'仓库',path:'/warehouses'},{key:'suppliers',label:'供应商',path:'/suppliers'},{key:'products',label:'商品款号',path:'/products'},{key:'skus',label:'商品规格',path:'/products'}]
async function load(){loading.value=true;error.value='';try{data.value=await apiRequest('/dashboard/summary')}catch(e){error.value=(e as Error).message}finally{loading.value=false}}
onMounted(load)
</script>
<template><section><div class="page-heading"><div><h1>工作台</h1><p>把基础档案建立好，让后续进销存有据可循。</p></div><el-button :loading="loading" @click="load">刷新数据</el-button></div>
<el-alert v-if="error" :title="error" type="error" :closable="false" role="alert" />
<div v-else class="stat-strip" v-loading="loading"><router-link v-for="stat in stats" :key="stat.key" :to="stat.path"><span>{{stat.label}}</span><strong>{{data ? data[stat.key] : '—'}}</strong><small>查看档案 →</small></router-link></div>
<div class="panel onboarding"><h2>从基础档案开始</h2><p>先建立门店与仓库，再维护供应商和商品规格。</p><ol><li><router-link to="/stores">建立门店档案</router-link><span>填写门店编码、类型与联系方式</span></li><li><router-link to="/warehouses">配置总仓与门店仓库</router-link><span>为每家门店关联默认店仓</span></li><li><router-link to="/suppliers">维护供应商信息</router-link><span>整理联系人和结算方式</span></li><li><router-link to="/products/new">创建商品颜色尺码矩阵</router-link><span>一次建立款号及其全部规格</span></li></ol></div>
</section></template>
