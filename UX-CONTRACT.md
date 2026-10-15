# 我川后台交互契约

## 商品保存与采购进货

规格明细每行显示颜色、码数、条码、零售价、本次进货数量。数量留空/0不入库；正整数数量要求供应商、收货仓库和非负进货单价，默认采购基准价可改。数量表示本次增量，成功后重新编辑为空。
保存只发送一个商品请求，商品、SKU、采购单、库存和流水由后台同一事务提交，失败保留输入。UUID与内容指纹防止重试重复入库；相同请求改内容须明确拒绝。
库存与流水只能查询，来源必须是已入库单据。查询失败显示错误，不伪造空结果。连续查看不同采购单时，旧成功/失败响应不得覆盖当前单据或加载状态。

## 商品选项补充（2026-10-15）

品类与面料成分从独立档案选择；品类默认面料全体共享，仅商品事务提交成功后记忆。加载已有商品不得覆盖其面料选项；切换品类才应用默认值。已停用默认不带入新选择。
颜色、尺码组共用ChoiceList，每类最多10个有序常用项，可替换/排序；颜色多选、尺码组单选，不采用颜色下拉。已有颜色保留，可追加完整尺码的新颜色；原SKU ID和条码不变。
字典管理在新标签打开，刷新字典保留商品输入、匹配规格价格和条码，同时同步新建草稿的最新尺码项。商品明细每行一个规格，显示颜色、码数、条码和零售价。

业务来源：已批准foundation-design.md。所有页面共享以下行为，中文locale为zh-CN。

## Canonical UI Map

| Capability | Canonical owner | Source of truth | Allowed variants | Verification |
|---|---|---|---|---|
| Select/Listbox | Element Plus ElSelect | DESIGN.md | single/multiple | browser select popup |
| Form | ArchiveEditor + ElForm | this contract | create/edit | component and browser tests |
| Scrollbar | frontend/src/styles.css | DESIGN.md | matrix horizontal | browser narrow viewport |
| Toast | Element Plus ElMessage | this contract | success/error | component and browser tests |
| CRUD | ArchiveTable + apiRequest | approved design | modal archives/product route | API and browser full flow |

## Lists and recovery
服务端分页默认20、最大100。搜索、状态、page与page_size保存在URL中；筛选变化重置page=1。搜索300ms防抖、IME完成后请求、取消旧请求；明确清除按钮。没有匹配结果与加载失败分别展示，失败不能显示假空列表。
当前页越界时回到可用页。列表不提供多选批量操作或排序（首批仅稳定id倒序），不出现无效控件。

## Forms and outcomes
所有产品form novalidate；ElForm提供字段验证，提交时定位首个错误，错误不只用toast。创建/编辑档案成功关闭弹窗并刷新原列表；商品保存回商品列表。取消回原页面，存在未保存输入时用ElMessageBox确认。
保存期间按钮busy且不重复提交；失败保留输入。密码默认掩码并允许显示切换；不使用localStorage保存密码或会话。
停用确认说明对象与后果；重新启用可直接执行。禁止浏览器原生alert/confirm/prompt。所有模态采用Element Plus焦点管理和Escape行为。

## Navigation and permissions
后台路由先验证服务端会话，401回登录并保留原目标；403独立提示；未知路由有返回工作台入口。退出调用后端撤销会话，后端失败时保留失败提示而非声称已退出。
首次安装数据为空，工作台指引建立门店/仓库/供应商/商品，不注入样例或虚构指标。

## Input and localization
编码ASCII、名称中文、金额字符串人民币、时间上海时区；数字不能用浮点计算。ElConfigProvider zh-CN统一分页和控件文案。select由ElSelect统一拥有，日期首批只有年份文本输入，没有日历需求。

## Resilience and accessibility
错误内联role=alert，成功反馈统一ElMessage及status live区。无秘密出现在URL、日志和界面错误。
页面自然纵向滚动，表格与矩阵内部横向滚动；窄屏保留入口和保存操作。label关联实际input；键盘focus可见；reduced motion关闭动画。
