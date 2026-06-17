# X11 科技研究系统框架文档

> 入口分析文件：`Assets/X11/Scripts/GameLogic/Module/Tech/View/TechnologyCenterMainHUD.cs`
> 模块根目录：`Assets/X11/Scripts/GameLogic/Module/Tech/`

科技研究（科研）系统让玩家在「科技中心 / 科学馆」内沿多棵科技树逐级研究科技，获得 Buff 与战力加成。系统支持多研究队列（含付费解锁的第二队列）、立即完成、加速、推荐科技、前置条件 / 资源消耗校验等。

---

## 一、整体分层架构

系统严格遵循项目的分层约定：

```
View 层（HUD / Popup / MonoBehaviour 行为组件）
    ↓  读 TechMgr.I.Data，调 Research / Archive
逻辑层 TechMgr（单例） → TechData（运行时数据 + 业务）
    ↓  service 调用
网络层 TechService（收发 protobuf）
    ↓
配置层 Cfg.CResearchCategory / CScienceLayout / CResearch
```

数据流向：

- **下行（服务器 → 客户端）**：`ResearchNtf` → `TechService.OnResearchUpdate` → `TechData.OnResearchUpdate` → 更新缓存并 `FireEvent` → 各 View 组件刷新。
- **上行（客户端 → 服务器）**：View 点击 → `TechMgr.I.Data.Research/Archive` → `TechService.SendAsync<...Req>` → 等待 Ack。

---

## 二、核心 ID 体系（关键概念）

代码中大量出现「1132 / 1181 / 1119 / 1118」等数字，它们是不同配置表的代号，务必区分：

| ID 代号 | 配置表 | 含义 | 说明 |
|---|---|---|---|
| **1132** | `CResearchCategory` | 科技树 / 类别 | 一棵树（如经济、军事），界面入口 `TechTreeEntry` 对应一棵 |
| **1181** | `CScienceLayout` | 科技组（节点） | 树上的一个圆形节点，含布局坐标、图标、前置 `Pregroup` |
| **1119** | `CResearch` | 科技（具体等级条目） | 一个科技组的某一等级，含消耗、Buff、`LvlMax`、`Category` |
| **1118** | （建筑短 ID） | 建筑条件用 | 条件项里建筑的短形态 ID |

层级关系：**一棵树（1132）→ 多个科技组（1181）→ 每组多个等级条目（1119）**。

- `CResearch.Category` 指向所属树（1132）
- `CResearch.ResearchId` 指向所属科技组（1181）
- `CScienceLayout.Pregroup` 是该节点的前置科技组（1181 列表），用于解锁判定与连线
- `CScienceLayout.Layout[0]/[1]` 是行/列坐标，用于树状布局绘制

---

## 三、逻辑层

### 3.1 TechMgr（`TechMgr.cs`）

极简单例，仅持有 `TechData`：

```csharp
public partial class TechMgr : TFW.Utility.Singleton<TechMgr>
{
    public TechData Data { get; private set; }
    public void Init()   => Data = new();
    public void DeInit() => Data = null;
}
```

所有 View 通过 `TechMgr.I.Data.Xxx` 访问数据与发起操作。

### 3.2 TechData（`Model/TechData.cs`）—— 系统核心

运行时数据中心，持有三类缓存与一套查询/操作 API。

**内部状态：**

| 字段 | 类型 | 含义 |
|---|---|---|
| `techGroups` | `Dictionary<int, TechGroup>` | 各科技组（1181）当前等级 |
| `researchQueue` | `Dictionary<long, ResearchQueue>` | 进行中的研究队列（key 为队列 ID） |
| `_techCostsCache` | `Dictionary<(techId,level), ResearchNeedAck>` | 研发消耗缓存，按 (科技ID, 等级) 缓存，避免重复请求 |
| `Recommends` | `int[]` | 推荐科技数组，下标为 `RecommendType`（经济/军事） |

**数据更新入口 `OnResearchUpdate(ResearchNtf)`：**

