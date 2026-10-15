import { expect, it } from 'vitest'
import { hasPermission, archivePermission, receivingOnlyBody } from '../access'
it('keeps ADMIN compatibility and distinguishes scoped and global rights',()=>{
  expect(hasPermission({id:1,username:'admin',display_name:'管理员',role:'ADMIN'},'catalog.write',true)).toBe(true)
  const user={id:2,username:'staff',display_name:'员工',role:'STAFF',permissions:['catalog.write','purchase.receive'],global_permissions:[]}
  expect(hasPermission(user,'catalog.write')).toBe(true)
  expect(hasPermission(user,'catalog.write',true)).toBe(false)
  expect(hasPermission(user,'role.manage')).toBe(false)
  expect(archivePermission('/people/positions')).toBe('position.manage')
})
it('receiver payload never carries metadata or price edits',()=>{
  expect(receivingOnlyBody({request_id:'x',warehouse_id:1})).toEqual({receiving:{request_id:'x',warehouse_id:1}})
  expect(()=>receivingOnlyBody(null)).toThrow('请填写本次进货数量')
})
