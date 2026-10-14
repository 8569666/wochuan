<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { House, Shop, Box, UserFilled, PriceTag, Menu } from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth'
const auth = useAuthStore(); const route = useRoute(); const router = useRouter()
const open = ref(false); const busy = ref(false)
const links = [{path:'/',label:'工作台',icon:House},{path:'/stores',label:'门店管理',icon:Shop},{path:'/warehouses',label:'仓库管理',icon:Box},{path:'/suppliers',label:'供应商管理',icon:UserFilled},{path:'/products',label:'商品中心',icon:PriceTag}]
function selected(path:string) { return path === '/' ? route.path === '/' : path === '/products' ? ['/products','/colors','/size-groups'].some(p=>route.path.startsWith(p)) : route.path.startsWith(path) }
async function logout() { busy.value=true; try { await auth.logout(); await router.push('/login') } catch(error) { ElMessage.error((error as Error).message) } finally { busy.value=false } }
</script>
<template>
  <div class="admin-shell">
    <aside class="sidebar" :class="{expanded:open}">
      <div class="brand"><strong>我川</strong><span>W-ERP</span></div><p class="brand-caption">女装连锁总部管理</p>
      <nav aria-label="主导航"><router-link v-for="item in links" :key="item.path" :to="item.path" :class="{selected:selected(item.path)}" @click="open=false"><el-icon><component :is="item.icon" /></el-icon>{{item.label}}</router-link></nav>
      <div class="sidebar-footer">基础档案 · 第一阶段</div>
    </aside>
    <div class="main-shell">
      <header class="topbar"><el-button class="mobile-menu" :icon="Menu" aria-label="展开导航" @click="open=!open" /><div class="breadcrumb">总部管理 <span>/</span> <strong>{{route.meta.title}}</strong></div><div class="user-menu"><el-icon><UserFilled /></el-icon><span>{{auth.user?.display_name}}</span><el-button text :loading="busy" @click="logout">退出</el-button></div></header>
      <main class="content"><router-view :key="route.path" /></main>
    </div>
  </div>
</template>
