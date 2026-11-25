# Avadon: The Black Fortress 简体中文汉化

《阿瓦登：黑色要塞》是 Spiderweb Software 开发的奇幻队伍角色扮演游戏。本项目面向 Steam Windows 版 Build 4252712 / Avadon v1.0s2（x86），覆盖正文、菜单、游戏提示及部分地图和界面贴图。[Steam 商店](https://store.steampowered.com/app/112100/)

## 当前版本

- **汉化 v1.7** 润色 2,777 条正文，改善对白、叙事与教程表达。安装载荷含汉化插件、词典和 19 张中文贴图。
- **体验优化 v2.4** 增加对汉化 v1.7 词典的兼容。支持字体缩放、镜头跟随、队伍探索加速、背包快捷键切换和可交互物标记，设置窗口支持简体中文与英文。

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

## 翻译

- 2026-11-25 对 15,928 条常规正文执行独立 API 润色，重点改善对白口吻、叙事衔接及教程表达。按当前 API 优先级执行，标准档疑难交由 GPT-6 Sol 定向处理。
- 逐条比对润色前的正式译文，2,777 条实际改动接受独立复审，13,151 条沿用原审校证据。正文使用第 4 版冻结术语，正式导出通过占位符、结构及术语校验。
- 润色版正式译文已导出并回填到 v1.7 词典。详见 [翻译操作记录](TranslateFiles/TranslateDoc.md) 与 [导出验证报告](TranslateFiles/reports/final_validation.json)。

## 构建与验证

在 StaticHanHua 工作区内，从本项目目录执行。原生构建使用 Python 3.12、MSVC x86 和 MinHook v1.3.4，设置界面使用 Windows .NET Framework / WinForms。

| 目标 | 入口 |
| --- | --- |
| 提取正文 | `python Extraction/extract_text.py` |
| 构建汉化载荷并离线验证 | `python Repack/build_patch.py`，然后运行 `python Repack/verify_patch.py` |
| 构建体验优化载荷 | `python Repack/build_patch.py --enhancement` |
| 打包体验优化 | 先运行 `Repack/Enhancement/Build/self_test.exe`，依次传入该构建的 `Payload/AvadonChinese/translations.bin`、`Build/required_glyphs.bin`、`Payload/winmm.dll` 和 `Tests` 目录的绝对路径，再执行 `python Repack/package_enhancement.py` |
| 打包汉化 v1.7 与体验优化 v2.4 | `python Release/build_release_v1_7.py`。该入口使用 v1.6 主包、v2.3 体验优化包和当前正式翻译工作流数据 |

维护词典时保留 `_`、`|`、文档标题控制符 `$` 及格式变量。动态拼接文本按已确认的结构匹配。未知词典键会回退到游戏原文。发布包只包含修改资源和补丁组件，原游戏文件留在本机。

## 对外发布

- Windows Steam Build 4252712 / Avadon v1.0s2 使用 `阿瓦登：黑色要塞_子非鱼汉化1.7.zip`。本版重新构建词典，沿用 v1.6 插件和贴图。可单独下载体验优化 v2.4，沿用 v2.3 的组件并更新词典兼容清单。[GitHub v1.7](https://github.com/zfyu222/avadon-the-black-fortress-hanhua/releases/tag/v1.7)
- 词典载入、字体字形和组件离线检查通过。隔离回放覆盖主包安装、重复安装、v1.6 升级、卸载和旧包恢复，以及 v2.4 安装、设置持久化和卸载。本机已同步新词典及兼容清单，保留已安装的增强组件和设置。实机检查仍待完成。[主包验证](Dispatch/RELEASE_VALIDATION.json) · [体验优化验证](Dispatch/ENHANCEMENT_V24_VALIDATION.json)
- 发布页复用现有封面 JPG。[封面](Dispatch/Artwork/title.jpg) · [官方素材来源](https://store.steampowered.com/app/112100/)
