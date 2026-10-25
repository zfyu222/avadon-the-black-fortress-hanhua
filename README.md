# Avadon: The Black Fortress 汉化项目

## 游戏信息
- 原名：Avadon: The Black Fortress
- 中文名：阿瓦登：黑色要塞（项目暂译，非官方中文名）
- 开发商 / 发行商：Spiderweb Software
- 发行平台：本项目使用 Steam Windows 版；Steam App ID `112100`。
- Steam 发售日期：2011-08-17（其他平台首发日期不据此推定）。
- 原语言 / 商店支持语言：英语；Steam 语言表仅列英语界面。
- 本地版本标识：Steam Build ID `4252712`，Depot `112101`，Manifest `6035336520543477858`；来自本机 `appmanifest_112100.acf`，不等同于程序版本号。
- 引擎：具体名称及版本尚未确认。目录包含 `Avadon.exe`、`steam_api.dll` 和 `Avadon Files/`，未见 Unity / RPG Maker 的常见目录标志。
- 本地游戏目录：`D:\Program Files (x86)\Steam\steamapps\common\Avadon The Black Fortress`
- 资料来源：[Steam 商店](https://store.steampowered.com/app/112100/)、[开发商官网](https://www.spiderwebsoftware.com/avadon/)。

## 游戏简介
玩家为黑色要塞 Avadon 效力，以战士与密探的身份调查威胁故土的阴谋。这是一部奇幻角色扮演游戏，提供四种职业、支线探索及受玩家选择影响的多种结局。简介据[开发商官方介绍](https://www.spiderwebsoftware.com/avadon/)转述。

## 汉化目标
- 范围：以常规可见文本和图片文字的简体中文汉化为目标；实际覆盖范围在提取与验证后记录。
- 目标语言：简体中文。
- 图片文字翻译：启用（用户于 2026-10-26 明确选择）。
- 初始化阶段未修改游戏安装文件。

## 图片文字流程
- 选择记录：`localization_project.json`，状态为 `enabled`。
- 顺序：常规解包 → `game-image-extract` → 正式翻译 → `game-image-repack` → 引擎回填。
- 常规与图片源文、译文独立保存；图片翻译中间产物放 `TranslateFiles/image-text/`。
- 图片候选、模型识别结果须经规定的视觉审核后才能作为正式源文；尚未执行图片扫描、OCR 或翻译。

## 技术栈
| 环节 | 工具 | 版本 / 状态 |
|------|------|------|
| 初始化 | start-translate / Python / Git | 2026-10-26 / 3.12.10 / 2.55.0.windows.5 |
| 常规提取 | game-unpack | 待执行 |
| 图片提取 | game-image-extract | 已启用，待执行 |
| 翻译 | game-translate | SubAgent / API 路线尚未选择 |
| 图片合入 | game-image-repack | 待正式图片译文完成 |
| 回填 | game-repack；需逆向时使用 REA + Ghidra | 待分析 |
| 发布 | game-release-patch | 待回填验证通过 |

## 文本提取
- 初始化目录检查：`Avadon Files/Scripts/` 存在文本脚本；`codex.txt` 中可见 `beginobjectscript`、`beginstate` 等语法，不能把全部字符串或全部行直接当作待译内容。
- 资源线索：`Avadon Files/AvScenData.dat`（6,026,632 字节）及 `Graphics A/`、`Graphics B/`、`Graphics Core/`。
- `Avadon Files/` 文件扩展名统计：279 个 TXT、633 个 PNG、46 个 BMP、42 个 JPG、195 个 OGG、1 个 DAT。图片数量不代表含字图片数量。
- 需要区分脚本中的显示文本、标识符、注释及控制语法，并检查场景数据与程序内的遗漏文本。
- 正式输出：项目根目录 `avadon-the-black-fortress_text.csv`，单列逐条文本；当前尚未提取。
- 需分析原生程序或字体/编码函数时，先阅读 `.agents/skills/game-unpack/references/rea_ghidra.md`，使用 REA + Ghidra，证据放项目 `Analysis/`。

## 翻译
- 执行路线：尚未选择，首次进入翻译阶段时确认 SubAgent 或 API。
- 正式译文：`avadon-the-black-fortress_text_translated.csv`，与源文逐条对应。
- 图片源文 / 译文：`avadon-the-black-fortress_images_text.csv` / `avadon-the-black-fortress_images_text_translated.csv`，来源及坐标独立保存为 mapping。
- 术语、占位符规则、语义审校、校验结果：待翻译阶段补充；中间文件统一放 `TranslateFiles/`，缓存、备份和凭据不入库。

## 回填
- 方案：待文本格式、编码及字体支持分析后确定。
- 验证：需覆盖中文字体显示、脚本加载、对话 / 任务界面、图片替换与存档兼容性。
- 尚未安装补丁或进行汉化实机验证。

## 已知问题
- 尚未确认中文编码、字体覆盖与排版限制。
- 尚未确认脚本、DAT 与 EXE 各自包含的可见文本范围。
- 项目 `Game/` 为安装目录的 junction；后续对其写入将影响实际游戏，回填前须备份。

## 对外发布
- 补丁文件 / 支持版本 / 载荷 / 验证结果：待完成回填和验证后记录。
- 发布目录：`Dispatch/`；当前无发布补丁。

## 版本记录
- 2026-10-26：初始化独立汉化仓库及 Game 目录联接；启用图片文字汉化；补充官方资料、本地资源线索和 Steam 构建标识。
