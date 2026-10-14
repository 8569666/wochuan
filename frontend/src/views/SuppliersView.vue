<script setup lang="ts">
import ArchiveTable from '../components/ArchiveTable.vue'
import type { FieldSpec } from '../api/types'
const fields:FieldSpec[]=[{key:'code',label:'供应商编码',required:true},{key:'name',label:'供应商名称',required:true},{key:'contact_name',label:'联系人',maxLength:64},{key:'contact_phone',label:'联系电话',maxLength:32},{key:'settlement',label:'结算方式',kind:'select',required:true,options:[{label:'现结',value:'现结'},{label:'月结30天',value:'月结30天'},{label:'滚动账期',value:'滚动账期'}]},{key:'address',label:'地址'},{key:'notes',label:'备注',kind:'textarea',maxLength:2000}]
</script><template><ArchiveTable path="/suppliers" title="供应商管理" label="供应商" description="维护供应商联系方式和结算信息。" :fields="fields" :columns="fields.slice(0,5)" /></template>
