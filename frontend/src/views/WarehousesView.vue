<script setup lang="ts">
import ArchiveTable from '../components/ArchiveTable.vue'
import type { FieldSpec } from '../api/types'
const fields:FieldSpec[]=[{key:'code',label:'仓库编码',required:true},{key:'name',label:'仓库名称',required:true},{key:'type',label:'仓库类型',kind:'select',required:true,options:[{label:'中央总仓',value:'CENTRAL'},{label:'门店仓库',value:'STORE'},{label:'在途仓',value:'TRANSIT'},{label:'残次仓',value:'DEFECT'}]},{key:'store_id',label:'关联门店',kind:'select',endpoint:'/stores',required:true}]
</script><template><ArchiveTable path="/warehouses" title="仓库管理" label="仓库" description="配置总仓与门店仓库，每家门店最多一个默认店仓。" :fields="fields" :columns="fields.slice(0,3)" /></template>
