<script setup lang="ts">
import ArchiveTable from '../components/ArchiveTable.vue'
import type { FieldSpec } from '../api/types'
const columns:FieldSpec[]=[{key:'code',label:'款号'},{key:'name',label:'款名'},{key:'category',label:'品类'},{key:'season',label:'季节'},{key:'tag_price',label:'吊牌价（元）'},{key:'sku_count',label:'规格数'}]
</script><template><ArchiveTable path="/products" title="商品中心" label="商品" description="以款号管理商品，用颜色尺码矩阵建立每一个规格。" :fields="[]" :columns="columns" product-route search-placeholder="搜索款号、款名或条码"><template #actions><router-link to="/categories"><el-button>品类管理</el-button></router-link><router-link to="/fabrics"><el-button>面料成分管理</el-button></router-link><router-link to="/colors"><el-button>颜色管理</el-button></router-link><router-link to="/size-groups"><el-button>尺码组管理</el-button></router-link></template></ArchiveTable></template>
