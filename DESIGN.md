---
version: alpha
name: 我川 W-ERP
description: 女装连锁总部基础档案后台，以清晰规格矩阵和可靠表单为核心。
colors:
  primary: "#267e78"
  background: "#f7f8fa"
  surface: "#ffffff"
  sidebar: "#18283b"
  text: "#18283b"
  muted: "#64748b"
  border: "#dce3eb"
  danger: "#b83e42"
typography:
  sans:
    fontFamily: '"Microsoft YaHei", "PingFang SC", system-ui, sans-serif'
  mono:
    fontFamily: '"Cascadia Mono", Consolas, monospace'
rounded:
  DEFAULT: "10px"
  sm: "6px"
  lg: "12px"
spacing:
  section-gap: "24px"
  page-max: "1440px"
components:
  button: {}
  card: {}
  dialog: {}
  table: {}
  input: {}
---

# 我川 Design System

## Overview
### Creative North Star
把门店款式台账和颜色尺码订货矩阵带入清晰的总部工作台，视觉参考见 docs/design/foundation-concept.png。
### Product context and register
面向中文女装零售总部人员，主要在Windows桌面日常维护基础档案。产品界面，非营销页面；市场证据为本项目PRD，不推断其他地区要求。
简体中文、人民币价格、Asia/Shanghai时间；尺寸规格编码使用等宽数字。唯一视觉重点为可横向阅读的颜色尺码矩阵，其余表格和表单保持克制。
不使用装饰大图、假指标、无业务依据的图表。令牌以本文件为规范，映射到frontend/src/styles.css中CSS变量，再适配Element Plus的--el-*变量；核对脚本检查颜色漂移。

## Colors
primary用于主要操作与选中导航；sidebar用于导航，background/surface分隔页面与面板；text/muted提供文字层次，border提供边界，danger用于失败与停用确认。状态必须同时有文字，不仅靠颜色。

## Typography
中文正文和控件14px、行高1.6；页面标题28px/700，面板标题17px/600，编码使用mono字体，数字采用tabular-nums。所有字体均本地回退，不外联加载。

## Layout
桌面224px侧栏、64px页头、32px内容边距，最大内容宽1440px。760px以下侧栏变为可展开导航，内容边距16px，表单单列，矩阵在自身面板中横向滚动；页面自然纵向滚动，不能裁剪长表单。

## Elevation & Depth
面板用细边框，轻阴影仅用于登录和弹窗；信息表格不用装饰阴影。

## Shapes
面板10px，控件6px，状态标识小圆角；按钮/表单由Element Plus提供统一基础行为。

## Components
ArchiveTable拥有列表、查询、分页和错误状态；ArchiveEditor拥有复用档案表单；SkuMatrix拥有颜色尺码编辑。Select为Element Plus authored；表单使用ElForm/ElInput，Toast为ElMessage，确认与未保存导航为ElMessageBox。
忙状态保持按钮尺寸，禁用重复提交；键盘focus可见。提交失败保留字段，内联错误提供重试方向。

## Motion
仅使用短过渡呈现交互，不作装饰动画；prefers-reduced-motion下关闭过渡。

## Responsive
360px起保持主要操作可见；矩阵最小列宽200px，横向滚动限定在矩阵容器，移动端展开菜单不改变内容状态。

## Accessibility
WCAG 2.2 AA基础目标，输入关联中文label，图标按钮提供aria-label，错误role=alert，结果role=status；不禁用密码粘贴，不以hover作为唯一信息入口。

## Verification
真实浏览器检查桌面与窄屏、表单错误与输入保留、Select展开、键盘导航、颜色尺码矩阵。颜色变量由scripts/check-design.mjs对照，静态审计由premium-ui.json配置。
