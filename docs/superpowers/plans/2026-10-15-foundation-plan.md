# 总部后台与基础档案 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 交付能本地启动、登录、持久化维护门店/仓库/供应商并创建3色4码商品矩阵的中文后台。

**Architecture:** Vue前端通过同源代理调用FastAPI模块化单体。后端使用SQLAlchemy异步事务和aiomysql连接用户已有MySQL，Alembic维护专属项目表；以真实数据库集成测试和浏览器验收验证闭环。

**Tech Stack:** Python 3.14、FastAPI、Pydantic v2、SQLAlchemy asyncio、aiomysql、Alembic、MySQL 8.0.46、Vue 3、TypeScript、Vite、Pinia、Element Plus、npm。

**Spec:** `docs/superpowers/specs/2026-10-15-foundation-design.md`（用户已审核通过）。

## Global Constraints

- 项目目录 D:\Codex\wochuan；保持当前仓库，所有产物在本项目目录内，敏感配置不提交。
- Python 3.14，开发数据库MySQL 8.0.46/codex_db；复用根.env的DB_*字段并兼容MYSQL_*别名，同名MYSQL_*优先，不输出连接串。
- 默认本机frontend 5173、backend 8000；后端使用独立.venv，前端npm/package-lock.json。
- 所有项目表及迁移版本表使用werp_前缀、InnoDB、utf8mb4、BIGINT主键；时间DATETIME(6)存UTC，界面Asia/Shanghai；金额DECIMAL(12,2)/字符串。
- 会话8小时、HttpOnly/SameSite=Strict；生产HTTPS启用Secure；无公开默认管理员密码。
- 不物理删除业务档案，不引入Redis、不修改其他表，不实现库存、采购、POS或财务。
- 首批不注入演示数据；工作台只显示真实档案统计。
- 每项业务功能先写能反映需求的失败测试，再实现并验证；可逆低风险配置不单独堆砌测试。

## Review Focus

- 密码含空格、#、引号或URL特殊字符时不被拼接/解析损坏，凭据不出现在日志（Task 1/3）。
- 同一编码两次并发创建，只成功一次，另一请求409，事务可继续使用（Task 4/5）。
- 已引用的字典停用或改编码，不得破坏已有SKU，旧商品详情仍能显示（Task 5）。
- 小数金额、矩阵遗漏/重复规格、超长编码应明确拒绝，不能生成半套商品（Task 5/7）。
- 数据库失联或提交失败，页面提示失败且保留输入，不能显示零条伪装成功（Task 1/6/7）。

## 文件与责任划分

- `backend/app/main.py`：应用工厂、路由注册、错误封装与健康检查；`core/config.py`、`core/database.py`：配置和连接生命周期。
- `backend/app/modules/{auth,organization,suppliers,catalog}/`：各模块的models/schemas/service/router；`modules/audit/`：审计模型和写入服务。
- `backend/app/common/{responses,pagination,errors}.py`：共享响应、分页、领域错误；`backend/app/cli.py`：管理员初始化和环境诊断。
- `backend/alembic/`：迁移；`backend/tests/`：真实MySQL测试和业务验收；`backend/pyproject.toml`、`backend/requirements.lock`：依赖及工具配置。
- `frontend/src/api/`、`stores/auth.ts`、`router/index.ts`：契约/请求/会话/导航；`layouts/AdminLayout.vue`、`views/`、`components/`：后台页面和共享交互。
- `.env.example`、`scripts/{start,stop,setup}.ps1`、`README.md`：配置说明与Windows运行；`docs/verification/`记录实际验收结果，不存密码和会话。

## Task 1：运行环境、异步连接与健康检查

**Files:** 创建 backend/pyproject.toml、backend/requirements.lock、backend/app/main.py、backend/app/core/config.py、backend/app/core/database.py、backend/app/common/responses.py、backend/tests/test_config.py、backend/tests/test_health.py、.env.example。

