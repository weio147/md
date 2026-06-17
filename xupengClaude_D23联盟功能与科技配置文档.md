# D23 联盟功能代码结构与配置文档

> 适用分支：`feature/0.0.3/union` ｜ 引擎：Unity 2022.3 + TFW 框架 ｜ 语言：C#
> 本文聚焦 D23 时期联盟（Union/Alliance）功能，**重点分析"联盟科技"（Union Research / Union Tech）子功能**的逻辑结构及其对应的配置文档。

---

## 一、联盟功能整体代码结构

### 1.1 分层架构

联盟功能遵循项目统一的分层模式：

```
┌──────────────────────────────────────────────┐
│ UI 层   D23Code/UI/Alliance/  (UIXxx)         │  界面展示与交互
├──────────────────────────────────────────────┤
│ 逻辑层  GameLogic/Alliance/   (LAllianceXxx)  │  单例 Mgr，业务逻辑/网络/缓存
├──────────────────────────────────────────────┤
│ 实体层  GameLogic/Entity/Union* (LMapEntity*) │  大地图联盟建筑实体
├──────────────────────────────────────────────┤
│ 协议+配置  Protos/ (req/ack/ntf) + Cfg config │  数据结构、策划配置表
└──────────────────────────────────────────────┘
```

- **UI ↔ 逻辑**：通过 `EventMgr`（业务事件）解耦，UI 订阅事件刷新。
- **逻辑 ↔ 服务端**：通过 `MessageMgr` 注册/收发协议（`Req` 请求、`Ack` 应答、`Ntf` 推送）。
- **单例命名规律**：`L` = Logic 单例（继承 `TFW.Utility.Singleton<T>`）。
  - `LAlliance*`：联盟通用功能
  - `LAT*`：Alliance Treasure，资源/战利品/遗迹
  - `LUnion*` / `LUnionBattle*`：联盟战、旗帜等
  - `LMapEntity*`：大地图实体

### 1.2 子功能模块总览

| 子功能模块      | 逻辑层（Logic）                                                | UI 层                                 | 实体/战斗                               |
| ---------- | --------------------------------------------------------- | ------------------------------------ | ----------------------------------- |
| **联盟科技** ⭐ | `LAllianceTech`                                           | `UIUnionTech` + `UI/Alliance/Tech/`  | —                                   |
| 联盟主页/概览    | `LAllianceMain`、`LAllianceMgr`                            | —                                    | —                                   |
| 创建联盟       | `LAllianceCreate`                                         | —                                    | —                                   |
| 成员/邀请/帮助   | `LAllianceHelp`、`LAllianceInvited`、`LAllianceApplyRecord` | `UiJoinApplication`、`UiMemberStatus` | —                                   |
| 建筑系统       | `LAllianceBuildingManager`                                | —                                    | `LMapEntityUnionCenter/Flag/Attach` |
| 旗帜系统       | `LUnionFlagMgr`                                           | `UIAllianceFlagSet`                  | `LMapEntityUnionFlag`               |
| 采集系统       | —                                                         | —                                    | `LMapEntityUnionGather`             |
| 指挥部/战争     | `LAllianceCommandPost`                                    | —                                    | `LUnionBattleSignUp/Field`          |
| 发展任务       | `LAllianceDevelopment`                                    | `AllianceProgress`                   | —                                   |
| 礼物/仓库/充值   | `LAllianceGift`、`LATWareHouse`                            | `UI/Alliance/Recharge/*`             | —                                   |
| 遗迹战斗       | `LATHumanRelic`、`LATRuinsBooty`                           | —                                    | `LUnionBattleField`                 |
| 排行榜/推荐     | `LAllianceRank`、`LAllianceRecommend`                      | —                                    | —                                   |
| 红点系统       | `LAllianceRedPoint`、`RedPoint/*`                          | —                                    | —                                   |
| 情报预警       | `LIntelligence`                                           | —                                    | —                                   |

### 1.3 关键目录路径

