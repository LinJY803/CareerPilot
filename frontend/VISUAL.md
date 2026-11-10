# CareerPilot 界面实现说明

这次只改了前端外观和少量布局结构。路由、接口、表单字段和业务逻辑保持原样。样式集中在 `src/styles/main.css`，页面只在结构需要时换了 class。

## 方向

界面用白底、近黑文字和细线分隔。全站同一套无衬线字体。朱红只出现在当前导航、文字链接、分数和雷达图上，不铺背景，也不做渐变、光晕或大阴影。

主按钮是近黑色。输入框聚焦时是一条黑边。

## 颜色和字体

字体从 Google Fonts 引入 **IBM Plex Sans SC**（字重 400、500、600），写在 `index.html`。加载失败时回退到 PingFang SC、Noto Sans SC、微软雅黑。

标题和正文用同一套字体。页面标题 22px、字重 600。登录和注册的主标题是 26px。说明文字 13px 到 14px。圆角 8px。内容区最大宽度 1080px，居中。

| 用途 | 变量 | 色值 |
| --- | --- | --- |
| 页面底 | `--bg` | `#f6f6f4` |
| 卡片 | `--card` | `#ffffff` |
| 正文 | `--ink` | `#161616` |
| 次要文字 | `--muted` | `#6f6f6c` |
| 分割线 | `--line` | `#e7e7e4` |
| 强调色 | `--signal` | `#d84a32` |

Element Plus 的主色 `--el-color-primary` 设为 `#161616`，和主按钮一致。

## 布局

登录后的壳层在 `src/layouts/AppLayout.vue`。

- 顶部是一条吸顶白栏：左侧字标 CareerPilot，中间是文字导航（工作台、简历、岗位、岗位匹配），右侧是用户名和「退出」。
- 当前项用朱红字和 2px 下划线。岗位详情、创建岗位算在「岗位」下面；匹配页和匹配报告只点亮「岗位匹配」。
- 窄于 760px 时，导航折到第二行，功能都还在。用户名过长会省略。
- 主内容放在 `.page` 里，左右留白。

## 页面

登录和注册（`LoginView.vue`、`RegisterView.vue`）是整页居中的一列：字标、标题、一句说明、表单。主按钮全宽。原有说明文字还在，没有改文案。

工作台（`DashboardView.vue`）的四个数字放在同一条白底指标栏里，用竖线分开，数字等宽。下面仍是「最近的简历」「最近的匹配」和「个人资料」三个白底区块。

列表页沿用原来的表格，表头改成 12px 灰色字，行间一条细线，悬停是一层浅灰。创建岗位、上传简历、岗位匹配这几个表单加了 `.narrow`，最大宽度 680px。

简历详情和匹配报告里，综合分、诊断分用 `.score`：44px、等宽、朱红。说明文字仍跟在分数下面。雷达图在 `ScoreRadar.vue`：墨色线条，淡朱红填充（`rgba(216, 74, 50, 0.12)`），刻度字用同一套字体。

空状态只留一句说明。Element Plus 自带的空状态插画被隐藏。

## 组件皮肤

仍使用 Element Plus，在 `main.css` 里覆盖默认外观：

- 主按钮近黑，悬停 `#2c2c2c`，禁用时降低透明度。
- 默认按钮白底、细线边。
- 文字按钮和链接用朱红；删除仍用危险色。
- 输入框、下拉框圆角 8px，聚焦为 1px 黑边。
- 标签改成线框，不填色。
- 单选选中为黑色。

成功、失败、警告这几类消息颜色没有改，用来区分操作结果。

## 窄屏

断点是 760px。

- 顶栏换行。
- 指标栏变成两列。
- 双栏和对照区改成单列。
- 页头标题和按钮上下排列。
- 表格最小宽度 640px，卡片内部可以横向滑动，页面本身不跟着撑开。

## 改动文件

- `index.html`：引入字体
- `src/styles/main.css`：颜色、字体、布局和组件覆盖
- `src/layouts/AppLayout.vue`：顶栏
- `src/views/LoginView.vue`、`src/views/RegisterView.vue`：单列表单
- `src/views/DashboardView.vue`：指标栏
- `src/views/ResumeDetailView.vue`、`src/views/MatchReportView.vue`：分数样式
- `src/views/JobCreateView.vue`、`src/views/ResumeUploadView.vue`、`src/views/JobMatchView.vue`：表单宽度
- `src/views/JobDetailView.vue`：原文区域去掉内联样式，改由全局 `pre` 样式控制
- `src/components/ScoreRadar.vue`：图表配色

## 没有改的部分

接口、鉴权、路由、文案逻辑、数据字段都没有动。列表页和优化页的结构也基本保持原样，只吃到全局样式。

简历详情和匹配报告上的大号分数、雷达图已经按上面的规则写好。当前环境没有模型密钥时，解析和匹配不会成功，所以这两块还没有在真实成功数据上看过。