1. 遍历 `ntf.tech` 更新 `techGroups`，并 `InvalidateTechCostsCache` 清理对应消耗缓存；
2. 填充经济 / 军事推荐科技；
3. 遍历 `ntf.studyTech` 更新研究队列，并通过 `CheckEvents` 比对新旧队列触发事件；
4. 末尾对每个变更科技 `FireEvent(TEventType1.TechUpdate)`。

**队列状态机（与城市队列 `LCityQueue` 联动）：**

- `OnCityQueueUpdate`：监听 `TEventType.CityQueueUpdate`，仅处理 `Research` 类型。
  - `startTime==0 && userEndTS==0`：研究收取结束 → 从 `researchQueue` 移除（因为后续 `ResearchNtf` 会传空列表无法对照删除，故此处提前处理）；
  - `startTime>0`：触发 `ResearchSpeedUp`。
- `GetPriorityQueue()`：优先级 **已完成 > 研究中 > 空**，供顶部气泡/标签展示当前最该关注的队列。

**主要查询 API：**

| 方法 | 入参 | 作用 |
|---|---|---|
| `IsUnlocked(id)` | 1181 | 前置组是否全部 > 0 级（已解锁） |
| `GetCrntLevel(id)` / `GetMaxLevel(id)` | 1181 | 当前等级 / 最大等级 |
| `GetResearchQueue(id)` | 1181 | 该科技对应的进行中城市队列 |
| `GetResearchQueueByIndex(index)` | 队列序号 | 按队列编号取城市队列 |
| `GetRecommandType(id)` / `GetRecommend(treeId)` / `GetRecommendTree()` | — | 推荐科技相关查询 |
| `GetTreeProgress(treeId)` | 1132 | 树进度（已研究等级数 / 总等级数） |
| `HasInResearch(treeId)` | 1132 | 该树是否有科技在研究中 |
| `GetTechCosts(techId)` | 1181 | 异步获取研发消耗（带缓存） |

**操作 API（异步）：**

- `Research(techId, immed, useItems, useRssItems, useDiamond)`：发起研究（`immed=true` 为立即完成）；
- `Archive(techId)`：收取已完成研究。

### 3.3 TechService（`Model/TechService.cs`）—— 网络层

封装 protobuf 收发，仅做请求构造与错误码校验：

- 注册 `ResearchNtf` 推送 → 转交 `TechData.OnResearchUpdate`；构造时若 `LoginNtfCacheMgr.I.CachedResearchNtf` 有缓存则立即消费（登录即时同步）。
- 上行请求：`StartResearchReq` / `DrawTechReq`（收取）/ `CancelResearchReq` / `ResearchNeedReq`（查消耗）。
- 统一判定 `ack == null || errCode != Success` 返回 null，调用方据此判空。

### 3.4 数据结构（`Model/DataStructs.cs`）

- `RecommendType` 枚举：`None(-1) / Economic(0) / Military(1) / All`。
- `TechTree` / `TechGroup` / `Tech` / `ResearchQueue`：对配置表与 protobuf 消息的轻量包装，提供 `GetCfg`、`From(msg)` 静态构造。其中 `ResearchQueue.CityQueue` 通过 `LCityQueue.I.GetQueueByQueueID(id)` 关联城市队列。

---

## 四、View 层（界面与组件）

View 层分两部分：**HUD/Popup（窗口，继承 `UIBaseMain`）** 与 **Behaviours（挂在 prefab 上的 `MonoBehaviour` 渲染组件）**。

### 4.1 窗口（HUD / Popup）

| 类 | 资源路径 | 职责 |
|---|---|---|
| `TechnologyCenterMainHUD` | `TechnologyCenter/TechnologyCenterMainHUD` | **总入口**：列出所有科技树入口 + 科研队列2礼包促销区 |
| `TechnologyCenterTreeHUD` | `TechnologyCenter/TechnologyCenterTreeHUD` | 单棵树详情，调 `TechTree.ShowTree(treeId)` 绘制树状图 |
| `TechInfoPopup` | `TechnologyCenter/TechInfoPopup` | 单个科技详情弹窗（条件、消耗、研究按钮），支持 `SwitchToTech` 切换 |
| `PopupTechQueueHUD` | `TechnologyCenter/PopupTechQueueHUD` | 研究队列总览（当前 `Refresh` 为空，待完善） |
| `PopupTechQueueBuy` | `TechnologyCenter/PopupTechQueueBuy` | 科研第二队列礼包购买弹窗 |