**Interfaces:** `get_settings() -> Settings`；`Settings.database_url -> sqlalchemy.engine.URL`；`get_session() -> AsyncIterator[AsyncSession]`；`create_app(settings: Settings | None = None) -> FastAPI`；`GET /api/v1/health/live`、`GET /api/v1/health/ready`。

- [ ] 在.venv中安装Python 3.14兼容稳定依赖：fastapi、uvicorn、pydantic-settings、sqlalchemy[asyncio]、aiomysql、PyMySQL[rsa]、alembic、pytest、pytest-asyncio、httpx、ruff；锁定已实际安装版本。此项先验证解释器及依赖导入，不创建业务表。
- [ ] 编写失败测试：`test_db_aliases_and_special_password`断言URL.password等于原值；`test_ready_returns_503_when_db_unavailable`断言HTTP 503；`test_live_does_not_require_database`断言HTTP 200。
- [ ] 执行 `.venv\Scripts\python -m pytest backend/tests/test_config.py backend/tests/test_health.py -q`，确认因功能未实现失败。
- [ ] 实现配置：用dotenv解析根.env而非字符串拼接，连接用URL.create；环境变量覆盖文件，默认允许origin为http://127.0.0.1:5173；pool_pre_ping开启。使用当前本地配置执行只读SELECT 1及异步rollback兼容性检查，不写入开发库。
- [ ] 实现统一响应code/message/data/timestamp与安全异常处理；数据库失联就绪接口503，不输出堆栈或URL；重跑测试并记录真实3.14导入/连接结果。
- [ ] 提交 `feat: bootstrap Python 3.14 API and MySQL connection`。

## Task 2：首个迁移与安全测试环境

**Files:** 创建 backend/alembic.ini、backend/alembic/env.py、backend/alembic/versions/0001_foundation.py、各模块models.py、backend/tests/conftest.py、backend/tests/test_migrations.py。

**Interfaces:** SQLAlchemy统一`Base.metadata`；`upgrade_database(settings: Settings) -> None`供迁移入口使用；pytest提供`db_session: AsyncSession`及`client: httpx.AsyncClient`。

- [ ] 模型定义覆盖werp_users、werp_sessions、werp_auth_limits、werp_stores、werp_warehouses、werp_suppliers、werp_colors、werp_size_groups、werp_sizes、werp_products、werp_skus、werp_audit_logs；版本表为werp_alembic_version。
- [ ] 编写失败测试`test_migration_roundtrip_on_test_database`：upgrade后项目表均存在、engine为InnoDB、中文列为utf8mb4、重复upgrade无变化；`test_refuse_development_database_cleanup`断言测试库名等于开发库时拒绝执行。
- [ ] 测试库使用`codex_werp_test`，由专用测试配置指定；仅该测试库可重置werp_表，验证库名与开发库不同后才能执行迁移/清理。不执行DROP DATABASE。权限不足时报告，不用SQLite代替。
- [ ] 实现显式Alembic迁移、BIGINT一致外键、SKU组合/编码/条码唯一约束、仓库store_id可空唯一约束；引用用RESTRICT，数据库不级联删除业务档案。连接会话设UTC，时间由UTC aware应用值转换为UTC naive写入DATETIME。
- [ ] 执行迁移测试；通过后向codex_db执行首个upgrade，仅创建werp_表；验证没有默认业务记录。模型不使用启动时create_all代替迁移。
- [ ] 提交 `feat: add foundation schema and isolated MySQL tests`。

## Task 3：管理员初始化、登录、会话与审计

**Files:** 创建 backend/app/modules/auth/{schemas,security,service,router}.py、backend/app/modules/audit/service.py、backend/app/cli.py、backend/tests/test_auth.py。

**Interfaces:** `hash_password(password: str) -> str`、`verify_password(password: str, encoded: str) -> bool`；`require_admin(request: Request, session: AsyncSession) -> User`；`record_audit(session: AsyncSession, actor_id: int, action: str, entity_type: str, entity_id: int, changes: dict) -> None`。

