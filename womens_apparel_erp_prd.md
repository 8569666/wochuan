# 女装零售连锁进销存系统 (ERP / SCM / POS)
## 产品需求规格说明书 (PRD - Product Requirements Document)

---

### 文档基本信息
- **项目名称**：新零售多门店女装连锁数字化进销存系统（W-ERP & POS）
- **技术栈架构**：Vue 3 (Vite + TypeScript + Pinia + Element Plus) + FastAPI (Python 3.14 + Async SQLAlchemy + Pydantic v2 + MySQL 8.0 + Redis)
- **文档版本**：v1.0.1
- **编制日期**：2026-10-14
- **技术选型更新**：2026-10-15，用户指定 Python 3.14 与本地 MySQL；首批以 MySQL 8.0.46 为兼容目标，详细范围见 `docs/superpowers/specs/2026-10-15-foundation-design.md`。
- **面向读者**：产品经理、前端开发工程师、后端开发工程师、测试工程师、零售业务运营团队、系统运维人员

---

## 1. 项目概述与业务背景

### 1.1 业务背景与行业特性
女装零售行业具备极高的快时尚属性与复杂的供应链网络，相较于标品零售，存在以下显著业务痛点：
1. **多维SKU与矩阵特性**：女装具有极强的“颜色、尺码、版型、面料、波段、年份、季节”属性组合。一个SPU款号对应多达10~30个SKU。人工录入与维护效率低下，极易发生“断码、断色”却无人知晓的情况。
2. **生命周期极短与快周转诉求**：常规单品销售周期仅2~6周，需经历“企划上新 -> 试销爆款 -> 批量补单 -> 平销维持 -> 季末清仓”完整闭环。库存贬值迅速，对**库销比**与**售罄率**监控极度敏感。
3. **连锁多形态门店协同**：包含直营店、加盟店、商场联营专柜三种模式。总部统一采购与集中仓储，需要支撑“总仓首铺配货”、“门店智能补货”、“同城跨店同级平衡调拨”及“季末退仓返厂”。
4. **线下收银与弱网可用性**：门店高峰期顾客试穿量大、成单节奏快，收银系统必须支持连续扫码、改价折让、复合支付、挂单取单；商场负一层或网络抖动环境下必须支持**离线收银**与自动重放对账。
5. **导购与私域会员联动**：依赖导购人际维护与身材档案推荐（身高、体重、三围、风格偏好），需要精准核算导购业绩提成、连带率（UPT）与客单价。

### 1.2 系统建设目标
构建一套“总部-分仓-门店-导购-会员”五位一体的现代化敏捷进销存系统，实现：
- **商品流数字化**：SPU/SKU矩阵化高效管理，条码与吊牌一键批量排版打印。
- **库存流精准化**：总仓与多店仓实时账实同步，在途库存透明追踪，智能跨店调拨平衡库存。
- **资金与成本核算精准化**：采用**移动加权平均法**核算存货成本，实现单店、单品、单款毛利穿透式核算。
- **技术架构现代化**：依托 Vue 3 极致的前端交互体验与 FastAPI 高并发异步处理能力，支撑百万级SKU检索与毫秒级库存并发扣减。

---

## 2. 系统用户角色与权限矩阵 (RBAC)

系统采用标准 RBAC (Role-Based Access Control) 模型，并结合“组织机构/门店”维度实现**行级数据隔离**。

| 角色编号 | 角色名称 | 典型用户 | 核心职责与操作边界 | 数据查看范围 |
| :--- | :--- | :--- | :--- | :--- |
| **R01** | 总部管理层 | 老板、运营总监 | 查看集团全盘经营看板、核心财务指标、审批重大单据（特批折让、加盟额度） | 集团全部数据 |
| **R02** | 商品企划/买手 | 商品部专员 | 建立SPU/SKU档案、颜色尺码规格、企划波段、指导吊牌价与渠道供货价 | 集团商品与供应链数据 |
| **R03** | 采购专员 | 供应链采购部 | 供应商开发与管理、采购订单创建与跟催、采购入库通知、采购退货单 | 采购与供应商往来 |
| **R04** | 总仓仓管员 | 中央物流仓储 | 总仓采购质检入库、配货发货复核、总仓调拨出库、总仓盘点、残损质检 | 中央仓库/区域分仓数据 |
| **R05** | 连锁运营/配货专员 | 运营部配货员 | 首批铺货指令下发、门店补货申请审批、同城跨店调拨协调、退仓指令发起 | 全部门店与库存在途数据 |
| **R06** | 门店店长 | 直营/加盟店长 | 门店日常经营管理、店仓收货验货、跨店调拨发起/接收、门店盘点、店员排班 | 本门店及关联同城可调拨仓 |
| **R07** | 门店导购/收银员 | 门店收银员 | POS端快速收银、挂单、退换货、会员身材建档、交接班日结 | 本机POS及所属个人业绩 |
| **R08** | 财务主管 | 财务部 | 供应商对账开票、加盟商往来账户充值、存货成本核算、销售毛利报表、日结审核 | 集团全部财务与业务单据 |
| **R09** | 系统管理员 | IT技术团队 | 组织架构配置、角色权限配置、系统参数、日志审计、条码规则设定 | 系统基础平台数据 |

