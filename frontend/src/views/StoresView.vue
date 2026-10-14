<script setup lang="ts">
import ArchiveTable from '../components/ArchiveTable.vue'
import type { FieldSpec } from '../api/types'
const fields:FieldSpec[]=[{key:'code',label:'门店编码',required:true},{key:'name',label:'门店名称',required:true},{key:'type',label:'经营类型',kind:'select',required:true,options:[{label:'直营店',value:'DIRECT'},{label:'加盟店',value:'FRANCHISE'},{label:'商场联营',value:'CONSIGNMENT'}]},{key:'region',label:'所属区域',maxLength:64},{key:'contact_phone',label:'联系电话',maxLength:32},{key:'address',label:'地址'}]
const columns=fields.filter(f=>['code','name','type','region','contact_phone'].includes(f.key))
</script><template><ArchiveTable path="/stores" title="门店管理" label="门店" description="建立门店信息，为每家门店连接仓库与商品。" :fields="fields" :columns="columns" /></template>