```
逻辑层：  Assets/P2/GameScript/GameLogic/Alliance/
联盟战：  Assets/P2/GameScript/GameLogic/UnionBattle/
旗帜：    Assets/P2/GameScript/GameLogic/UnionFlag/
实体：    Assets/P2/GameScript/GameLogic/Entity/Union{Center,Flag,Attach,Gather,Member,BattleCity}/
UI：      Assets/P2/GameScript/GameScriptMain/D23Code/UI/Alliance/
配置：    Assets/P2/GameScript/GameData/Config/
协议：    Assets/P2/GameScript/GameData/Protos/
```

---

## 二、联盟科技（Union Tech）子功能逻辑结构 ⭐

联盟科技是联盟功能中最核心、逻辑最完整的子模块。其架构为三层：

```
UIUnionTech（表现层）
      ↕ EventMgr 事件 / 方法查询
LAllianceTech（业务逻辑层，单例）
      ↕ MessageMgr 协议
服务端（Req / Ack / Ntf）
```

### 2.1 业务逻辑层：LAllianceTech

**文件**：`Assets/P2/GameScript/GameLogic/Alliance/LAllianceTech.cs`

职责：管理全部科技数据、捐献/研究/技能释放的请求、状态判定、奖励领取、CD/次数恢复的每秒检查。

#### 2.1.1 核心数据缓存

| 字段 | 类型 | 含义 |
|---|---|---|
| `m_TechMap` | `Dict<int, UnionTech>` | 所有科技运行时数据（techID → UnionTech） |
| `m_ResearchingCgfId` | `int` | 当前正在研究的科技配置 ID |
| `m_ResearchingEndTS` | `long` | 研究结束时间戳（ms） |
| `m_DonateCoin` | `long` | 本周期累计捐献积分（贡献度） |
| `m_DonateCost` | `long` | 钻石捐献当前消耗 |
| `m_DonateTime` / `m_MaxDonateTime` | `int` / `float` | 剩余 / 每日最大资源捐献次数 |
| `m_NextRecoverTime` | `long` | 下次恢复捐献次数的时间戳 |
| `m_FirstDonateCost` / `m_NextDonateCost` | `long` | 首次钻石捐献基础消耗 / 后续递增消耗 |
| `m_ResearchRewardDic` / `m_ResearchGirlDic` | `HashSet<int>` | 已领取的满级普通奖励 / 满级英雄奖励 |

#### 2.1.2 状态机枚举

```csharp
enum TechStatus {           // 普通科技状态
    Error, PreTechLock,     // 错误 / 前置未解锁
    NoMatchRequirement,     // 不满足条件
    CanDonate, CanResearch, // 可捐献 / 可研究
    MaxLevel, Researching   // 满级 / 研究中
}
enum ActiveSkillStatus {    // 主动技能状态
    PreTechLock, CanDonate,
    CanCast, Active, CoolDown
}
enum DonateType { vm = 0, rss = 1 }  // vm=钻石快捐, rss=资源捐献
enum RewardGetState { none, canGet, reward }  // 满级奖励领取状态
```

#### 2.1.3 关键方法

**网络请求**
- `ReqAllianceTech(bool isBrief)` / `ReqAllianceTechAsync(...)` — 拉取科技完整/简略信息（异步带超时）
- `ReqAllianceTechDonate(int configId, DonateType)` — 提交捐献（资源或钻石）
- `ReqAllianceTechResearch(int configId)` — 提交研究/升级
- `ReqCastSkill(int configId)` — 释放主动技能
- `ReqSetAllianceTechRecommend(int category, bool)` — 设置推荐分类（盟主/官员）
- `ReqReward(int techID, int type)` — 领取满级奖励（type：0=普通，1=英雄）

**状态/数据查询**
- `GetTechStatus(int techId)` → `TechStatus`
- `GetActiveSkillStatus(int techId)` → `ActiveSkillStatus`
- `GetAllianceTechInfo(int techId)` → `UnionTech`
- `GetTechCfg(int researchId, int curLevel)` → `Cfg.CUnionResearch`（按当前等级取对应配置）
- `GetTechConfigId(researchId, level)` → `researchId * 100 + level`（科技 ID 与等级合成配置 ID 的规律）
- `GetDonateCost()` / `GetDonateTime()` / `GetDailyContribution()`