---

## 3. 系统信息架构与业务实体模型 (ER)

### 3.1 组织架构与多仓模型
系统组织架构划分为三级逻辑层级：
`集团总部 (Headquarters) -> 运营大区/分公司 (Region) -> 经营网点 (Store/Outlet)`
仓库体系支持多类型虚拟与实体仓：
- **中央总仓 (Central Warehouse)**：负责工厂集采接收入库、分拣、向门店首发铺货与大宗补货。
- **门店实体仓 (Store Warehouse)**：每家门店绑定的默认进销存实体仓（包含前厅陈列与后仓）。
- **在途虚拟仓 (In-transit Virtual Warehouse)**：调拨、配货、采购退货发货后至目标仓入库验收前的中间过渡仓，确保库存总量守恒。
- **残次/质检仓 (Defect/Inspection Warehouse)**：处理顾客退货次品、运输破损品的专有仓，不计入可用销售库存。

### 3.2 女装商品核心数据模型 (SPU-SKU 矩阵)

女装商品以 **SPU (Standard Product Unit, 标准款号)** 与 **SKU (Stock Keeping Unit, 单品规格)** 双层架构建模。

```
【SPU 款号对象】
  ├── 款号 (Style Code): 2026S-DR088 (年份+季节+大类+序号)
  ├── 款名: 法式法兰绒收腰泡泡袖复古连衣裙
  ├── 类目层级: 女装 > 裙装 > 连衣裙
  ├── 年份/季节/波段: 2026年 / 春夏 / 第2波段(3月上新)
  ├── 版型 / 风格 / 长度: A字修身 / 法式复古 / 中长裙
  ├── 面料成分: 100% 桑蚕丝 / 内衬 100% 聚酯纤维
  ├── 安全技术类别: GB 18401-2010 B类 (直接接触皮肤)
  ├── 吊牌价 (Tag Price): ¥599.00
  ├── 采购基准价 / 零售限价底线: ¥140.00 / ¥399.00
  └── 关联规格矩阵:
        ├── 颜色组: [01-米白, 02-樱花粉, 03-曜石黑]
        └── 尺码组: [S(155/80A), M(160/84A), L(165/88A), XL(170/92A)]
              │
              ▼ (笛卡尔积自动生成 3 × 4 = 12 个 SKU)
【SKU 单品规格对象】
  ├── 唯一标识: SKU_ID
  ├── 组合编码: 2026S-DR088-01-S
  ├── 国际条形码 (EAN-13 / Code-128): 6971234560012
  ├── 颜色/尺码/色号: 米白 / S
  ├── 移动加权平均成本 (Moving Weighted Cost): ¥138.50
  ├── 建议调拨价 (Transfer Price): ¥220.00
  └── 加盟结算底价 (Franchise Cost): ¥240.00
```

---

## 4. 核心功能模块详细需求规范

### 4.1 商品中心 (Product Center)
#### 4.1.1 需求背景与痛点
女装单款多色多码，传统软件逐个建立SKU效率极低，易漏码错码。需支持矩阵式快速生成与批量调价。
#### 4.1.2 详细功能点
1. **SPU/SKU 矩阵录入**：
   - 维护通用的“颜色库”（支持标准色卡、缩写、十六进制色板）与“尺码组”（如女装上衣组：S/M/L/XL/均码；女裤裤腰组：26/27/28/29/30）。
   - 新建SPU时，勾选颜色组与尺码组，系统自动笛卡尔积生成SKU表格，支持在二维矩阵中批量填报条形码、成本、吊牌价。
2. **条码与吊牌规则引擎**：
   - 支持自定义编码生成规则：`前缀 + 年份(2位) + 季节(1位) + 品类(2位) + 款号流水(3位) + 色号(2位) + 尺码代码(2位)`。
   - 吊牌批量打印：集成 Web 端静默打印（支持 TSC/斑马等主流热敏吊牌机），支持自定义包含“合格证、执行标准、安全类别、面料成分、零售价、二维码/条形码”的标准服装吊牌模板。
3. **价格体系管理**：
   - 多级价格控制：吊牌价（挂牌价）、直营零售指导价、会员限价（最低折让红线）、加盟批发供货价、同业代销协议价。
   - 变价单（Price Adjustment Notice）：支持按款号批量设置生效时间、执行门店范围，到期自动切换并下发POS终端。