**`TechnologyCenterMainHUD` 关键流程（入口文件）：**

- `OnLoad`：绑定返回按钮、第二队列礼包购买按钮，注册 `HandleBoughtPackage` 事件，刷新促销区，`ShowAllEntries` 异步加载所有树入口。
- `ShowAllEntries`：遍历 `CResearchCategory.RawList()`，按 `ConditionShow` 过滤后异步实例化 `TechTreeEntry.prefab` 挂到 `treeContainer`。
- 促销区（`RefreshResearchQueue2Promo`）：通过 `ResearchQueue2IapUi.GetSellablePackage()` 判断礼包是否可售（未下发或限购用尽则隐藏整个区域）。

### 4.2 行为组件（Behaviours）

| 组件 | 作用 |
|---|---|
| `TechTreeEntry` | 主界面一个树入口卡片：树名、进度百分比、是否在研、推荐角标、点击进 `TechnologyCenterTreeHUD` |
| `TechTree` | **树状图绘制器**：按 `Layout` 坐标布局节点、连线、对象池复用、自动跳转到「研究中 > 推荐 > 下一可研」目标 |
| `TechItem` | 单个科技节点显示：名称、图标、等级、Buff 新旧值对比、战力增益、置灰（未解锁）、推荐角标 |
| `TechState` | 科技详情的**条件与升级逻辑**：渲染前置条件 + 资源消耗、未满足跳转、研究/立即完成按钮 |
| `ConditionItem` | 单条条件项：支持道具/资源/建筑/科技四类，未满足时显示「前往」按钮并跳转 |
| `TechLine` | 节点连线：根据父节点是否已研究切换亮/暗色，按宽度切换直线/转角线 |
| `TechQueueItem` | 队列展示：进行中倒计时 / 可收取 / 空闲 / 未解锁（含礼包购买）四态，加速、收取按钮 |
| `TechLabel` | 建筑头顶/外部入口气泡：显示当前优先队列，点击按状态收取/看队列/进科技中心 |
| `TechRecommend` | 推荐角标：按 `RecommendType` 切换 `HierarchySnapshot` 快照 |

### 4.3 树状图绘制（`TechTree.cs`）核心逻辑

1. `GetGroupConfigs`：取该树所有科技组，按 `Layout[0]`（行）、`Layout[1]`（列）排序并按行分组；
2. `DrawTechTree`：逐节点 `DrawTechItem` 定位（`x = 列*列宽`，`y = (-行+1)*行高 - 顶部间距`），再 `DrawParentLines` 向前置节点连线；
3. `SortChildren`：调整渲染层级（激活节点在前、亮线压暗线）；
4. `SetJumpTarget`：自动定位到最该关注的节点（研究中 > 推荐 > 下一个可研究），并播放跳转特效；
5. 节点与连线均用**对象池**（`techItemPool` / `techLinePool`）复用。

### 4.4 条件与消耗校验（`TechState` + `ConditionItem`）

`TechState.SetResearchConditions` 是研究前校验的核心，分三步且**前置条件先渲染、消耗后异步拉取**避免阻塞：

1. **前置条件**（`CollectRequirementConditions` 从 `CResearch.Requirement` 收集）→ 异步生成 `ConditionItem`，统计是否全满足 `_prerequisitesMet`；
2. **资源消耗**（`GetTechCosts` 异步拉 `ResearchNeedAck.rssItems`）→ 生成消耗类 `ConditionItem`，收集未满足项 `_unmetRssItems`；
3. 更新预计总时长 `totalTime`、初始化「立即完成」按钮 `btnFinishNow`。

`ConditionItem` 按类型分流：

- **Item / Rss**：比对 `PlayerAssetsMgr` 拥有量，资源未满足显示「获取更多」按钮跳 `UIGetMorePanel`；
- **Building**：未满足跳转建筑（`MoveToBuildingWithGuideArrow`）并关闭科技窗口；
- **Research**：未满足时切换/打开 `TechInfoPopup` 到对应前置科技。