**条件判定**
- `CheckPreTechUnlock(researchId)` — 前置科技是否全部解锁
- `TechIsUnlock(researchId, level)` — 是否满足解锁条件（对应配置 `Requirement`）
- `TechCategoryUnlock(category cfg)` — 分类是否解锁（按联盟总等级）
- `CanRssDonate()` / `DonateTimeMax()` — 资源捐献次数判断
- `IsMax(int type)` — 指定分类是否全部满级

#### 2.1.4 主要事件（EventMgr）

| 事件 | 触发时机 |
|---|---|
| `UnionResearchNtf` / `UnionResearchAck` | 收到科技全量推送 / 拉取应答 |
| `UnionTechUpdate` | 科技数据更新（参数为更新的 techID 列表） |
| `UnionTechResearchingChanged` | 当前研究科技改变 |
| `UnionTechDonateGaugeChanged` | 捐献进度改变 |
| `UnionTechDonateCostChanged` / `UnionTechRssDonateTimesChanged` | 钻石消耗 / 资源次数改变 |
| `UnionTechDonateAck` / `UnionTechResearchAck` / `UnionTechRewardAck` | 捐献 / 研究 / 领奖应答 |
| `UnionActiveSkillCdChanged` / `UnionActiveSkillCdEnd` | 主动技能 CD 改变 / 结束 |

#### 2.1.5 每秒帧更新 `OnPerSecondUpdate()`
- 检查主动技能 CD 是否结束 → 发 `UnionActiveSkillCdEnd`
- 检查资源捐献次数是否到恢复时间 → 恢复并通知

### 2.2 表现层：UIUnionTech

**文件**：`Assets/P2/GameScript/GameScriptMain/D23Code/UI/Alliance/UIUnionTech.cs`（`Tech/` 子目录存放配套 Item 等）

界面结构：

```
UIUnionTech
├─ 三个分类 Tab          (TYPE1/2/3 = 18170001/02/03)
├─ 科技列表 (TFWLoopListView)
│   ├─ Item0 当前研究中（进度条、扫光）
│   ├─ Item1 英雄奖励展示（cfg 为空时）
│   ├─ Item2 未解锁科技
│   └─ Item3 已完成/满级科技
├─ 捐献按钮区
│   ├─ 资源捐献（有次数时）
│   └─ 钻石快捐（无次数时，富文本显示消耗）
├─ 推荐星标 ×3（每个 Tab 一个）
└─ 红点 ×3（每个分类未领奖数）
```

关键刷新逻辑：
- `SetData()`：按 Tab 选择科技列表，计算当前应展示的科技 index
- `RefreshUpgradeBtn(canRssDonate)`：满级显示"升级完成"；有资源次数显示资源消耗；否则显示钻石消耗
- `OnUnionTechDonateAck(crit)`：根据暴击倍数（`critNum` = 1/2/5/10）播放暴击 + 飞币特效，延迟刷新

### 2.3 协议结构

**文件**：`Protos/req.cs`、`ack.cs`、`ntf.cs`，数据体扩展 `Protos/Ext/UnionTech.cs`

#### 请求 Req
| 协议 | 关键字段 |
|---|---|
| `UnionResearchReq` | `brief:bool` 是否简略 |
| `UnionTechDonateReq` | `typ:string`("vm"/"rss")、`techID:int` |
| `UnionTechResearchReq` | `techID:int` |
| `UnionTechCastSkillReq` | `techID:int` |
| `UnionTechRecommendReq` | `category:int`、`isRecommend:bool` |
| `UnionTechGetMaxLvRewardReq` | `techID:int`、`rewardTyp:int`(0普通/1英雄) |

#### 应答 Ack
| 协议 | 关键字段 |
|---|---|
| `UnionTechDonateAck` | `errCode`、`critNum:int`（暴击倍数 1/2/5/10） |
| `UnionTechGetMaxLvRewardAck` | `techID`、`maxLvReward/maxHeroReward:bool`、`rewards:List<CValTypId_isi>` |

