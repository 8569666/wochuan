# 我川 W-ERP · 总部基础档案后台

首批可运行版本：管理员登录、门店、仓库、供应商、颜色尺码字典、商品矩阵和真实档案统计。
当前未包含采购入库、库存数量、收银支付、会员或财务。

## 环境

- Windows / PowerShell，Python **3.14**，Node.js **22.12+或24**，MySQL **8.0.46**兼容目标。
- Vue 3、Element Plus、FastAPI、SQLAlchemy异步、aiomysql、Alembic。
- 数据库使用InnoDB/utf8mb4，项目表名以`werp_`开头。

## 当前机器直接使用

运行 `scripts/start.ps1`，打开 [总部后台](http://127.0.0.1:5173)。后端在本机8000端口。
管理员用户名为 `admin`，随机初始密码保存在项目本地 `.cache/initial-admin.txt`，该文件被Git忽略。首次凭据不是公开默认密码；请在受控设备上使用，不分享该文件。
停止服务运行 `scripts/stop.ps1`。启动/停止脚本只管理本项目记录的进程。

```powershell
cd D:\Codex\wochuan
.\scripts\start.ps1
.\scripts\stop.ps1
```

## 新机器初始化

1. 参考根目录 `.env.example` 填写 `.env`，账号需要开发库的建表及读写权限。
2. 在项目目录运行 `scripts/setup.ps1`：安装锁定依赖、验证连接、迁移项目表，交互创建管理员。
3. 运行 `scripts/start.ps1`，访问5173。浏览器入口使用`127.0.0.1`，与配置的Origin保持一致。

配置字段支持 `DB_HOST/DB_PORT/DB_DATABASE/DB_USERNAME/DB_PASSWORD`，也支持`MYSQL_HOST/MYSQL_PORT/MYSQL_DATABASE/MYSQL_USER/MYSQL_PASSWORD`，同名`MYSQL_*`优先。密码中的#、空格或引号按标准dotenv语法正确引用。`.env`不提交。
`APP_ORIGIN`默认`http://127.0.0.1:5173`；`COOKIE_SECURE`仅在HTTPS部署时开启。

单独执行命令：

```powershell
cd D:\Codex\wochuan\backend
..\.venv\Scripts\python -m app.cli check-db
..\.venv\Scripts\python -m app.cli migrate
..\.venv\Scripts\python -m app.cli init-admin
```

管理员初始化不会覆盖已有账号。开发库迁移仅管理`werp_`项目表，启动服务不会自动重建或清空表。

## 日常操作

1. 门店管理中新建门店；仓库管理中创建中央总仓，并为每家门店配置一个店仓。
2. 供应商管理中维护联系人和结算方式。
3. 商品中心进入颜色管理、尺码组管理，建立颜色与顺序明确的尺码项。
4. 新建商品，填写款号/款名/品类/年份/价格，选择颜色和尺码组，检查矩阵后保存。
5. 商品支持按款号、名称或条码查询。3色4码应生成12个SKU，默认内部条码为规格编码。

档案支持编辑、启用和停用，不提供物理删除。已生成商品的款号、条码和规格组合固定，可编辑描述和价格；字典已引用的编码不能修改。内部条码不是注册EAN-13编号。采购基准价是参考价格，不是已核算的库存成本。
列表搜索与分页保存在地址中；保存失败保留输入。写请求遇到会话过期时，可按页面提示在新标签页重新登录，再回到原页面重试。

## 测试与验证

后端真实MySQL测试只允许`codex_werp_test`，不得设为开发库。管理员先创建该库，并授权项目账号读写/建表；测试会清理该独立库的`werp_`表记录，不影响`codex_db`。

```powershell
cd D:\Codex\wochuan
.venv\Scripts\python -m pytest backend/tests -q
.venv\Scripts\python -m ruff check backend
.venv\Scripts\python -m ruff format backend --check
npm --prefix frontend run test -- --run
npm --prefix frontend run typecheck
npm --prefix frontend run build
npm --prefix frontend run check:design
```

浏览器独立测试入口：`scripts/start.ps1 -TestMode`使用5174/8001与`codex_werp_test`；停止时同样加`-TestMode`。验收账号由测试过程单独创建，不能用来登录开发库。
验证记录见`docs/verification/2026-10-15-foundation.md`，接口文档见[本地OpenAPI](http://127.0.0.1:8000/docs)。

## 开发管理

设计与任务计划位于`docs/superpowers/`。每项业务改动先补需求测试，验证失败后实现，再跑相关测试和全套回归；数据库结构变化必须新增迁移。
设计令牌与行为契约为根目录`DESIGN.md`、`UX-CONTRACT.md`，所有后台页面共用列表、编辑表单和反馈组件。
项目运行日志、进程记录、临时截图和初始凭据位于`.cache/`，不纳入Git。依赖锁文件、源代码、迁移和说明纳入Git。

## 使用边界

这是本机开发版本，默认只监听回环地址。正式对外部署还需配置HTTPS、独立低权限数据库账号、备份恢复、网络访问控制和生产运行配置。
生产环境不能使用测试库或测试账号；不要在营业环境运行测试清理流程。
