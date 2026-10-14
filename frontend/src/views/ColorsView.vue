<script setup lang="ts">
import ArchiveTable from '../components/ArchiveTable.vue'
import type { FieldSpec } from '../api/types'
const fields:FieldSpec[]=[{key:'code',label:'颜色编码',required:true,maxLength:16,placeholder:'例如 C01，仅字母、数字和下划线'},{key:'name',label:'颜色名称',required:true},{key:'hex_value',label:'色值',placeholder:'例如 #F3E7D4',maxLength:7}]
</script><template><ArchiveTable path="/colors" title="颜色管理" label="颜色" description="维护商品矩阵可选颜色；已被引用的颜色编码不可修改。" :fields="fields" :columns="fields"><template #actions><router-link to="/products"><el-button>返回商品中心</el-button></router-link></template></ArchiveTable></template>
