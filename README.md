# ArkUI Visual Replica

面向 AI Agent 的 HarmonyOS NEXT 界面与动效复刻技能资源，指导 Agent 以截图、设计稿或本地 HTML 原型为参考，用 ArkUI / ArkTS 高保真复刻界面与动效，并通过截图对比和交互验证检查还原效果。

## 适用场景

| 任务 | 工作流 |
| --- | --- |
| 静态页面复刻 | 对齐参考视口、系统安全区和坐标，使用原生组件实现，再按区域比较截图。 |
| 简单自动动效 | 在静态复刻基础上核对指定帧、正常播放和离页清理。 |
| 精确交互动效 | 记录触发条件、阶段、时序和打断行为，按场景验证手势、共享元素、滚动联动、弹簧、3D 或粒子效果。 |

适合有明确视觉参考的任务。工作范围以选定页面、组件和交互为准。

## 获取与使用

使用 Git 下载技能资源，并保留目录结构。也可以在 GitHub 下载 ZIP，解压后将目录命名为 `arkui-visual-replica`。

```bash
git clone https://github.com/liuying-cell/ArkUI-Visual-Replica.git arkui-visual-replica
```

- **支持技能导入的 Agent**可按平台文档导入整个 `arkui-visual-replica` 目录，再按技能名称调用。以 Codex 为例，可在对话中输入 `$arkui-visual-replica`。
- **直接在对话中使用**时，可以把仓库放到 Agent 可访问的工作区，或在对话中提供 [`SKILL.md`](SKILL.md) 和任务所需的参考文档、脚本与素材。请 Agent 先阅读 `SKILL.md`，再按任务选用资源。

发起任务时，给出视觉参考、目标页面或组件，以及希望验证的细节。下面的提示词可以直接使用。

> 请按 `arkui-visual-replica/SKILL.md` 的流程，将 `design/profile.png` 复刻到现有鸿蒙项目的 `ProfilePage.ets`。只做静态页面，保留现有逻辑。构建后对比头像、标题和底部按钮的位置，并报告实际完成的验证。

交互动效任务还可以指定动作和验收点，例如「快速连点反向播放时，从当前帧继续，记录打断前后的关键帧」。

## 工具与示例

- **HTML 取样**使用支持全局 `WebSocket` 的 Node.js 22+ 和 Chromium 系浏览器。见[本地 HTML 采集指南](references/local-html-capture.md)。
- **截图对比和时序分析**使用 Python 和 Pillow。Windows 模拟器窗口录制还需要 `imageio-ffmpeg`。见[视觉验收](references/visual-qa.md)和[时序与性能测量](references/motion-measurement.md)。
- **HarmonyOS 构建与运行验证**使用本地 DevEco 工具链。运行时验证还需 HDC 和可用设备或模拟器。见[环境预检](references/preflight.md)。

从仓库根目录运行示例生成脚本，然后在 DevEco Studio 中打开生成的工程。选择一个新目录，最好使用实际的纯 ASCII 路径。

```powershell
python scripts/materialize_motion_lab.py scroll-and-burst D:/arkui-labs/scroll-and-burst
```

可选示例为 `intro`、`scroll-and-burst` 和 `navigation-and-gestures`。场景、对应的 HTML 参考和复刻契约见[示例索引](references/motion-examples.md)。

## 仓库结构

| 路径 | 内容 |
| --- | --- |
| [`SKILL.md`](SKILL.md) | Skill 入口、任务选择和交付要求 |
| [`references/`](references/) | 视觉与动效实现指南、验收和测量方法 |
| [`scripts/`](scripts/) | 浏览器采集、截图比较、时序分析和校验工具 |
| [`assets/`](assets/) | HTML 原型、ArkUI 模板和动效契约 |
| [`evals/cases.json`](evals/cases.json) | 触发、流程选择和无设备降级的行为评测用例 |

维护者可在仓库根目录用下列命令检查文件结构、文档链接、契约和脚本。校验需要 Node.js，以及 Python 的 Pillow 和 PyYAML。

```powershell
python -B scripts/validate_skill.py .
```
