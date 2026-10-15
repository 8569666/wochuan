export interface ApiResponse<T> { code: number; message: string; data: T; timestamp: number }
export interface Page<T> { items: T[]; total: number; page: number; page_size: number }
export interface User { id: number; username: string; display_name: string; role: string; employee_id?:number|null; permissions?:string[]; global_permissions?:string[]; is_admin?:boolean }
export interface Archive { id: number; code: string; name: string; status: 'ACTIVE'|'INACTIVE'; [key: string]: unknown }
export interface Dictionary extends Archive { hex_value?: string|null; sizes?: Dictionary[]; composition?:string; last_fabric_id?:number|null }
export interface MatrixCell { id?: number; color_id: number; size_id: number; retail_price: string; barcode?: string; code?: string; incoming_quantity?:string }
export interface Product extends Archive { category: string; year: number; season: string; tag_price: string; purchase_base_price: string|null; min_retail_price: string|null; size_group_id: number; sku_count?: number; skus: (MatrixCell & {id: number; color: Dictionary; size: Dictionary})[] }
export interface FieldSpec { key: string; label: string; kind?: 'text'|'textarea'|'select'|'sizes'; required?: boolean; options?: {label:string;value:string|number}[]; endpoint?: string; placeholder?: string; maxLength?: number }
export type FormValues = Record<string, string|number|null|undefined>
