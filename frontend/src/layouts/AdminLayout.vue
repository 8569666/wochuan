<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { House, Shop, Box, UserFilled, PriceTag, Menu } from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth'
const auth = useAuthStore(); const route = useRoute(); const router = useRouter()
const open = ref(false); const busy = ref(false)
const allLinks = [{path:'/',label:'工作台',icon:House},{path:'/stores',label:'门店管理',icon:Shop},{path:'/warehouses',label:'仓库管理',icon:Box},{path:'/suppliers',label:'供应商管理',icon:UserFilled},{path:'/products',label:'商品中心',icon:PriceTag},{path:'/purchase-receipts',label:'采购进货',icon:Box},{path:'/inventory',label:'库存查询',icon:Box}]
const extraLinks=[{path:'/people/org-units',label:'组织架构',icon:Shop},{path:'/people/positions',label:'岗位管理',icon:UserFilled},{path:'/people/employees',label:'员工档案',icon:UserFilled},{path:'/people/roles',label:'角色权限',icon:UserFilled},{path:'/my-profile',label:'本人档案',icon:UserFilled}]
const permissions:Record<string,string>={'/':'dashboard.read','/stores':'store.read','/warehouses':'warehouse.read','/suppliers':'supplier.read','/products':'catalog.read','/purchase-receipts':'purchase.read','/inventory':'inventory.read','/people/org-units':'org.read','/people/positions':'position.read','/people/employees':'employee.read'}
const links=computed(()=>[...allLinks,...extraLinks].filter(item=>item.path==='/my-profile'||(item.path==='/people/roles'?auth.admin():auth.has(permissions[item.path]||''))))
function selected(path:string) { return path === '/' ? route.path === '/' : path === '/products' ? ['/products','/colors','/size-groups','/categories','/fabrics'].some(p=>route.path.startsWith(p)) : route.path.startsWith(path) }
async function logout() { busy.value=true; try { await auth.logout(); await router.push('/login') } catch(error) { ElMessage.error((error as Error).message) } finally { busy.value=false } }
</script>
<template>
  <div class="admin-shell">
    <aside class="sidebar" :class="{expanded:open}">
      <div class="brand"><strong>我川</strong><span>W-ERP</span></div><p class="brand-caption">女装连锁总部管理</p>
      <nav aria-label="主导航"><router-link v-for="item in links" :key="item.path" :to="item.path" :class="{selected:selected(item.path)}" @click="open=false"><el-icon><component :is="item.icon" /></el-icon>{{item.label}}</router-link></nav>
      <div class="sidebar-footer">基础档案 · 采购进货</div>
    </aside>
    <div class="main-shell">
      <header class="topbar"><el-button class="mobile-menu" :icon="Menu" aria-label="展开导航" @click="open=!open" /><div class="breadcrumb">总部管理 <span>/</span> <strong>{{route.meta.title}}</strong></div><div class="user-menu"><el-icon><UserFilled /></el-icon><span>{{auth.user?.display_name}}</span><el-button text :loading="busy" @click="logout">退出</el-button></div></header>
      <main class="content"><router-view :key="route.path" /></main>
    </div>
  </div>
</template>