4. **商品生命周期状态机**：
   - 状态包含：`设计企划款 -> 样衣确认 -> 订货上架 -> 首发热销 -> 平销补单 -> 促销清仓 -> 季节性下架 -> 永久淘汰`。

### 4.2 采购与供应链管理 (Purchasing & SCM)
#### 4.2.1 业务流程说明
企划选款或补货建议 -> 生成采购订单 (PO) -> 总部审核 -> 供应商确认 -> 工厂发货与物流追踪 -> 总仓收货质检 -> 采购入库入账 -> 财务应付账款。
#### 4.2.2 详细功能点
1. **供应商协同档案**：
   - 维护供应商基本信息、结算周期（现结、月结30天、滚动账期）、供货品类、历史交期履约率与次品率评分。
2. **采购订单 (Purchase Order)**：
   - 表头：供应商、预计到货日期、收货总仓、结算币种、定金比例。
   - 明细：支持“SPU矩阵录入视图”，横轴尺码、纵轴颜色，直接录入配额件数。
   - 状态流转：`草稿 -> 待审批 -> 已审核(执行中) -> 部分入库 -> 全部入库 -> 已关闭/作废`。
3. **采购收货与质检 (QC & Inspection)**：
   - 总仓到货时支持“箱条码扫描”，支持盲验与明细核验双模式。
   - 质检判定：合格入库、让步接收（扣减折价）、不合格拒收并自动生成《采购退货单》。
4. **采购对账单与付款申请**：
   - 自动归集入库流水，生成采购发票核销单，推送到财务应付模块。

### 4.3 仓储管理与多仓协同 (WMS & Multi-Warehouse)
#### 4.3.1 库存状态四维模型
系统在任意“仓库 + SKU”维度下严格维护四类库存度量：
1. **账面总库存 (Physical Stock)**：仓内实际物理件数。
2. **锁定库存 (Locked Stock)**：已成单待打包/待出库、挂单保留或盘点锁定的件数。
3. **可用库存 (Available Stock)**：`可用 = 账面总库存 - 锁定库存`，直接供POS收银与调拨占用。
4. **在途库存 (In-transit Stock)**：发出但目标仓未入库验收的单据件数。
#### 4.3.2 详细功能点
1. **入库单据体系**：采购入库、调拨入库、销售退货入库、盘盈入库、其他入库。
2. **出库单据体系**：首铺出库、配货出库、跨店调出、销售出库、返厂出库、盘亏出库。
3. **库存快照与流水台账**：
   - 每一笔库存增减必须强制记录流水号、单据类型、变动前库存、变动数量、变动后库存、操作人、时间戳。
   - 严禁任何直接修改库存数字的非法接口，所有变动必须源自合法已审核单据。
4. **盘点管理 (Stocktaking)**：
   - **动态动碰盘点**：针对近7天有出入库流水的SKU进行抽盘，不影响门店正常营业。
   - **全面停业盲盘**：盘点人员手持PDA或扫码枪直接扫码，系统不显示账面理论库存，盘点录入完毕后由系统比对生成《盘点差异分析表》，经店长与总部审批后生成盘盈/盘亏调整单。

### 4.4 配货、调拨与智能补货引擎 (Distribution & Replenishment)
#### 4.4.1 女装特色配补调逻辑
1. **新季首铺配货策略 (Initial Allocation)**：
   - 按门店等级（A类旗舰店、B类标准店、C类小型社区店）及陈列货架容量，设定首铺配比矩阵。
   - 一键将采购到货拆分下发为数十家门店的《首铺配货单》。
2. **智能补货算法 (Automatic Replenishment)**：
   - 算法模型：
     $$R_{suggest} = (V_{avg7} 	imes D_{target}) + S_{safe} - (I_{available} + I_{transit})$$
     - $V_{avg7}$：近7天该门店该SKU的日均销售件数（可配置加权系数）。
     - $D_{target}$：目标备货周转天数（默认14天）。
     - $S_{safe}$：安全库存阈值（断码保护件数，如黄金码M/L设为2件）。
     - $I_{available}, I_{transit}$：本店可用库存与在途库存。
   - 当计算值 $>0$ 时自动生成补货建议单，商品运营一键合并转化为总仓发货单。
3. **跨店横向同级调拨 (Store-to-Store Balancing Transfer)**：
   - 痛点解决：A店M码售罄断码缺货，而同城B店M码近14天零动销积压。
   - 调拨引擎：系统每日夜间跑批，识别同城/同商圈内的“高动销缺码店”与“滞销积压店”，自动推荐同级调拨方案。
   - 业务闭环：调出店申请/总部指派 -> 调出店扫码装箱发货（扣可用、入在途） -> 调入店扫码收货验视（出在途、加实体可用）。若有差异，支持“差异确认单”进行异常追溯。

