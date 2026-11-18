# Avadon: The Black Fortress 简体中文汉化

《阿瓦登：黑色要塞》是 Spiderweb Software 开发的奇幻队伍角色扮演游戏。本项目面向 Steam Windows 版 Build 4252712 / Avadon v1.0s2（x86），覆盖正文、菜单、游戏提示及部分地图和界面贴图。[Steam 商店](https://store.steampowered.com/app/112100/)

## 当前版本

- **汉化 v1.6** 补齐 26 个百科主题的首次收录和重复阅读提示，以及治疗之触、野蛮打击和缴械打击的目标选择提示。安装载荷含汉化插件、词典和 19 张中文贴图。
- **体验优化 v2.3** 依赖匹配版本的子非鱼汉化。支持字体缩放、镜头跟随、队伍探索加速、背包快捷键切换和可交互物标记，设置窗口支持简体中文与英文。

[GitHub 最新发布](https://github.com/zfyu222/avadon-the-black-fortress-hanhua/releases/latest) · [问题反馈](https://docs.qq.com/sheet/DTkNXdm54YVFOSmJ0?tab=BB08J2)

## 源码与数据

| 路径 | 用途 |
| --- | --- |
| `Game/` | 本机 Steam 游戏目录链接，构建时读取原版文件 |
| [Extraction/](Extraction/) | 游戏脚本、DAT 和 EXE 的文本提取。根目录的 `*_text.csv`、`*_text_translated.csv` 和 `*.mapping.json` 保存源文、译文和来源映射 |
| [TranslateFiles/](TranslateFiles/) | 术语、翻译与校验配置。图片文字使用独立子工程，正式 CSV 存在根目录 |
| [ImagePatch/](ImagePatch/) | 图片回填。当前发布基线为 `build-v9`，使用同尺寸 PNG 替换游戏贴图 |
| [Repack/native/](Repack/native/) | x86 `winmm.dll` 转发及 MinHook 钩子，通过 GDI / OpenGL 绘制中文并测宽。体验优化设置界面位于 [EnhancementSettings.cs](Repack/EnhancementSettings.cs) |
| [Release/](Release/) · [Dispatch/](Dispatch/) | 发布脚本、安装配置、载荷清单和验证报告 |

## 构建与验证

在 StaticHanHua 工作区内，从本项目目录执行。原生构建使用 Python 3.12、MSVC x86 和 MinHook v1.3.4，设置界面使用 Windows .NET Framework / WinForms。

| 目标 | 入口 |
| --- | --- |
| 提取正文 | `python Extraction/extract_text.py` |
| 构建汉化载荷并离线验证 | `python Repack/build_patch.py`，然后运行 `python Repack/verify_patch.py` |
| 构建体验优化载荷 | `python Repack/build_patch.py --enhancement` |
| 打包体验优化 | 先运行 `Repack/Enhancement/Build/self_test.exe`，依次传入该构建的 `Payload/AvadonChinese/translations.bin`、`Build/required_glyphs.bin`、`Payload/winmm.dll` 和 `Tests` 目录的绝对路径，再执行 `python Repack/package_enhancement.py` |
| 打包汉化 v1.6 | `python Release/build_release_v1_6.py`。该入口在 v1.5 ZIP 的载荷上更新词典，需要 v1.5 发布包及当前本地翻译工作流数据 |

维护词典时保留 `_`、`|`、文档标题控制符 `$` 及格式变量。动态拼接文本按已确认的结构匹配。未知词典键会回退到游戏原文。发布包只包含修改资源和补丁组件，原游戏文件留在本机。