- [ ] 写失败测试：`test_login_logout_and_expiry`断言Cookie HttpOnly/SameSite strict、过期和退出后401；`test_disabled_user_and_missing_cookie_rejected`断言401；`test_wrong_origin_rejected`断言写请求403；`test_password_special_characters_roundtrip`断言密码原样验证。
- [ ] 加入`test_failed_login_rate_limit`：相同用户名与来源IP在15分钟内5次失败，第6次429；有效会话不因另一个用户失败受影响；错误登录不得泄露账号存在性。
- [ ] 执行 `.venv\Scripts\python -m pytest backend/tests/test_auth.py -q`，确认失败。
- [ ] 实现scrypt（n=16384,r=8,p=1，随机16字节盐、64字节摘要，常量时间比较）；会话令牌secrets.token_urlsafe(32)，只存SHA256摘要，过期8小时。限流使用数据库桶/锁处理，读取真实连接IP，不信任未配置代理的请求头。
- [ ] 实现POST /auth/login、POST /auth/logout、GET /auth/me；Cookie本地不设Secure，生产开关显式开启；登录/退出和档案修改均有审计，凭据字段永不入审计。
- [ ] 实现 `python -m app.cli init-admin`，交互读取用户名和两次密码，已有账号拒绝覆盖；测试使用随机临时账号，不设固定默认密码。验证接口及初始化命令后提交 `feat: add administrator authentication and audit`。

## Task 4：门店、仓库、供应商档案接口

**Files:** 创建 backend/app/modules/organization/{schemas,service,router}.py、backend/app/modules/suppliers/{schemas,service,router}.py、backend/app/common/{errors,pagination}.py、backend/tests/test_archives.py。

**Interfaces:** 认证依赖Task 3；`Page[T]`包含items/total/page/page_size；HTTP /stores、/warehouses、/suppliers的GET/POST/PATCH；规范字段code/name/status（ACTIVE/INACTIVE）。门店type DIRECT/FRANCHISE/CONSIGNMENT；仓库type CENTRAL/STORE/TRANSIT/DEFECT。

- [ ] 写失败测试`test_archive_crud_pagination_and_inactive`、`test_store_warehouse_binding_rules`、`test_concurrent_duplicate_code`、`test_archive_requires_admin`；断言编码trim/uppercase、默认page_size=20、上限100、STORE必须绑定店、其他类型不能绑定、一店只一个店仓、并发重复一个201另一个409。
- [ ] 执行 `.venv\Scripts\python -m pytest backend/tests/test_archives.py -q`确认失败。
- [ ] 实现GET列表/详情、POST创建、PATCH编辑及启停用；仓库创建必须引用有效门店，已停用的关联店仍能在历史详情显示。不提供DELETE；IntegrityError回滚为409，业务变更与审计同一事务。
- [ ] 所有列表关键词按名称/编码查询，status可过滤，稳定按id倒序分页；编辑重复编码排除自身，未知id返回404，未登录401。
- [ ] 重跑测试并验证总仓/两门店/店仓流程在测试库可完成，提交 `feat: add store warehouse and supplier archives`。

## Task 5：颜色尺码字典与原子商品矩阵接口

**Files:** 创建 backend/app/modules/catalog/{schemas,service,router}.py、backend/tests/test_catalog.py、backend/tests/test_dashboard.py。

**Interfaces:** /colors、/size-groups按档案规范GET/POST/PATCH；`create_product(session: AsyncSession, actor: User, payload: ProductCreate) -> ProductDetail`；/products GET/POST、/{id} GET/PATCH、/{id}/skus GET；GET /dashboard/summary返回五类真实档案总量。