### 4.5 门店收银系统 (Store POS Terminal)
#### 4.5.1 前端设计要求
POS前端基于 Vue 3 + Pinia 构建独立极简收银界面，支持全键盘快捷键、触屏双模操作，支持扫码枪无需聚焦直接捕获输入。
#### 4.5.2 详细功能点
1. **快速收银录单**：
   - 扫码枪连续扫码录入SKU，蜂鸣声提示成功/失败；支持手动输入款号选择颜色尺码。
   - 挂单与解挂 (Hold & Resume)：顾客临时加购试穿时，一键挂单（快捷键 `F4`），保存至本地缓存，优先结算后续顾客，之后一键提取恢复。
2. **复合促销计算引擎**：
   - 实时根据购物车商品计算女装多重促销规则：
     - 单品折扣（如吊牌价8折）。
     - 满件折（如“任意2件8.8折，3件7.5折”）。
     - 满减优惠（如“满400减50，满800减120”）。
     - 搭配满减/第二件半价。
     - 会员权益叠加（会员折上折/积分抵扣）。
   - 权限拦截：导购临时抹零或改价时，若超出导购限额（如低于7折），强制弹出店长授权密码确认窗口。
3. **复合结算与支付聚合**：
   - 支持多渠道组合支付：微信/支付宝刷卡付（扫码枪扫顾客付款码）、现金收银、会员卡储值余额扣减、实体优惠券核销。
4. **跨店退换货处理**：
   - 支持凭小票流水号、会员手机号快速调取原单；
   - 支持同款不同色/码直接等额换货；支持异款退补差价；退回良品入本店仓，残损品直接转入待质检残次仓。
5. **离线收银与网络自愈**：
   - 当网络断开时，POS前端通过 IndexedDB 保存销售单，使用本地缓存的最新离线商品数据与会员信息完成收银并打印脱机离线小票。
   - 网络恢复后，后台 Service Worker / 定时器自动将离线单批量重放到 FastAPI 接口，带唯一离线UUID幂等去重校验。
6. **班次日结与钱箱交接**：
   - 开班：录入备用金金额。
   - 交班/日结：清点实际收缴现金，系统自动核对微信/支付宝/会员流水，生成《收银员日结对账单》并打印，钱箱弹出指令控制。

### 4.6 会员管理与导购协同 (CRM & Commission)
#### 4.6.1 会员全生命周期管理
1. **会员档案与身材标签**：
   - 基础信息：手机号、生日、微信OpenID/UnionID。
   - 女装身材专有画像：身高、体重、三围、肩宽、肤色偏好、穿衣风格标签（通勤/法式/休闲/极简）。
2. **会员等级与积分体系**：
   - 消费积分规则（1元=1积分）、积分抵现规则（100积分抵扣5元，单笔最高抵扣订单金额20%）。
   - 会员等级门槛（普卡、银卡、金卡、黑金VIP），享受专属折扣与生日月双倍积分/专属无门槛券。
#### 4.6.2 导购归属与提成核算 (Clienteling & Commission)
1. 专属导购绑定：会员首次进店或扫导购个人码注册即绑定归属导购。
2. 提成结算策略：
   - 个人业绩阶梯提成（如月销<3万提成3%，3~6万提成5%，>6万提成7%）。
   - 高连带率奖励：当单笔订单件数 $\ge 3$ 件时，额外给予连带率专项奖金。
   - 跨店业绩归属规则与退换货提成逆向扣减。

### 4.7 财务对账与存货成本核算 (Finance & Cost Accounting)
#### 4.7.1 存货成本核算：移动加权平均法 (Moving Weighted Average)
每次采购入库后，自动根据最新入库金额重新计算该 SKU 的单位成本：
$$C_{new} = rac{(Q_{before} 	imes C_{old}) + (Q_{in} 	imes C_{in})}{Q_{before} + Q_{in}}$$
所有销售出库、调拨出库均严格以此移动成本出账，确保毛利率真实可靠。
#### 4.7.2 往来对账模块
1. **加盟商账户管理**：加盟商预付款钱包、授信信用额度管控；发货时严格校验可用余额，欠款超额自动拦截发货审核。
2. **商场联营专柜扣点结算**：按合同约定账期（如月结扣点22%），系统自动核算商场应返还实收金额。
3. **单品/单店毛利穿透**：报表实时穿透计算：`销售收入 - 销售成本 - 促销折让 - 导购提成 = 销售毛利`。

### 4.8 经营数据看板与BI报表中心 (Analytics & BI)
#### 4.8.1 服装零售核心指标体系
1. **售罄率 (Sell-through Rate)**：
   $$	ext{售罄率} = rac{	ext{某波段/某款累计销售件数}}{	ext{总采购入库件数}} 	imes 100\%$$
   - 监控指标：上新第14天售罄率需达 $30\%$，第30天需达 $60\%$。低于阈值自动触发“滞销预警”。