并发安全：`TechState` 使用 `_refreshVersion` 版本号，异步任务回来后通过 `IsRefreshValid` 校验，防止快速切换科技导致的 UI 错乱。

---

## 五、事件机制

系统混用了两套事件总线：

**`EventMgr`（TEventType）—— 框架通用事件：**

- `CityQueueUpdate`：城市队列变化（研究队列即属此类），驱动队列状态刷新；
- `RefreshAssetAck`：资源变化，`TechState` 据此重算条件满足状态；
- `HandleBoughtPackage`：礼包购买成功，刷新第二队列礼包相关 UI。

**`EventMgr1`（TEventType1）—— 科研业务事件：**

| 事件 | 触发时机 | 监听者 |
|---|---|---|
| `TechUpdate` | 科技等级变化/收取 | `TechItem`、`TechState`、`TechLine`、`TechTreeEntry`、`TechQueueItem` |
| `ResearchStart` | 开始研究 | `TechItem`、`TechQueueItem` |
| `ResearchSpeedUp` | 加速 | `TechQueueItem` |

事件均在组件 `OnEnable/Start` 注册、`OnDisable/OnDestroy` 注销。

---

## 六、研究队列与第二队列礼包

### 6.1 队列状态（`TechQueueItem`）

通过 `HierarchySnapshot` 快照在多态间切换：`progress`（倒计时中）/ `archive`（可收取）/ `idle`（空闲）/ `lock`（未解锁）。来源有两种（`Source`）：按队列编号 `QueueIndex` 或按科技 `CfgId` 查找。

### 6.2 第二队列付费解锁

第二研究队列需购买礼包（`CIapTemplate.ResearchQueue2`，`queueIndex = 2`）解锁：

- `ResearchQueue2IapUi`：静态工具类，`GetSellablePackage()` 统一判定可售（未下发或限购用尽返回 null），`ApplyPriceText` 统一价格展示（优先折扣价）；
- `PopupTechQueueBuy`：礼包详情弹窗，展示价格/折扣/奖励列表，走 `UIPayHelper.BuyIapPackage` 支付，成功后延迟 0.2s 关闭（版本号 `_hideAfterPurchaseVersion` 防重复关闭）；
- 主界面促销区、队列锁态购买条、弹窗三处共用 `ResearchQueue2IapUi` 保证逻辑一致；
- 充值积分通过 `IapRechargePointUiKit` 绑定在购买按钮下方展示。

---

## 七、配置依赖总览

### 7.1 `CResearchCategory`（1132）— 科技树/分类

源文件：`1132_research_category.gsheet.xlsx`

| 字段 | 类型 | 含义 |
|---|---|---|
| `id` | int | 分类 ID，如 `11321001`，代码中称「1132 id」 |
| `icon` | string | 主界面入口卡片图标资源名（如 `Icon_Tech_KSFZ`） |
| `lineCnt` | int | 该树布局的总行数，影响 `TechTree` 绘制区域高度 |
| `lc_name` | map | 树名称本地化 key（如 `LC_RESEARCH_research_globe_name_02`） |
| `lc_desc` | map | 树描述本地化 key |
| `display_order` | int | 主界面树入口卡片的排列顺序 |
| `condition_show` | map | **显示条件**：不满足时入口卡片隐藏，`TechnologyCenterMainHUD.ShowAllEntries` 用 `OpExt.CheckConditions` 过滤 |
| `condition` | map | **解锁条件**：不满足时卡片图标置灰、不可点击（`TechTreeEntry` 中判断） |

### 7.2 `CScienceLayout`（1181）— 科技组（树节点）

源文件：`1181_science_layout.gsheet.xlsx`

