import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import './styles.css'
import App from './App.vue'
import { router } from './router'
import { useAuthStore } from './stores/auth'

const app = createApp(App)
app.use(createPinia()).use(ElementPlus).use(router)
window.addEventListener('werp:unauthorized', () => {
  useAuthStore().clear()
  if (router.currentRoute.value.path !== '/login') void router.replace({path:'/login',query:{redirect:router.currentRoute.value.fullPath}})
})
app.mount('#app')