2. **库销比 (Stock-to-Sales Ratio)**：
   $$	ext{库销比} = rac{	ext{期末库存金额}}{	ext{当期销售金额}}$$
   - 理想女装零售库销比控制在 3.0 ~ 4.5 之间。
3. **动销率 (Active Sales Ratio)**：有销售记录的SKU数占店铺全部陈列SKU数的比例。
4. **连带率 (UPT - Units Per Transaction)**：$rac{	ext{总销售件数}}{	ext{总交易单数}}$，考核导购搭配销售能力（健康指标通常 $\ge 1.8$）。
5. **断码率热力图**：统计各门店核心畅销码（如S/M/L）缺货占比，直观定位补货盲区。

---

## 5. 系统技术架构与接口设计 (Vue 3 + FastAPI)

### 5.1 整体技术拓扑架构
```
                      ┌──────────────────────────────────────────┐
                      │             客户端表现层                  │
                      ├────────────────────┬─────────────────────┤
                      │  总部管理后台(Web) │ 门店收银终端 (POS)   │
                      │  Vue 3 + Vite      │ Vue 3 PWA / Electron│
                      │  Element Plus PC端 │ 触屏+扫码枪+小票驱动 │
                      └─────────▲──────────┴──────────▲──────────┘
                                │                     │
                         HTTPS/WSS REST API & EventStream
                                │                     │
                      ┌─────────▼─────────────────────▼──────────┐
                      │              网关接入与安全控制           │
                      │  Nginx 反向代理 + SSL/TLS + 限流防刷      │
                      └───────────────────▲──────────────────────┘
                                          │
                      ┌───────────────────▼──────────────────────┐
                      │            业务逻辑服务层 (FastAPI)       │
                      │  • ASGI 异步并发运行时 (Uvicorn Workers) │
                      │  • OAuth2 JWT 鉴权 & 门店行级隔离中间件  │
                      │  • Pydantic v2 强类型校验与序列化        │
                      │  • 进销存领域服务 (商品/库存/配调补/财务) │
                      └─────▲─────────────▲──────────────▲───────┘
                            │             │              │
         SQLAlchemy 2.0 Async        Redis Client     Celery/ARQ
                            │             │              │
    ┌───────────────────────▼┐   ┌────────▼─────────┐   ┌▼──────────────┐
    │     关系型数据库        │   │    缓存与锁服务  │   │ 异步后台任务  │
    │  MySQL 8.0 (InnoDB)        │   │  Redis 7.0+      │   │ • 报表批量导出│
    │  • 事务一致性 ACID     │   │  • 分布式库存锁  │   │ • 夜间补货跑批│
    │  • 行级排他锁 (FOR UPDATE)│  • 会员Token/会话│   │ • 消息推送    │
    │  • JSON 扩展规格      │   │  • 流水号生成器  │   └───────────────┘
    └────────────────────────┘   └──────────────────┘
```

### 5.2 前端工程架构 (Vue 3)
- **核心包选型**：`Vue 3.4+` + `Vite 5` + `TypeScript 5` + `Pinia` + `Vue Router 4` + `Element Plus` + `ECharts` + `vue-print-nb`。
- **项目模块组织**：
  ```
  src/
  ├── api/               # 封装 Axios 请求，遵循 RESTful 接口
  ├── assets/            # 静态资源与样式
  ├── components/        # 公共组件（SkuMatrixTable, BarcodePrinter, DateRangePicker）
  ├── directive/         # 自定义指令 (v-permission 按钮鉴权)
  ├── layout/            # 侧边栏、顶部导航、Tag多标签页
  ├── router/            # 动态权限路由表
  ├── stores/            # Pinia状态管理 (user, app, posCart, inventory)
  ├── utils/             # 扫码枪监听器、离线存储(IndexedDB)、小票ESC/POS协议工具
  └── views/
      ├── goods/         # 商品SPU录入、SKU规格矩阵、吊牌打印
      ├── purchase/      # 采购订单、质检收货单
      ├── warehouse/     # 出入库台账、多仓调拨、盲盘盘点
      ├── allocation/    # 智能补货引擎、同城跨店调拨看板
      ├── pos/           # 门店收银台、挂单结算、日结交接班
      ├── crm/           # 会员身材画像、积分券包、导购提成
      └── dashboard/     # 售罄率、库销比BI大屏
  ```
- **关键前端技术难点实现**：
  1. **SKU规格矩阵动态编辑器**：基于两组属性（颜色/尺码）动态渲染二维网格，支持矩阵批量填充价格、库存预警阈值。
  2. **POS扫码枪无焦点监听**：通过全局 `window.addEventListener('keydown')` 捕获扫描枪高速输入的字符流（间隔 $<30	ext{ms}$，以回车结束），避免收银员鼠标未聚焦输入框导致扫码丢失。

