<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { FormInstance } from 'element-plus'
import { useAuthStore } from '../stores/auth'
const auth = useAuthStore(); const router = useRouter(); const route = useRoute()
const form = reactive({username:'',password:''}); const busy = ref(false); const error = ref(''); const formRef=ref<FormInstance>()
const rules = {username:[{required:true,message:'请输入用户名',trigger:'blur'}],password:[{required:true,message:'请输入密码',trigger:'blur'}]}
async function submit() {
  if (busy.value || !(await formRef.value?.validate().catch(()=>false))) return
  busy.value=true; error.value=''
  try { await auth.login(form.username,form.password); const redirect=String(route.query.redirect||(auth.has('dashboard.read')?'/':'/my-profile')); await router.replace(redirect.startsWith('/')&&!redirect.startsWith('//') ? redirect : '/') }
  catch(e) { error.value=(e as Error).message } finally { busy.value=false }
}
</script>
<template>
  <main class="login-page"><section class="login-story"><div class="brand"><strong>我川</strong><span>W-ERP</span></div><h1>从一款商品，<br>连接每一家门店。</h1><p>商品、门店与供应商档案，<br>在同一个工作台中有序管理。</p><div class="login-line">女装连锁 · 总部管理后台</div></section>
  <section class="login-form-panel"><div class="login-form"><h2>登录总部后台</h2><p class="subtext">使用员工账号进入工作台</p>
  <el-form ref="formRef" :model="form" :rules="rules" label-position="top" :show-message="true" novalidate @submit.prevent="submit">
    <el-form-item label="用户名" prop="username" for="login-username"><el-input id="login-username" v-model="form.username" autocomplete="username" placeholder="请输入用户名" /></el-form-item>
    <el-form-item label="密码" prop="password" for="login-password"><el-input id="login-password" v-model="form.password" type="password" show-password autocomplete="current-password" placeholder="请输入密码" /></el-form-item>
    <p v-if="error" role="alert" class="inline-error">{{error}}</p><el-button type="primary" native-type="submit" :loading="busy" class="login-submit">登录</el-button>
  </el-form><p class="setup-note">首次使用请先完成管理员初始化。<br>请查看项目启动说明获取本地账号。</p></div></section></main>
</template>
