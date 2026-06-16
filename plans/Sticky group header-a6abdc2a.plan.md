<!-- a6abdc2a-2865-4114-84cc-012584a631b1 -->
---
todos:
  - id: "fields"
    content: "在 UIAlliancesMemberList 增加 m_stickyGroup / m_scrollHooked 字段及（可选）grade->Group 数据缓存"
    status: pending
  - id: "create-overlay"
    content: "首次 InitListView 后实例化 AlliancesMemberListGrade 预制体到 viewport 作为悬浮吸顶头，顶部锚定、SetAsLastSibling、初始隐藏"
    status: pending
  - id: "hook-scroll"
    content: "注册 ScrollRect.onValueChanged -> OnListScroll，加防重复注册标记"
    status: pending
  - id: "update-logic"
    content: "实现 UpdateStickyHeader：找顶边 item、按 itemClass==Group 隐藏/否则显示对应 grade 的 Group，搜索态无 Group 自动隐藏"
    status: pending
  - id: "refresh-hooks"
    content: "在 RefushList 末尾调用 UpdateStickyHeader，保证展开/折叠/刷新后同步"
    status: pending
  - id: "cleanup"
    content: "OnHidden 隐藏悬浮头；OnDestroyed 移除监听并销毁悬浮头"
    status: pending
  - id: "verify-geometry"
    content: "实现时验证 Offset 方向与悬浮头锚点对齐（竖向列表、顶部贴合 viewport）"
    status: pending
isProject: false
---
# 联盟成员列表 Group 吸顶

## 目标
在 [UIAlliancesMemberList.cs](Assets/P2/GameScript/GameScriptMain/UI/AllianceX11/UIAlliancesMemberList.cs) 中，为 `m_ListScrollView_member_list` 增加一个悬浮吸顶头：上滑时把"当前位于可视区顶部的阶级"的 Group 固定在最上沿；该阶级所有 Item 被遮挡、下一个阶级头到顶后，吸顶头切换为下一个阶级（即上一个隐藏）。纯代码实现（方案 A），边界处简单切换（无顶推动画）。

## 核心思路
循环列表会回收 item，无法直接钉住列表内的 Group，因此用一个悬浮覆盖层：
- 运行时实例化 `AlliancesMemberListGrade` 预制体，挂到 ScrollView 的 `viewport` 下（被 ScrollRect 的 mask 裁剪），`SetAsLastSibling` 保证盖在内容之上。
- 监听 `ScrollRect.onValueChanged`，每次滚动重算"顶部所在分区"，更新吸顶头内容与显隐。

## 判定算法（关键）
数据顺序固定：grade 高在前，每个分区 = `[Group, Items..., (R4 的 Tips)]`。
1. 在已显示 item 中找到"跨越可视区顶边"的 item（`topItem`）：遍历 `GetShownItemByIndex(i)`，取满足 `Offset <= 0 && Offset + ItemSize > 0` 的项（`Offset` 为 item 顶部相对 viewport 顶部的距离，<=0 表示已到/超出顶部）。找不到则取第 0 个。
2. `topData = datas[topItem.ItemIndex]`。
3. 显隐规则：
   - `topData.itemClass == Group`：真实 Group 头正好在顶部，隐藏悬浮层（避免重影）。
   - 否则（Item / Tips）：该分区真实 Group 头已滚到顶部之上，显示悬浮层，内容取该 `grade` 对应的 Group 数据，钉在 viewport 顶部。
   - 找不到该 grade 的 Group 数据（如搜索态只有 Item）：隐藏悬浮层。

这样真实头滚到顶→上移的瞬间悬浮层无缝接管，下一个真实头到顶时悬浮层隐藏→其上移后显示下一个分区，实现"上一阶级 Item 全部遮挡后切到下一阶级"。

## 改动点（均在 UIAlliancesMemberList.cs）

### 新增字段
- `private UIAlliancesMemberListGrade m_stickyGroup;`（悬浮头组件）
- `private bool m_scrollHooked;`（避免重复注册 onValueChanged）
- 可选：`Dictionary<AllianceClassEnum, UnionMemberGradeInfo>` 或在 `FreshDatas` 内缓存各 grade 的 Group 数据，供吸顶头取用。

### 创建悬浮头与挂钩滚动
在首次 `InitListView` 之后（`RefushList` 里 init 分支末尾，或单独 `EnsureStickyHeader()`）：
- `var prefab = m_ListScrollView_member_list.GetItemPrefabConfData("AlliancesMemberListGrade").mItemPrefab;`
- `Instantiate(prefab, m_ListScrollView_member_list.ViewPortRectTransform)`，取 `UIAlliancesMemberListGrade` 组件存为 `m_stickyGroup`，设置 RectTransform 顶部锚定（顶对齐 viewport 顶，x/宽度对齐列表项），`SetAsLastSibling`，初始 `SetActive(false)`。
- `m_ListScrollView_member_list.ScrollRect.onValueChanged.AddListener(OnListScroll)`，置 `m_scrollHooked = true`。

### 滚动/刷新更新
- `private void OnListScroll(Vector2 _) => UpdateStickyHeader();`
- `UpdateStickyHeader()`：按上面的算法计算并 `m_stickyGroup.gameObject.SetActive(...)` + `m_stickyGroup.SetData(groupInfo, this)`。
- 在 `RefushList()` 末尾调用一次 `UpdateStickyHeader()`（展开/折叠、数据刷新后同步）。
- 搜索态（`OnBtnButton_searchClick` / `FreshDatasSearch`）数据无 Group，算法自然隐藏悬浮层。

### 清理
- `OnHidden()`：`m_stickyGroup?.gameObject.SetActive(false)`。
- `OnDestroyed()`：移除 `onValueChanged` 监听、`Destroy(m_stickyGroup.gameObject)`。

## 复用说明
`UIAlliancesMemberListGrade.SetData(info, this)` 会把 `m_parent` 设为本界面，点击吸顶头会调用 `SwitchGroupShow(grade)`（与列表内头一致，点击可折叠当前阶级），`m_GoImage_me` 等显示逻辑也照常工作，无需改动该脚本。若希望吸顶头不可点击，再单独处理（默认保留点击折叠）。

## 备注 / 待实现时验证
- `Offset` 正负方向、`GetShownItemByIndex(0)` 是否为顶部项，按 `ArrangeType`（本列表为竖向）在实现时打印验证一次即可。
- 悬浮头的 RectTransform 锚点/宽度需与列表项一致，确保左右与列表对齐、顶部贴合 viewport 顶。