### 5.3 后端架构设计 (FastAPI)
- **分层规范**：
  ```
  app/
  ├── api/               # API 路由控制层 (v1/goods, v1/inventory, v1/pos...)
  ├── core/              # 核心配置 (config, security, database, exceptions)
  ├── middlewares/       # 中间件 (数据权限过滤、操作审计日志、请求耗时监控)
  ├── models/            # SQLAlchemy 异步 ORM 数据模型
  ├── schemas/           # Pydantic v2 请求验证与响应序列化模型
  ├── services/          # 领域业务服务 (库存原子扣减、移动加权成本计算)
  └── tasks/             # 异步后台任务 (Celery / ARQ)
  ```
- **关键后端技术难点实现**：
  1. **高并发库存扣减与防超卖 (Redis Lua 脚本)**：
     秒杀或多门店并发占用总仓库存时，采用 Redis Lua 脚本保证“校验库存并扣减”的原子性，操作成功后异步写入数据库事务，若后续流程失败则执行补偿反向释放。
  2. **行级数据隔离中间件**：
     在依赖注入中解析当前用户 JWT Token，提取其所属 `store_id` 与 `role`。非总部角色查询所有库存与销售单据时，自动化在 SQLAlchemy 查询中添加 `.filter(Model.store_id == current_user.store_id)`。
  3. **分布式单据单号生成器**：
     通过 Redis `INCR` 维护每日流水号：`PO-YYYYMMDD-{00001}`，确保单据全局唯一且连续。

---

## 6. 核心数据库物理表结构设计 (DDL)