#### 推送 Ntf
| 协议 | 关键字段 |
|---|---|
| `UnionResearchNtf` | `researchingTechID`、`researchingEndTS`、`donateGauge`、`settleDeadline`、`coinDonateTimes`、`remainDonateTimes`、`donateRecoverTs`、`tech:List<UnionTech>`、`maxLvReward/maxHeroReward:List<int>`、`recommendCategory` |
| `UnionTechNtf` | `researchingTechID`、`researchingEndTS`、`tech:List<UnionTech>` |
| `ResearchActiveCDNtf` | `activeSkillCD:List<ResearchActiveCDInfo>` |

**UnionTech 数据体**（`Protos/Ext/UnionTech.cs`）：
```csharp
class UnionTech {
    int  techID;       // 科技配置 ID
    int  level;        // 当前等级
    long donateGauge;  // 捐献进度 (0 ~ MaxXp)
    bool isLocked;     // 是否锁定（前置未解锁）
    bool isRecommend;  // 是否被推荐
    long cdEndTs;      // 主动技能 CD 结束时间戳
    long castTs;       // 技能释放时间戳
}
```

### 2.4 完整业务流程

```
① 打开界面
   点击"科技" → UIUnionTech.ShowTech() → ReqAllianceTechAsync(brief=false)
   → 等 UnionResearchAck → WndMgr.Show<UIUnionTech>() → 用 Ntf 数据首刷

② 捐献（核心循环）
   点资源/钻石捐献按钮 → 校验跨服/资源/钻石
   → ReqAllianceTechDonate(cfgId, rss/vm) → UnionTechDonateReq
   → UnionTechDonateAck(critNum) → 播暴击+飞币特效 → 刷新进度

③ 研究/升级
   donateGauge ≥ MaxXp → 状态变 CanResearch
   → 用户点"研究" → ReqAllianceTechResearch → 服务端推 UnionResearchNtf
   → researchingTechID/EndTS 更新 → 每秒检查到点完成 → 等下次推送刷新

④ 满级奖励
   level == LvlMax 且进度满 → 显示"可领取"
   → ReqReward(researchId, type) → UnionTechGetMaxLvRewardAck(rewards)
   → 展示奖励 → 标记已领取

⑤ 主动技能
   分类为主动技能 → 状态 CanCast → ReqCastSkill
   → ResearchActiveCDNtf(cdEndTs) → 每秒检查 CD → CD 结束发 UnionActiveSkillCdEnd
```

---

## 三、联盟科技配置文档（Config）

联盟科技涉及一组生成配置类（`Const`）+ 手写扩展（`Extension`）+ KvK 变体。

### 3.1 配置类与策划表对应

| 配置类                          | 策划表                          | 主键   | 说明               |
| ---------------------------- | ---------------------------- | ---- | ---------------- |
| `CUnionResearch`             | union_research               | `Id` | 科技主表：属性、消耗、效果、奖励 |
| `CUnionResearchCategory`     | union_research_category      | `Id` | 科技分类表：分类、解锁条件    |
| `CUnionResearchDonationRank` | union_research_donation_rank | `Id` | 捐献排名奖励表          |

> 生成的配置定义集中在 `Assets/P2/GameScript/GameData/Config/Gen/CfgGenerated.cs`。

### 3.2 CUnionResearch（科技主配置）字段详解

**基础信息**
| 字段 | 类型 | 含义 |
|---|---|---|
| `Id` | int | 科技配置唯一 ID（主键），= `researchId*100 + level` |
| `TechnologyId` | int | 技术 ID（主动技能用 `SkillTechIdPrefix` 前缀区分） |
| `Category` | int | 所属分类（→ `CUnionResearchCategory.Id`） |
| `Quality` | int | 品质（影响显示） |
| `Lvl` / `LvlMax` | int | 当前等级 / 最大等级 |

**前置与解锁**
| 字段 | 类型 | 含义 |
|---|---|---|
| `PreTech` | `List<CId>` | 前置科技列表 |
| `Requirement` | `COpArgs_sissi` | 解锁条件表达式（`Args` + `Op` 逻辑符 `&&/\|\|`） |