- [ ] 创建请求字段：code/name/category/year/season/wave_band/fabric_composition/safety_category/tag_price/purchase_base_price/min_retail_price/color_ids/size_group_id/skus。SKU项为color_id/size_id/retail_price/barcode（可空，生成内部码）；展示SKU返回code/barcode/color/size及价格字符串。
- [ ] 写失败测试`test_three_colors_four_sizes_create_twelve_skus`断言12条、组合唯一、SKU码与缺省条码为款号-颜色码-尺码码；`test_duplicate_barcode_rolls_back_whole_product`断言409且无新SPU/SKU/审计；`test_missing_or_repeated_matrix_cell_is_422`。

  矩阵成功用例的核心断言（response为3色4码创建请求的返回）：

  ```python
  assert response.status_code == 201
  skus = response.json()["data"]["skus"]
  assert len(skus) == 12
  assert len({sku["code"] for sku in skus}) == 12
  assert all(sku["barcode"] == sku["code"] for sku in skus)
  assert all(sku["retail_price"] == "599.00" for sku in skus)
  ```
- [ ] 加入`test_decimal_precision_and_code_length`断言金额"599.00"原样返回、负数及多于两位小数拒绝、SKU码超过64字符拒绝；`test_referenced_dictionary_code_immutable`、`test_inactive_dictionary_preserves_existing_detail`、`test_concurrent_product_code_unique`。
- [ ] 执行 `.venv\Scripts\python -m pytest backend/tests/test_catalog.py backend/tests/test_dashboard.py -q`确认失败。
- [ ] 实现矩阵组合完整性及独立服务端校验；代码字段大小写规范化、颜色尺码[A-Z0-9_]+；SPU允许[A-Z0-9_-]+；颜色值为可空#RRGGBB。字典只能选有效项；已有SKU的编码/条码/组合只读，修改价格由明确SKU价格映射处理，不改历史组合。
- [ ] SPU+SKU+审计一个事务；无库存接口、不填写虚假移动成本；款号/名称/条码搜索使用关联查询且不重复计数。工作台计数以数据库为准。
- [ ] 重跑测试，提交 `feat: add atomic product matrices and catalog dictionaries`。

## Task 6：中文后台骨架、登录与基础档案页面

**Files:** 创建 frontend/package.json、frontend/package-lock.json、frontend/vite.config.ts、frontend/src/{main.ts,App.vue}、frontend/src/api/{client,types}.ts、frontend/src/stores/auth.ts、frontend/src/router/index.ts、frontend/src/layouts/AdminLayout.vue、frontend/src/views/{LoginView,DashboardView,StoresView,WarehousesView,SuppliersView}.vue、frontend/src/components/ArchiveTable.vue、frontend/src/styles.css、frontend/src/tests/archives.spec.ts。

**Interfaces:** `apiRequest<T>(path: string, options?: RequestInit): Promise<T>`；共享ApiResponse<T>/Page<T>与后端契约一致；auth store exposes loadSession/login/logout；列表组件以查询函数及编辑表单slot组合，不写万能schema表单引擎。

- [ ] 实施UI前读取适用的frontend-app-builder、frontend-design与frontend-design-premium技能，建立该项目设计上下文，沿用Vue/Element Plus，不因技能示例切换React。浏览器测试优先现有Browser工具。
- [ ] UI方向：中文服装总部运营台，暖白底、深蓝导航、低饱和强调色，清晰表格/表单；不加入无数据的经营图表。页面可用键盘导航、输入有标签、状态不只靠颜色表达。
- [ ] 写交互失败测试：401后回登录、登录后回原目标路由、登录失败显示错误、创建编辑停用刷新列表；503列表显示错误而非空状态；提交失败保留字段；重复点击只发一次请求。
- [ ] 执行 `npm --prefix frontend run test -- --run`确认失败，再实现路由守卫、Cookie请求、/api代理、错误提示和真实工作台统计。登录页无注册和默认密码提示。
- [ ] 完成门店仓库供应商搜索/分页/启停用，仓库表单只在STORE时允许绑定门店；小屏保持操作可见，表格可横向滚动。
- [ ] 执行前端测试、`npm --prefix frontend run typecheck`及`npm --prefix frontend run build`，通过后提交 `feat: build Chinese admin shell and archive screens`。

