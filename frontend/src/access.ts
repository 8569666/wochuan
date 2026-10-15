import { computed } from 'vue'
import { getActivePinia } from 'pinia'
import { useAuthStore } from './stores/auth'
import type { User } from './api/types'
export function isAdmin(user:User|null|undefined){return user?.is_admin===true||user?.role==='ADMIN'}
export function hasPermission(user:User|null|undefined,code:string,global=false){return isAdmin(user)||Boolean((global?user?.global_permissions:user?.permissions)?.includes(code))}
export function archivePermission(path:string){return path.startsWith('/people/positions')?'position.manage':path.startsWith('/people/org-units')?'org.manage':path==='/stores'?'store.write':path==='/warehouses'?'warehouse.write':path==='/suppliers'?'supplier.write':'catalog.write'}
export function useAccess(){const auth=getActivePinia()?useAuthStore():null;return {admin:computed(()=>isAdmin(auth?.user)),has:(code:string)=>hasPermission(auth?.user,code),hasGlobal:(code:string)=>hasPermission(auth?.user,code,true)}}
export function receivingOnlyBody(receiving:unknown){if(!receiving)throw new Error('请填写本次进货数量');return {receiving}}
