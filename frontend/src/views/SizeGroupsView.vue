<script setup lang="ts">
import ArchiveTable from '../components/ArchiveTable.vue'
import type { FieldSpec } from '../api/types'
const fields:FieldSpec[]=[{key:'code',label:'尺码组编码',required:true},{key:'name',label:'尺码组名称',required:true},{key:'sizes',label:'尺码项',kind:'sizes',required:true,placeholder:'用英文逗号分隔，例如 S,M,L,XL',maxLength:500}]
</script><template><ArchiveTable path="/size-groups" title="尺码组管理" label="尺码组" description="按显示顺序填写尺码；已被商品引用的规格组合不能修改。" :fields="fields" :columns="fields"><template #actions><router-link to="/products"><el-button>返回商品中心</el-button></router-link></template></ArchiveTable></template>