## Task 7：商品矩阵页面与字典管理

**Files:** 创建 frontend/src/views/{ProductsView,ProductEditorView}.vue、frontend/src/components/{SkuMatrix,ColorManager,SizeGroupManager}.vue、frontend/src/tests/catalog.spec.ts；修改前端router和api类型。

**Interfaces:** `SkuMatrix`输入colors、sizes、modelValue，输出update:modelValue，单元格保存color_id/size_id/retail_price/barcode；商品编辑路由/products/new与/products/:id；字典在商品中心管理入口访问。

- [ ] 写失败测试：选3色4码渲染12个组合、批量价格仅更新当前矩阵、移除选择不误保留旧格、未填写必要字段不能提交、409不丢输入、已有商品编码/维度只读。
- [ ] 矩阵按颜色行/尺码列显示，金额保持字符串，不用JS浮点计算；规格编码与条码生成预览仅作交互，保存结果以服务端返回为准。默认条码清楚注明“内部条码”。
- [ ] 新建颜色/尺码组后刷新字典；已有引用编码锁定。创建和编辑分开能力，已有商品只编辑设计允许的描述/价格/状态。
- [ ] 确认前端测试先失败再通过，类型检查和构建通过，提交 `feat: add product matrix editor and dictionary management`。

## Task 8：Windows启动、真实浏览器验收与交付

**Files:** 创建 scripts/{setup,start,stop}.ps1、README.md、backend/tests/test_acceptance.py、docs/verification/2026-10-15-foundation.md；修改.env.example补齐非敏感运行选项。

**Interfaces:** setup检查Python3.14、依赖、MySQL，显式迁移并指引init-admin；start后台隐藏启动前后端并记录进程ID；stop只停止已记录且路径匹配本项目的进程，不能按端口杀其他进程。

- [ ] 编写真实MySQL验收测试：登录→一个总仓→两家门店及店仓→供应商→3颜色/4尺码→商品12SKU→按条码搜索→刷新查看→启停用；断言数据库和接口数目一致、审计存在、非登录访问被拒绝。
- [ ] 执行后端完整测试、ruff、前端完整测试/类型检查/构建；新失败才扩大检查，不无意义重复已通过项目。
- [ ] 浏览器验收启动独立测试库配置的服务（API8001、前端5174），测试账号为运行时随机凭据；页面操作验证登录/档案/矩阵/错误状态，截取主要页面并检查控制台；测试记录不得含密码和Cookie。
- [ ] 验证重启API后商品依然可读；测试结束只清理独立测试库记录，开发库不注入演示业务数据。正常开发入口按默认8000/5173启动。
- [ ] README包含配置项、安装/迁移/管理员初始化/启动停止/测试命令、第一批边界和已知限制；验收报告填写实际命令结果与未通过项，不预填“通过”。不执行drop数据库或自动覆盖管理员。
- [ ] 完成后审查Git差异和敏感文件排除、对照设计逐项检查，提交 `feat: deliver runnable foundation admin and verification guide`；按执行方式安排最终独立代码审核，修复影响范围内问题并重跑相关检查。

## 自审与执行交接

- [x] 覆盖设计的配置、迁移、登录、审计、五类档案、矩阵、真实统计、Windows启动与持久化验收。
- [x] 故障重点各自落到所属任务的测试，跨任务响应、字段与路由一致。
- [x] 开发库/测试库隔离明确，没有占位需求，不在计划阶段建表或安装产品依赖。
- [ ] 用户审核本实施计划并选择执行方式。

推荐在当前会话由主代理依次实施：八项任务共享认证、事务及数据契约，连续执行容易保持接口一致，也减少每项重新传递上下文的成本。另一选择是按任务使用独立子代理实施/审核，资源开销更高。
