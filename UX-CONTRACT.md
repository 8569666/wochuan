# 我川后台交互契约

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
