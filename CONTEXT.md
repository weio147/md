# 任务上下文 (CONTEXT)

> 分支：`feature/0.0.3/union`
> 更新时间：2026-06-16

## 当前目标
联盟（Union/Alliance）X11 相关 UI 的一系列功能完善与修复，覆盖配置读取健壮性、
信息修改校验、申请/加入流程、成员列表展示与分组吸顶等。

## 已完成修改

### 1. 配置读取健壮性 — `Assets/P2/GameScript/GameLogic/Alliance/LAllianceMgr.cs`
- `CreateUnionNameCoinNum()` / `CreateUnionNickNameCoinNum()`：读取 `UnionChangeNameCost.Quintuple[0]`
  前加 `Count > 0` 判空，空数组返回 `0`，避免越界崩溃。

### 2. 联盟名称/简称合法字符校验（X11 修改信息 UI）
- `Assets/P2/GameScript/GameScriptMain/UI/AllianceX11/UIPopupAllianceInfoEditSub.cs`
  - 新增 `charValidator`，复用 `LAllianceMgr.CheckTextLegal`（长度 + 字符规则）；
    非法时禁用确认按钮并显示提示（`LC_UNION_length_limit_less_greater_short_tip` /
    `LC_UNION_illegal_word_short_tip`）。
- `Assets/P2/GameScript/GameScriptMain/UI/AllianceX11/UIPopupAllianceInfoEdit.cs`
  - 名称用 `LAllianceMgr.NameRegular`（3–15、禁符号），简称用 `TagRegular`（3–4、海外版仅字母数字）。

### 3. 语言 Toggle 选中显示修复 — `Assets/P2/GameScript/GameScriptMain/UI/Alliance/UIAllianceCreateLang.cs`
- `Refresh` 改用 `SetIsOnWithoutNotify` + `selected.SetActive` 直接驱动视觉，
  修复首次打开（未 LogicShown）时已选中项不显示勾选的问题。

### 4. 联盟资料页申请/加入 — `Assets/P2/GameScript/GameScriptMain/UI/AllianceX11/UIPopupAllianceProfile.cs`
- 自己无联盟（`!HasAlliance()`）时才显示加入相关按钮。
- 补全 `已申请`/`直接加入`/`申请` 三按钮逻辑（参考 `UIAlliancesListItem`），
  注册 `AllianceJoin`/`AllianceCancelApply` 事件实时刷新按钮。
- `OnBtnButton_ApplyClick` 增加入盟条件校验：主堡等级或战力未达标弹 tips、不申请。
- 打开流程改为「先开界面、界面内 `RequestUnionInfo` 早请求、回调 `FreshUI` 刷新」；
  `PopupAllianceProfileData` 增加 `unionId`，`UIAlliancesListItem.OnBtnItem_AllianceFlagClick` 配合改为直接开窗。

### 5. 语言相同判断 — `Assets/P2/GameScript/GameScriptMain/UI/AllianceX11/UIAlliancesListItem.cs`
- `languageSame = unionInfo.lang == LocalizationMgr.CurrentLanguage`。

### 6. 成员列表 — `Assets/P2/GameScript/GameScriptMain/UI/AllianceX11/UIAlliancesMemberList.cs`
- `InitDefaultGroupShow`：打开时默认展开自己所在阶级；盟主(R5)默认展开 R4。
- **分组吸顶（已验证）**：纯代码悬浮覆盖层实现。
  - 运行时实例化 `AlliancesMemberListGrade` 预制体挂到 viewport，监听 `ScrollRect.onValueChanged`。
  - `UpdateStickyHeader`：找到跨越可视区顶沿的项，判定当前阶级并驱动悬浮头显隐/内容；
    `GetGroupInfo` 取对应 Group 数据，`m_stickyGradeShown` 缓存避免每帧重复 `SetData`。
  - Group 头一旦被顶部遮挡（`Offset < 0`）即隐藏真实 `m_BtnBtn`、由悬浮头接管显示。
  - **仅展开状态**的 Group 才吸顶（`topData.showFlag`），折叠 Group 正常滚动不悬停。

### 7. 成员阶级 "me" 标记 — `Assets/P2/GameScript/GameScriptMain/UI/AllianceX11/UIAlliancesMemberListGrade.cs`
- 仅在「自己所在联盟且自己所在阶级」时显示 `m_GoImage_me`，
  用 `LAllianceMgr.GetMemberClassInfo(self, viewedUnion)` 判断（`UIAlliancesMemberList` 暴露 `UnionInfo`）。
- 新增 `SetHeaderVisible`（供吸顶遮挡控制），`ApplyVisual` 默认恢复显示防回收残留。

## 待修改文件 / 后续可选项
- `LAllianceMgr.CreateUnionFlagCoinNum()`：仍用 `try/catch` 兜底访问 `Quintuple[0].Val`，
  建议统一为 `Count > 0` 判空风格。
- 排查其它直接以 `Quintuple[0]` 形式读取配置的调用点，确认越界风险。

## 设计原则
- 读取配置数组前判空、取安全默认值，不依赖 `try/catch` 吞异常。
- 校验逻辑集中复用（`CheckTextLegal`），名称/简称规则与 D23 创建保持一致。
- 申请与直接加入服务端同一接口 `JoinUnionReq`，UI 仅按 `NeedApply` 区分展示。
- 循环列表（`TFWLoopListView`）的吸顶用悬浮覆盖层，不改 prefab；回收项默认恢复显示，
  遮挡显隐由列表统一在滚动回调中控制。

## 注意事项
- 配置键：`Cfg.Const.CX11ConstConfig.UnionChangeNameCost`、`UnionChangeFlagCost`；
  金币返回类型名称/简称为 `long`、旗帜为 `int`，注意不要混用。
- 申请条件提示文案目前沿用占位串（`总部等级>={0}`/`战斗力>={0}`，带 `//TODO`），
  若有正式本地化 key 需替换。
- 吸顶悬浮头复用 `UIAlliancesMemberListGrade.SetData(info, this)`，点击可折叠当前阶级。
- 提交前确认未引入新的编译/Lint 错误。
