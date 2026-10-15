import type { Archive } from './types'
export interface OrgUnit extends Archive {kind:string;parent_id:number|null;store_id?:number|null;warehouse_id?:number|null;children?:OrgUnit[]}
export interface Grant {role_id:number;scope_type:string;scope_ids:number[]}
export interface Role extends Archive {permissions:string[]}
export interface Employee extends Omit<Archive,'status'> {id:number;code:string;name:string;status:string;phone?:string;personnel_type:string;company_id?:number;org_unit_id:number;position_id:number;manager_id?:number|null;hire_date?:string;company_name?:string;org_unit_name?:string;position_name?:string;manager_name?:string;assignments?:Record<string,unknown>[];events?:Record<string,unknown>[];account?:{id:number;username:string;enabled:boolean;grants?:Grant[]}|null}
export const employeeStatuses=[{value:'PENDING',label:'待入职'},{value:'PROBATION',label:'试用'},{value:'ACTIVE',label:'在职'},{value:'LEFT',label:'离职'}]
export const personnelTypes=[{value:'EMPLOYEE',label:'正式员工'},{value:'CONTRACTOR',label:'外包'},{value:'PARTNER',label:'合作伙伴'},{value:'TEMP',label:'临时人员'}]
export const eventKinds=[{value:'ONBOARD',label:'入职'},{value:'CONFIRM',label:'转正'},{value:'TRANSFER',label:'调岗'},{value:'LEAVE',label:'离职'}]
export const orgKinds=[{value:'COMPANY',label:'公司'},{value:'HQ',label:'总部'},{value:'REGION',label:'区域'},{value:'DEPARTMENT',label:'部门'},{value:'STORE',label:'门店'},{value:'WAREHOUSE',label:'仓库'}]