```sql
-- MySQL 8.0示例；应用和数据库连接统一使用UTC。正式表结构以Alembic迁移为准。
SET time_zone = '+00:00';

-- 1. 商品 SPU 表
CREATE TABLE spu_products (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    spu_code VARCHAR(64) UNIQUE NOT NULL,      -- 款号, 如 2026S-DR088
    spu_name VARCHAR(255) NOT NULL,            -- 款名
    category_id INT NOT NULL,                  -- 品类ID
    brand_id INT DEFAULT 1,                    -- 品牌
    year INT NOT NULL,                         -- 年份: 2026
    season VARCHAR(16) NOT NULL,               -- 季节: 春夏/秋冬
    wave_band VARCHAR(32),                     -- 波段: 第1波段/第2波段
    fabric_composition TEXT,                   -- 面料成分: 100% 桑蚕丝
    safety_category VARCHAR(32) DEFAULT 'B类', -- 安全等级
    tag_price DECIMAL(10, 2) NOT NULL,         -- 吊牌价
    purchase_base_price DECIMAL(10, 2),        -- 采购基准价
    min_retail_price DECIMAL(10, 2),           -- 最低零售限价
    status VARCHAR(32) DEFAULT 'ACTIVE',       -- 状态: ACTIVE/DISCONTINUED
    created_at DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 2. 商品 SKU 表
CREATE TABLE sku_items (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    spu_id BIGINT,
    sku_code VARCHAR(64) UNIQUE NOT NULL,      -- SKU编码: 2026S-DR088-01-S
    barcode VARCHAR(64) UNIQUE NOT NULL,       -- 国际条形码
    color_code VARCHAR(32) NOT NULL,           -- 色号: 01
    color_name VARCHAR(64) NOT NULL,           -- 颜色名称: 米白
    size_code VARCHAR(32) NOT NULL,            -- 尺码代码: S
    size_name VARCHAR(64) NOT NULL,            -- 尺码名称: 155/80A (S)
    cost_price DECIMAL(10, 2) NOT NULL,        -- 当前移动加权成本价
    retail_price DECIMAL(10, 2) NOT NULL,      -- 门店零售价
    franchise_price DECIMAL(10, 2),            -- 加盟商批发价
    created_at DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6),
    CONSTRAINT fk_sku_items_spu_id FOREIGN KEY (spu_id) REFERENCES spu_products(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 3. 组织门店与仓库表
CREATE TABLE stores (
    id INT AUTO_INCREMENT PRIMARY KEY,
    store_code VARCHAR(32) UNIQUE NOT NULL,
    store_name VARCHAR(128) NOT NULL,
    store_type VARCHAR(32) NOT NULL,           -- DIRECT(直营), FRANCHISE(加盟), CONSIGNMENT(商场联营)
    region_id INT,
    address VARCHAR(255),
    contact_phone VARCHAR(32),
    credit_limit DECIMAL(12, 2) DEFAULT 0.00,  -- 加盟商授信额度
    balance DECIMAL(12, 2) DEFAULT 0.00,       -- 账户预付余额
    status VARCHAR(16) DEFAULT 'OPEN'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE warehouses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    wh_code VARCHAR(32) UNIQUE NOT NULL,
    wh_name VARCHAR(128) NOT NULL,
    wh_type VARCHAR(32) NOT NULL,              -- CENTRAL(总仓), STORE(店仓), TRANSIT(在途), DEFECT(残次)
    store_id INT,        -- 关联门店 (店仓专用)
    status VARCHAR(16) DEFAULT 'ACTIVE',
    CONSTRAINT fk_warehouses_store_id FOREIGN KEY (store_id) REFERENCES stores(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 4. 实时库存主表 (仓+SKU维度)
CREATE TABLE inventory_stocks (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    warehouse_id INT,
    sku_id BIGINT,
    physical_stock INT NOT NULL DEFAULT 0,     -- 物理在库总数
    locked_stock INT NOT NULL DEFAULT 0,       -- 锁定库存
    transit_stock INT NOT NULL DEFAULT 0,      -- 在途库存
    safe_stock INT DEFAULT 2,                  -- 安全警戒库存
    updated_at DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6),
    CONSTRAINT uk_wh_sku UNIQUE(warehouse_id, sku_id),
    CONSTRAINT chk_stock_non_negative CHECK (physical_stock >= 0),
    CONSTRAINT fk_inventory_stocks_warehouse_id FOREIGN KEY (warehouse_id) REFERENCES warehouses(id),
    CONSTRAINT fk_inventory_stocks_sku_id FOREIGN KEY (sku_id) REFERENCES sku_items(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 5. 库存变动流水台账表
CREATE TABLE inventory_transactions (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    trans_no VARCHAR(64) UNIQUE NOT NULL,
    warehouse_id INT,
    sku_id BIGINT,
    change_type VARCHAR(32) NOT NULL,          -- IN_PURCHASE, OUT_SALE, IN_TRANSFER, OUT_TRANSFER, PANDIAN
    change_qty INT NOT NULL,                   -- 变动数量 (+/-)
    before_qty INT NOT NULL,
    after_qty INT NOT NULL,
    unit_cost DECIMAL(10, 2),                  -- 出入库当时成本
    ref_bill_no VARCHAR(64) NOT NULL,          -- 关联业务单据号
    operator_id INT NOT NULL,
    created_at DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6),
    CONSTRAINT fk_inventory_transactions_warehouse_id FOREIGN KEY (warehouse_id) REFERENCES warehouses(id),
    CONSTRAINT fk_inventory_transactions_sku_id FOREIGN KEY (sku_id) REFERENCES sku_items(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 6. 门店销售订单表 (POS)
CREATE TABLE sales_orders (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    order_no VARCHAR(64) UNIQUE NOT NULL,      -- 销售单号: SO-20261014-0012
    store_id INT,
    cashier_id INT NOT NULL,                   -- 收银员ID
    guide_id INT,                              -- 提成导购员ID
    member_id BIGINT,                          -- 会员ID (可为空)
    total_amount DECIMAL(10, 2) NOT NULL,      -- 吊牌原价合计
    discount_amount DECIMAL(10, 2) DEFAULT 0,  -- 促销优惠合计
    pay_amount DECIMAL(10, 2) NOT NULL,        -- 实付金额
    pay_method VARCHAR(32) NOT NULL,           -- WECHAT, ALIPAY, CASH, MIXED
    pay_status VARCHAR(16) DEFAULT 'PAID',     -- PAID, REFUNDED, PART_REFUND
    is_offline_sync BOOLEAN DEFAULT FALSE,     -- 是否为离线重放单据
    created_at DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6),
    CONSTRAINT fk_sales_orders_store_id FOREIGN KEY (store_id) REFERENCES stores(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 7. 销售订单明细表
CREATE TABLE sales_order_items (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    order_id BIGINT,
    sku_id BIGINT,
    quantity INT NOT NULL DEFAULT 1,
    tag_price DECIMAL(10, 2) NOT NULL,
    sold_price DECIMAL(10, 2) NOT NULL,
    cost_price DECIMAL(10, 2) NOT NULL,        -- 销售结转成本
    commission_rate DECIMAL(5, 4) DEFAULT 0,   -- 导购提成比率
    CONSTRAINT fk_sales_order_items_order_id FOREIGN KEY (order_id) REFERENCES sales_orders(id) ON DELETE CASCADE,
    CONSTRAINT fk_sales_order_items_sku_id FOREIGN KEY (sku_id) REFERENCES sku_items(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
```

---

## 7. 核心 API 接口规范与数据契约

系统遵循 RESTful 规范，接口统一返回封装结构：
```json
{
  "code": 200,
  "message": "操作成功",
  "data": {},
  "timestamp": 1791970930
}
```

