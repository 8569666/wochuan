# 人员架构与权限第一批

用户已选择开发上一轮建议的第一批，并授权后续可自主完成的操作。范围：组织、岗位、员工、任职历史、入转调离、账号绑定、角色/数据范围、日志。沿用Vue3/Python3.14/MySQL。现有业务单据的仓库、操作人ID不随调岗修改。

## 后台契约（共同开发接口）

`/api/v1/people`下所有列表返回Page。组织`org-units` CRUD软停用，`org-units/tree`返回children树；岗位`positions` CRUD软停用；员工`employees`列表/新建/详情/编辑基本资料，`employees/me`本人档案，`employees/{id}/events` POST异动。角色`roles`列表/新建/修改，`permissions`返回权限目录与scope_types。账号：`employees/{id}/account` POST绑定新账号，`accounts/{id}` PATCH启停/重置密码；`accounts/{id}/grants` PUT替换完整授权。

组织OrgUnit：id/code/name/status(ACTIVE/INACTIVE)/kind(COMPANY,HQ,REGION,DEPARTMENT,STORE,WAREHOUSE)/parent_id/store_id/warehouse_id。STORE/WAREHOUSE唯一关联既有业务档案，显示业务档案现名；不复制业务数据。根必须COMPANY，不能循环、无效父级不能使用。关联门店仓库由内置管理员管理，停用有有效子节点或未离职员工的组织须拒绝。

岗位Position：id/code/name/status。为共享字典，全局写授权才能编辑；引用中的岗位不能停用。

Employee：id/code(工号)/name/phone/personnel_type(EMPLOYEE,CONTRACTOR,PARTNER,TEMP)/status(PENDING,PROBATION,ACTIVE,LEFT)/company_id/org_unit_id/position_id/manager_id/hire_date/confirmation_date/left_date。创建输入公司可省略，由org_unit归属推导；不采集身份证银行卡薪资。编辑仅name/phone/personnel_type。manager必须同公司有效员工，不能自指或成环。

Assignment：employee_id/org_unit_id/position_id/manager_id/effective_from/effective_to(结束日不包含当天)，保留每次主职任职。PersonnelEvent：employee_id/kind(ONBOARD,CONFIRM,TRANSFER,LEAVE)/effective_date/reason/handover_employee_id/handover_notes/before_data/after_data/actor_id。首批事件只记录已经生效的异动，不做未来自动调度；调岗日期不能早于当前任职开始，跨公司调岗不在本批。

员工详情返回基础列、company_name/org_unit_name/position_name/manager_name、assignments、events、account安全摘要。账号不返回password_hash。User新增employee_id(可空，仅内置管理员可无员工)，普通账号role=STAFF。新建账号输入username/password(至少12位)/enabled，启用要求员工PROBATION/ACTIVE。离职同时停账号、撤销会话，禁止直接重新启用离职账号。调岗撤销会话和全部旧授权；若内置管理员事件请求附带grants，则同事务配置新授权，否则员工重新登录仅可查看本人资料，待管理员授权。更换岗位不自动继承原权限。

Role在`app.modules.access.models`：Archive + permissions(JSON字符串列表)。UserRoleGrant：Record + user_id/role_id/scope_type/scope_ids(JSON整数数组)，同用户/角色/范围类型唯一。scope_type为ALL、ORG_TREE、STORES、WAREHOUSES、HOME、SELF；ALL/HOME/SELF的scope_ids必须为空。HOME动态使用员工当前org子树。账户和角色授权配置仅内置ADMIN可执行，普通角色不能自提权。岗位与角色分开，一人可有多个角色/范围。

## 权限公共接口（access/service.py）

AccessContext：user(User)、id、is_admin、employee_id、permissions(set)、global_permissions(set)，has(permission,global_scope=False)、org_unit_ids(permission)、store_ids(permission)、warehouse_ids(permission)、employee_ids(permission)均返回set[int]或None(全量)；allows_org/ allows_store/ allows_warehouse/ allows_employee(permission,id)返回bool。导出AccessDep与require_permission(access,permission,global_scope=False)。每个请求实时解析有效员工、有效角色与授权；只有包含该权限的角色参与范围合并，不能把无关角色范围串用。

权限目录PERMISSION_CATALOG为code→中文label：dashboard.read、org.read/org.manage、position.read/position.manage、employee.read/employee.manage/employee.transfer/employee.leave、employee.self、account.manage、role.manage、audit.read、store.read/store.write、warehouse.read/warehouse.write、supplier.read/supplier.write、catalog.read/catalog.write/catalog.cost、purchase.read/purchase.receive、inventory.read。

登录与me输出原User字段及employee_id、permissions、global_permissions、is_admin；可附roles摘要。内置ADMIN兼容现有全部功能。普通员工可登录且可读本人；无业务权限时默认去/my-profile。菜单、按钮配合权限，但API也必须检查。未授权记录详情返回404或403；禁止通过列表、详情、搜索、分页总数、仪表盘、SKU子接口绕过。

业务：Store/Warehouse按permission范围过滤；供应商/商品共享档案允许有读权限的员工读，写需要该write权限的ALL授权。采购入库需要purchase.receive且目标仓库在其范围；商品新增还需catalog.write全局授权；已有商品receiving-only PATCH可由入库权限执行，商品元数据/价格变更另需catalog.write全局。采购成本须catalog.cost：商品采购基准价仅全局成本权限可见，库存和采购单/明细成本按目标仓库成本范围隐藏。普通角色没有入库权限时不能因能编辑商品而加库存。

## 前端

复用现有表单、状态、错误保留与未保存确认。新增组织树/岗位/员工（详情及异动）/角色/账号授权入口及本人档案。组织、员工列表支持过滤分页；管理动作受权限限制。角色权限目录显示中文，不让用户填内部权限字符串。账号配置由ADMIN进入员工详情完成，密码不显示在列表/日志中；调岗撤旧权限的后果在提交前说明。

库存/采购隐藏成本列；商品界面无写权限时只读，有入库权限可填本次数量，构建receiving-only请求。没有业务权限的员工进入本人档案。现有ADMIN行为不变。

## 验收

独立测试库覆盖组织循环/员工工号唯一、manager循环、入转调离历史、账号绑定、停用/离职已有会话立即失效、转岗撤旧授权、按权限分别合并范围、本店/所辖区域/指定仓库隔离、成本字段脱敏、商品编辑不能越权入库。全套旧47后台与23前端回归；真实浏览器新组织/岗位/员工/异动流程、员工只读和权限错误。开发库只增量迁移/种角色，不放真实员工或测试账号。