| 字段 | 类型 | 含义 |
|---|---|---|
| `id` | int | 科技组 ID，如 `11812001`，代码中称「1181 id」，是大部分接口的主入参 |
| `layout` | int[2] | 节点在树中的坐标 `[行, 列]`，`TechTree` 用此计算像素位置：`x = 列 * 列宽`，`y = (-行+1) * 行高` |
| `pregroup` | int[] | **前置科技组 ID 列表**，决定：① 解锁判定（`IsUnlocked`：前置全部 > 0 级）；② 连线绘制方向；③ 有多个前置时连线取「倒置」样式 |
| `frame` | string | 节点特效帧标识，值为 `"wing"` 时显示金色翅膀装饰（`TechItem` 中判断） |
| `icon` | string | 节点图标资源名，未解锁时置灰显示 |
| `lc_name` | map | 科技名称本地化 key |
| `lc_desc` | map | 科技描述本地化 key |

### 7.3 `CResearch`（1119）— 科技等级条目

源文件：`1119_玩家科技_research.gsheet.xlsx`（共两个 Sheet：D23 新版英雄科技 / 旧版常规科技）

| 字段 | 类型 | 含义 |
|---|---|---|
| `id` | int | 等级条目唯一 ID（如 `11190101`），通常为 `research_id` + 等级后缀 |
| `research_id` | int | 所属科技组 ID（关联 1181），`TechData` 中以此为 key 存储等级数据 |
| `category` | int | 所属科技树 ID（关联 1132），`GetTreeProgress` / `HasInResearch` 按此筛选 |
| `lvl` | int | 本条目代表的等级值，从 1 起计 |
| `lvl_max` | int | 该科技的最大等级，`TechData.GetMaxLevel` 查此字段 |
| `cost_time` | int64 | 研究耗时（**毫秒**），`TechState` 中除以 1000 转秒后格式化显示 |
| `cost_asset` | array | 研究消耗的资源列表，每项 `{typ, id, val}`，服务器通过 `ResearchNeedAck` 下发，客户端缓存在 `_techCostsCache` |
| `requirement` | map | 解锁前置条件，格式 `{op, args:[{op,typ,id,val}...]}`；支持建筑等级、科技等级等类型；`TechState.CollectRequirementConditions` 解析后渲染为 `ConditionItem` |
| `status` | array | 研究效果列表，每项 `{typ, id, val}`；`typ="buff"` 为属性加成（`TechItem` 展示新旧值对比），`typ="power"` 为战力增益 |
| `add_asset`（旧版） | array | 研究完成额外奖励资源 |
| `path`（旧版） | map | 布局坐标 `{col, row}`，旧版用此替代 `layout`，新版已迁移到 1181 |
| `PreTech`（旧版） | array | 旧版前置科技 ID 列表，新版已迁移到 1181 的 `pregroup` |

### 7.4 辅助配置表

| 配置表 | 用途 |
|---|---|
| `CBuff` / `CBuffCategory` | Buff 定义与数值格式，`valFormat.Typ` 为 `"int"` 或 `"percent"`（万分比转百分数） |
| `1182_recommended_science` | 服务器推荐科技来源配置，对应 `ResearchNtf` 中 `EconomicRecommendTech` / `MilitaryRecommendTech` |
| `CIapTemplate` | IAP 礼包模板，`ResearchQueue2` 常量对应第二研究队列礼包 |

---

## 八、关键设计要点与约定

1. **ID 严格区分**：方法注释普遍标注入参是 1132/1181/1119，调用时务必传对类型，混用会查不到配置。
2. **消耗缓存按 (科技,等级) 维度**：升级后须 `InvalidateTechCostsCache` 清理，否则显示旧消耗。
3. **队列收取的特殊处理**：收取结束依赖 `CityQueueUpdate` 而非 `ResearchNtf`（后者传空列表无法对照删除）。
4. **异步刷新防错乱**：`TechState` 用 `_refreshVersion`、`PopupTechQueueBuy` 用版本号，均为防止异步回调作用到已切换的 UI。
5. **对象池复用**：树节点与连线复用，避免频繁实例化。
6. **促销三处共用判定**：第二队列礼包的可售判断集中在 `ResearchQueue2IapUi`，避免多处逻辑漂移。
7. **大量被注释代码**：`PopupTechQueueHUD.Refresh`、`TechState.SetResearchingState`、`TechLabel` 快照切换等存在待完善 / 已迁移逻辑，属开发中状态。