**消耗与进度**
| 字段 | 类型 | 含义 |
|---|---|---|
| `DonateCost` | `List<CValTypId_isi>` | 捐献消耗（`Id`资源/物品、`Typ`类型、`Val`数量） |
| `CostTime` | int | 研究耗时（秒） |
| `Cd` | int | 技能冷却时间 |
| `Xp` / `MaxXp` | int | 单次获得经验 / 进度上限 |

**效果加成**
| 字段 | 类型 | 含义 |
|---|---|---|
| `Status` | `List<CValTypIdArg1>` | 效果列表；当 `Typ=="buff"` 时 `Id`→`CBuff.Id`，经 `CBuff.Category`→`CBuffCategory` 取名与格式化值 |

**奖励**
| 字段 | 类型 | 含义 |
|---|---|---|
| `MemberAward` | `List<CValTypId_isi>` | 成员研究完成奖励 |
| `MaxLvAward` | `List<CValTypId_isi>` | 科技满级普通奖励 |
| `MaxLvHeroAward` | `List<CValTypId_isi>` | 科技满级英雄奖励 |
| `UseCost` | `List<CValTypId_isi>` | 主动技能使用消耗 |

**本地化与显示**
| 字段 | 类型 | 含义 |
|---|---|---|
| `LcName` / `LcDesc` | `CTypTxt` | 名称 / 描述（多语言） |
| `DisplayKey` / `DisplayOrder` | int | 排序键 / 显示顺序 |
| `Path` | `CRowCol` | 科技树坐标（Row/Col） |
| `Icon` | string | 图标资源路径 |

### 3.3 CUnionResearchCategory（分类配置）

| 字段 | 类型 | 含义 |
|---|---|---|
| `Id` | int | 分类主键（18170001/02/03 对应三个 Tab） |
| `Requirement` | int | 分类解锁条件（如等级需求） |
| `LcName` / `LcDesc` | `CTypTxt` | 分类名称 / 描述 |
| `DisplayKey` | int | 排序键 |
| `UseType` | int | 用途标记 |

### 3.4 CUnionResearchDonationRank（捐献排名奖励）

| 字段 | 类型 | 含义 |
|---|---|---|
| `Id` | int | 主键 |
| `GroupId` | int | 捐献分组 ID |
| `MinRank` / `MaxRank` | int | 排名区间（含两端） |
| `RankReward` | `List<CSettingOwnerAsset>` | 该排名区间奖励 |

> 用于按联盟成员的捐献贡献度排名发放奖励。

### 3.5 Const 常量类 vs Extension 扩展类

**Const：`Config/Const/CUnionReserch.cs`**（注意文件名拼写 Reserch）
```csharp
namespace Cfg.Const {
    public class CUnionResearchDefault {
        public virtual int SkillTechIdPrefix => 1831;  // 主动技能 technology_id 前缀
    }
    public class CUnionResearch : CConstantDefinition<CUnionResearchDefault> {
        public static int SkillTechIdPrefix => instance.SkillTechIdPrefix;
    }
}
```
作用：提供"主动技能 ID 前缀"常量，逻辑层据此判断某科技是否为主动技能。

**Extension：`Config/Extension/CUnionResearch.cs`**（`partial class CUnionResearch`）
- `Name` → `LocalizationMgr.Get(LcName.Txt)`，取本地化名称
- `Description` → `GetDesc()`：遍历 `Status` 中 `Typ=="buff"` 的项，查 `CBuff`/`CBuffCategory` 取 buff 名，用 `CfgStatusHelper.GetFormattedStatusValue` 格式化数值，拼接多语言模板 `LC_UNION_active_skill_buff_show_{N}`（N=buff 数）

**分工**：Const 提供生成的硬编码常量；Extension 在生成类基础上手写便捷属性与动态计算（本地化、效果描述格式化），互不覆盖（partial）。

### 3.6 KvK（跨服战）配置变体

**文件**：`Config/Const/KvK/CUnionResearchKvK.cs`、`CUnionResearchKvK2.cs`

