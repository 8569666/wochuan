<script setup lang="ts">
import ArchiveTable from '../components/ArchiveTable.vue'
import type { FieldSpec } from '../api/types'
const fields:FieldSpec[]=[{key:'code',label:'品类编码',required:true},{key:'name',label:'品类名称',required:true,maxLength:64}]
</script><template><ArchiveTable path="/categories" title="品类管理" label="品类" description="统一维护品类；商品保存成功后，记忆该品类最后使用的面料成分，供全体操作员使用。" :fields="fields" :columns="fields"><template #actions><router-link to="/products"><el-button>返回商品中心</el-button></router-link></template></ArchiveTable></template>
