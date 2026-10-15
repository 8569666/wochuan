import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import AdminLayout from '../layouts/AdminLayout.vue'

export const router = createRouter({history:createWebHistory(), routes:[
  {path:'/login',component:()=>import('../views/LoginView.vue'),meta:{title:'登录'}},
  {path:'/',component:AdminLayout,children:[
    {path:'',component:()=>import('../views/DashboardView.vue'),meta:{title:'工作台'}},
    {path:'stores',component:()=>import('../views/StoresView.vue'),meta:{title:'门店管理'}},
    {path:'warehouses',component:()=>import('../views/WarehousesView.vue'),meta:{title:'仓库管理'}},
    {path:'suppliers',component:()=>import('../views/SuppliersView.vue'),meta:{title:'供应商管理'}},
    {path:'purchase-receipts',component:()=>import('../views/InventoryView.vue'),props:{mode:'receipts'},meta:{title:'采购进货'}},
    {path:'inventory',component:()=>import('../views/InventoryView.vue'),props:{mode:'inventory'},meta:{title:'库存查询'}},
    {path:'inventory/movements',component:()=>import('../views/InventoryView.vue'),props:{mode:'movements'},meta:{title:'库存流水'}},
    {path:'products',component:()=>import('../views/ProductsView.vue'),meta:{title:'商品中心'}},
    {path:'products/new',component:()=>import('../views/ProductEditorView.vue'),meta:{title:'新建商品'}},
    {path:'products/:id',component:()=>import('../views/ProductEditorView.vue'),meta:{title:'编辑商品'}},
    {path:'categories',component:()=>import('../views/CategoriesView.vue'),meta:{title:'品类管理'}},
    {path:'fabrics',component:()=>import('../views/FabricsView.vue'),meta:{title:'面料成分管理'}},
    {path:'colors',component:()=>import('../views/ColorsView.vue'),meta:{title:'颜色管理'}},
    {path:'size-groups',component:()=>import('../views/SizeGroupsView.vue'),meta:{title:'尺码组管理'}},
    {path:':pathMatch(.*)*',component:()=>import('../views/NotFoundView.vue'),meta:{title:'页面不存在'}},
  ]},
]})
router.beforeEach(async to => {
  const auth = useAuthStore()
  if (to.path !== '/login' && !auth.user) {
    try { await auth.loadSession() } catch { return {path:'/login',query:{redirect:to.fullPath}} }
  }
})
router.afterEach(to => { document.title = `${String(to.meta.title||'总部后台')} · 我川 W-ERP` })
