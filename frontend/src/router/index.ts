import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import AdminLayout from '../layouts/AdminLayout.vue'

export const router = createRouter({history:createWebHistory(), routes:[
  {path:'/login',component:()=>import('../views/LoginView.vue'),meta:{title:'登录'}},
  {path:'/',component:AdminLayout,children:[
    {path:'',component:()=>import('../views/DashboardView.vue'),meta:{permission:'dashboard.read',title:'工作台'}},
    {path:'stores',component:()=>import('../views/StoresView.vue'),meta:{permission:'store.read',title:'门店管理'}},
    {path:'warehouses',component:()=>import('../views/WarehousesView.vue'),meta:{permission:'warehouse.read',title:'仓库管理'}},
    {path:'suppliers',component:()=>import('../views/SuppliersView.vue'),meta:{permission:'supplier.read',title:'供应商管理'}},
    {path:'purchase-receipts',component:()=>import('../views/InventoryView.vue'),props:{mode:'receipts'},meta:{permission:'purchase.read',title:'采购进货'}},
    {path:'inventory',component:()=>import('../views/InventoryView.vue'),props:{mode:'inventory'},meta:{permission:'inventory.read',title:'库存查询'}},
    {path:'inventory/movements',component:()=>import('../views/InventoryView.vue'),props:{mode:'movements'},meta:{permission:'inventory.read',title:'库存流水'}},
    {path:'products',component:()=>import('../views/ProductsView.vue'),meta:{permission:'catalog.read',title:'商品中心'}},
    {path:'products/new',component:()=>import('../views/ProductEditorView.vue'),meta:{permission:'catalog.write',title:'新建商品'}},
    {path:'products/:id',component:()=>import('../views/ProductEditorView.vue'),meta:{permission:'catalog.read',title:'编辑商品'}},
    {path:'categories',component:()=>import('../views/CategoriesView.vue'),meta:{permission:'catalog.read',title:'品类管理'}},
    {path:'fabrics',component:()=>import('../views/FabricsView.vue'),meta:{permission:'catalog.read',title:'面料成分管理'}},
    {path:'colors',component:()=>import('../views/ColorsView.vue'),meta:{permission:'catalog.read',title:'颜色管理'}},
    {path:'size-groups',component:()=>import('../views/SizeGroupsView.vue'),meta:{permission:'catalog.read',title:'尺码组管理'}},
    {path:'people/:section(org-units|positions|employees|roles)',component:()=>import('../views/PeopleView.vue'),meta:{title:'人员架构'}},
    {path:'my-profile',component:()=>import('../views/MyProfileView.vue'),meta:{title:'本人档案'}},
    {path:':pathMatch(.*)*',component:()=>import('../views/NotFoundView.vue'),meta:{title:'页面不存在'}},
  ]},
]})
router.beforeEach(async to => {
  const auth = useAuthStore()
  if (to.path !== '/login' && !auth.user) {
    try { await auth.loadSession() } catch { return {path:'/login',query:{redirect:to.fullPath}} }
  }
  if(to.path.startsWith('/people/')){const section=String(to.params.section);const permission=section==='org-units'?'org.read':section==='positions'?'position.read':'employee.read';if(section==='roles'?!auth.admin():!auth.has(permission))return '/my-profile'}
  if(to.path==='/products/new'&&!auth.hasGlobal('catalog.write'))return '/my-profile'
  if(to.meta.permission&&!auth.has(String(to.meta.permission)))return '/my-profile'
})
router.afterEach(to => { document.title = `${String(to.meta.title||'总部后台')} · 我川 W-ERP` })