设计意图：不同 KvK 赛季使用专属的主动技能 ID 前缀，避免与常规及其它赛季冲突：

| 配置 | SkillTechIdPrefix | 用途 |
|---|---|---|
| `CUnionResearchDefault` | 1831 | 常规版 |
| `CUnionResearchKvK` | 2585 | KvK 第一季 |
| `CUnionResearchKvK2` | 3253 | KvK 第二季 |

相关 buff 常量见 `Config/Extension/X11CfgEx/X11CfgEx.cs`，如 `BcUnionResearchDonateRecoveryTimePct`（联盟科技捐献次数恢复时间百分比加成）。

### 3.7 配置关联关系图

```
CUnionResearch (科技主表)
 ├─ Category ───────────→ CUnionResearchCategory
 ├─ PreTech ────────────→ 其它 CUnionResearch.Id（前置依赖）
 ├─ Requirement ────────→ COpArgs_sissi（解锁条件表达式）
 ├─ DonateCost/各类Award→ CValTypId_isi（资源/物品 ID+类型+数量）
 ├─ Status (Typ=="buff")→ CBuff.Id → CBuff.Category → CBuffCategory（效果名/值）
 └─ Path ───────────────→ CRowCol（科技树坐标）

CUnionResearchDonationRank (捐献排名)
 ├─ GroupId  → 科技分组
 └─ RankReward → 排名奖励

KvK 变体：CUnionResearchKvK / KvK2 仅覆盖 SkillTechIdPrefix
```

---

## 四、关键设计要点小结

1. **配置 ID 规律**：科技配置 `Id = researchId * 100 + level`，逻辑层 `GetTechConfigId` / `GetTechCfg` 据此在"科技 + 等级"与"具体配置行"间转换。
2. **效果通过 buff 系统实现**：科技 `Status` 不直接写数值，而是引用 `CBuff`，经 buff 分类格式化，便于复用与多语言展示。
3. **捐献双通道**：资源捐献（`rss`，有每日次数与恢复机制）和钻石快捐（`vm`，消耗递增），暴击倍数 `critNum` 增加进度。
4. **科技树三分类**：`CUnionResearchCategory` 三个分类（18170001/02/03）对应 UI 三 Tab，分类按联盟等级解锁。
5. **KvK 隔离**：仅通过 `SkillTechIdPrefix` 前缀区分赛季技能，配置主体复用，扩展成本低。
6. **生成 + 扩展分离**：`Const`（生成、只读常量）与 `Extension`（手写 partial，本地化/计算）解耦，重新生成配置不会覆盖手写逻辑。

---

## 五、文件路径速查

```
逻辑层
  科技：  Assets/P2/GameScript/GameLogic/Alliance/LAllianceTech.cs
  主页：  Assets/P2/GameScript/GameLogic/Alliance/LAllianceMain.cs
  红点：  Assets/P2/GameScript/GameLogic/Alliance/LAllianceRedPoint.cs

UI 层
  科技：  Assets/P2/GameScript/GameScriptMain/D23Code/UI/Alliance/UIUnionTech.cs
  科技Item：Assets/P2/GameScript/GameScriptMain/D23Code/UI/Alliance/Tech/

配置
  常量：  Assets/P2/GameScript/GameData/Config/Const/CUnionReserch.cs
  扩展：  Assets/P2/GameScript/GameData/Config/Extension/CUnionResearch.cs
  KvK：   Assets/P2/GameScript/GameData/Config/Const/KvK/CUnionResearchKvK.cs / KvK2.cs
  生成：  Assets/P2/GameScript/GameData/Config/Gen/CfgGenerated.cs
  公共类型：Assets/P2/GameScript/GameData/Config/Gen/CommonType/CommonTypeGenerated.cs

协议
  请求/应答/推送：Assets/P2/GameScript/GameData/Protos/{req,ack,ntf}.cs
  科技数据体：    Assets/P2/GameScript/GameData/Protos/Ext/UnionTech.cs

引导
  科技引导：Assets/P2/GameScript/GameScriptMain/FTE/Guide/GuideAllianceTech.cs
```
