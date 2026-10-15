<script setup lang="ts">
import { onMounted,ref } from 'vue'
import { apiRequest } from '../api/client'
import type { Employee } from '../api/people'
import EmployeeProfile from '../components/EmployeeProfile.vue'
const employee=ref<Employee|null>(null),error=ref(''),loading=ref(false)
async function load(){loading.value=true;error.value='';try{employee.value=await apiRequest<Employee>('/people/employees/me')}catch(e){error.value=(e as Error).message}finally{loading.value=false}}
onMounted(load)
</script>
<template><section><div class="page-heading"><div><h1>本人档案</h1><p>查看当前任职、联系方式与人事异动。</p></div><el-button :loading="loading" @click="load">刷新</el-button></div><div class="panel editor-panel" v-loading="loading"><div v-if="error" class="inline-error" role="alert">{{error}}<el-button text @click="load">重试</el-button></div><EmployeeProfile v-else-if="employee" :employee="employee"/><el-empty v-else-if="!loading" description="当前账号尚未关联员工档案"/></div></section></template>
