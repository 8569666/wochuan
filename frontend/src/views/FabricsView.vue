<script setup lang="ts">
import ArchiveTable from '../components/ArchiveTable.vue'
import type { FieldSpec } from '../api/types'
const fields:FieldSpec[]=[{key:'code',label:'面料编码',required:true},{key:'name',label:'面料名称',required:true},{key:'composition',label:'面料成分',kind:'textarea',required:true,maxLength:2000,placeholder:'例如 95%棉，5%氨纶'}]
</script><template><ArchiveTable path="/fabrics" title="面料成分管理" label="面料成分" description="建立可重复选用的面料成分档案。" :fields="fields" :columns="fields"><template #actions><router-link to="/products"><el-button>返回商品中心</el-button></router-link></template></ArchiveTable></template>
