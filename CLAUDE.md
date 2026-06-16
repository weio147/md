# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

Unity 手游项目（Unity 2022.3.62f2c1），经营策略类网游，支持联盟、跨服、PvP 等玩法。基于 TFW (Tap4Fun) 框架，使用 HybridCLR 热修复。

## 语言

永远使用中文回复。所有对话、代码注释、commit 信息都使用中文。

## 构建与测试

- 通过 Unity Editor 构建和运行
- 测试：Unity Test Runner（Edit Mode / Play Mode）
- 提交前确认无编译错误

## 架构

### 分层结构

```
UI 层 (UIXxx.cs, UIPopupXxx.cs)
    ↓
逻辑层 (LXxxMgr.cs - 单例管理器，通过 .I 访问)
    ↓
配置/数据层 (Cfg.xxx, cspb protobuf)
    ↓
网络层 (TFW 框架)
```

### 关键目录

- `Assets/P2/GameScript/GameLogic/` — 业务逻辑（70+ 模块，每模块一个 LXxxMgr 单例）
- `Assets/P2/GameScript/GameScriptMain/D23Code/UI/` — D23 期 UI（当前主要开发区域）
- `Assets/P2/GameScript/GameScriptMain/UI/` — 早期 UI
- `Assets/P2/BasicScript/` — 基础系统（音频、网络、登录、输入）
- `Assets/X11/` — X11 新社交系统

### 核心 API 与模式

- 对象池：`TFW.Utility.ListPool<T>.Get()` / `.Release(list)`，`DictionaryPool<T, U>` 同理
- 本地化：`LocalizationMgr.Get("LC_KEY")`
- 窗口管理：`WndMgr.Show<UIXxx>(data)`
- 事件系统：`RegisterEvent(TEventType.Xxx, handler)` 随 UI 销毁自动解绑
- 循环列表：`TFWLoopListView`，吸顶用悬浮覆盖层实现（不改 prefab）
- 内城聚焦建筑：`GameDerived.instance.camAgent.MoveToBuildingWithGuideArrow` 或 `SetViewMode`
- 跳转大世界：`Switch2WorldUtil.Jump2WorldPosition`
- 浮动提示：`FloatTips.I.FloatMsg(text)`

### 联盟系统（当前开发重点）

- 逻辑：`Assets/P2/GameScript/GameLogic/Alliance/LAllianceMgr.cs`
- X11 UI：`Assets/P2/GameScript/GameScriptMain/D23Code/UI/AllianceX11/`
- 权限检查：`LAllianceMgr.I.HavePermission(UnionAuthority.Xxx)`
- X11 按钮灰态：`GetComponent<IX11UIBtnBlueOnlyText>()?.SetInteractable(hasPermission, true)`
- 无权限提示：`FloatTips.I.FloatMsg(LocalizationMgr.Get("LC_UNION_no_jurisdiction"))`
- 二次确认弹窗：`UIMsgBox.Push(MsgBoxType.TwoButtonWithoutClose, title, content, btn1, btn2)`

## 开发规范

- 读取配置数组前判空（`Count > 0`），不依赖 `try/catch`
- 校验逻辑集中复用（如 `LAllianceMgr.CheckTextLegal`）
- 申请与加入走同一接口 `JoinUnionReq`，UI 按 `NeedApply` 区分
- 回收项默认恢复显示，遮挡显隐由列表在滚动回调中统一控制
- 配置值类型注意区分：名称/简称花费为 `long`，旗帜为 `int`