### 7.1 POS 收银扫码结算接口
- **Endpoint**: `POST /api/v1/pos/checkout`
- **Desc**: 门店POS扫码收银最终结算，支持原子扣库存、会员积分累积、销售单创建。
- **Pydantic Request Schema**:
```python
from pydantic import BaseModel, Field
from typing import List, Optional
from decimal import Decimal

class CartItemSchema(BaseModel):
    sku_id: int = Field(..., description="SKU唯一ID")
    quantity: int = Field(..., ge=1, description="购买数量")
    sold_price: Decimal = Field(..., description="实收单价")
    guide_id: Optional[int] = Field(None, description="导购员ID")

class PaymentDetailSchema(BaseModel):
    method: str = Field(..., description="WECHAT / ALIPAY / CASH / MEMBER_CARD")
    amount: Decimal = Field(..., gt=0, description="支付金额")
    auth_code: Optional[str] = Field(None, description="顾客付款码")

class POSCheckoutRequest(BaseModel):
    store_id: int = Field(..., description="门店ID")
    cashier_id: int = Field(..., description="收银员ID")
    member_id: Optional[int] = Field(None, description="会员ID")
    items: List[CartItemSchema] = Field(..., min_length=1)
    payments: List[PaymentDetailSchema] = Field(..., min_length=1)
    offline_uuid: Optional[str] = Field(None, description="离线单唯一标识(防重放)")
```

### 7.2 智能跨店调拨建议接口
- **Endpoint**: `GET /api/v1/allocation/store-balance-suggestions`
- **Query Params**: `region_id: int`, `spu_id: Optional[int]`, `threshold_days: int = 14`
- **Desc**: 计算同城门店间的断码缺货与滞销分布，输出最优化点对点调拨建议矩阵。

---

## 8. 非功能性需求 (NFR) 与部署方案

### 8.1 性能与高可用指标
1. **接口响应时延**：
   - 门店 POS 扫码检索与改单响应时间：$P99 \le 50	ext{ms}$。
   - 结算出库与打印指令生成：$P95 \le 200	ext{ms}$。
   - 总部大盘BI复杂聚合报表：$P95 \le 1.5	ext{s}$。
2. **高并发抗压能力**：
   - 支持至少 200 家门店同时在线营业收银，支持峰值 500 TPS 订单秒级扣减。
3. **数据一致性保证**：
   - 涉及库存出入库与金额结算的事务，强制由数据库 ACID 事务控制或分布式锁屏障保障，禁止脏读、幻读与并发超卖。

### 8.2 容灾备份与安全合规
1. **网络容灾方案**：
   - POS终端离线收银模式：本地使用 IndexedDB 缓存 1000 笔离线交易流水，重连后指数退避重试同步。
2. **数据冷热备份**：
   - MySQL 每日全量逻辑备份，保留近 90 天；持续归档 binlog 并定期演练按时间点恢复，目标恢复点 (RPO) $\le 5$ 分钟。
3. **敏感信息脱敏**：
   - 会员手机号、身份证号、员工薪资在前端与非高权API展示时强制执行脱敏：`138****1234`。

### 8.3 推荐生产部署方案 (Docker Compose)
- **前端部署**：Nginx 容器托管 Vue 3 静态编译资源（开启 gzip / brotli 压缩，反向代理 `/api/`）。
- **后端服务**：FastAPI 容器运行在 Gunicorn + UvicornWorker 模式下（推荐 Worker 数为 `CPU核心数 * 2 + 1`）。
- **数据库与缓存**：MySQL 8.0（InnoDB）挂载高性能 SSD 存储卷；本地开发可连接已有 MySQL 实例；Redis 7 开启 AOF + RDB 双模持久化。
- **异步任务处理**：Celery Worker 容器独立调度耗时较长的数据跑批与报表导出。

---

## 9. 迭代规划与上线路线图 (Roadmap)

| 阶段 | 周期 | 核心建设内容 | 里程碑交付物 |
| :--- | :--- | :--- | :--- |
| **Phase 1** | 第 1 ~ 4 周 | 基础档案与核心进销存跑通 | 商品SPU/SKU矩阵录入、多仓体系、采购管理、总仓基础出入库、条码打印 |
| **Phase 2** | 第 5 ~ 8 周 | 门店POS终端与连锁调拨协同 | 门店收银POS、离线缓存、首铺配货、跨店同级调拨、门店盲盘 |
| **Phase 3** | 第 9 ~ 11 周 | 会员CRM、导购提成与财务核算 | 会员身材档案、促销引擎、导购阶梯提成、移动加权成本核算、加盟账款 |
| **Phase 4** | 第 12 ~ 14 周 | 智能配调补引擎与经营BI看板 | 智能补货模型、售罄率/库销比大屏、断码热力图、系统压测与全网联调上线 |
