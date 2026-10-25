# Avadon: The Black Fortress 汉化项目

## 游戏信息
- 原名：Avadon: The Black Fortress
- 中文名：阿瓦登：黑色要塞（项目暂译，非官方中文名）
- 开发商 / 发行商：Spiderweb Software
- 发行平台：本项目使用 Steam Windows 版；Steam App ID `112100`。
- Steam 发售日期：2011-08-17（其他平台首发日期不据此推定）。
- 原语言 / 商店支持语言：英语；Steam 语言表仅列英语界面。
- 本地版本标识：Steam Build ID `4252712`，Depot `112101`，Manifest `6035336520543477858`；来自本机 `appmanifest_112100.acf`，不等同于程序版本号。
- 引擎：32 位 x86 原生程序，采用自定义脚本与二进制场景结构；EXE 中有 PTK Game Library / OpenGL 线索，具体引擎名称及版本未确认。程序内版本字符串为 `v1.0s2, Copyright 2011-2, Spiderweb Software, All Rights Reserved`。
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
| 常规提取 | game-unpack / Python / REA + Ghidra | 3.12.10 / 6.4.0 + 12.1.4；已导出 15,928 条 |
| 图片提取 | game-image-extract | 已启用，待执行 |
| 翻译 | game-translate | SubAgent / API 路线尚未选择 |
| 图片合入 | game-image-repack | 待正式图片译文完成 |
| 回填 | game-repack；需逆向时使用 REA + Ghidra | 待分析 |
| 发布 | game-release-patch | 待回填验证通过 |

## 文本提取
- 状态：2026-10-26 完成首版静态提取，共 **15,928 条去重原文 / 18,379 个来源位置**。脚本 17,350 处、DAT 192 处、EXE 837 处；同文精确去重，全部来源保留。
- 正式原文：`avadon-the-black-fortress_text.csv`，UTF-8 BOM、无表头、单列标准 CSV；逗号、引号、换行按 CSV 规则处理，读取时使用 CSV 解析器。
- 来源映射：`avadon-the-black-fortress_text.mapping.json`；记录 CSV 行号、文件、字节偏移、编码、脚本上下文；原生文本另记 VA / RVA、容量和证据 ID。
- 可复现命令：工作区根目录执行 `python Projects/avadon-the-black-fortress/Extraction/extract_text.py`。脚本仅只读访问游戏；已有不同源文时拒绝覆盖。
- 脚本：遍历 279 个 TXT，按字符串 / 注释词法解析；提取对话、选项、文本库、技能 / 物品 / 地形名称及显示函数参数，排除注释、空槽和资源脚本名；保留源空格、转义、下划线与 `$` 等格式标记。
- 特殊项：`z12beastwddlg.txt` 的 `set_coloradj(132,"Ice Imp")` 是数值参数中的异常字符串，记入排除报告，不当作该调用的显示文本。
- DAT：REA + Ghidra 确认头部 `0x1168`、每区 `0x3d42c`、共 24 区；地图名在头部 `4 + zone*44`，容量 32 字节。每区两层、层跨度 `0x161f8`；每层 `0x16054` 起有 10 个 40 字节地图标注槽，`0x15604` 起有 10 个 256 字节消息槽（本版均为空）。严格按槽起点读取到首个 NUL，避免把残留旧字节误当文本。
- EXE：REA Ghidra 已定义字符串清单与已检查 UI 表字节联合提取；覆盖战斗提示、技能说明、库存 / 商店 / 训练 / 设置、键位标签、读写档错误等，排除调试输出、引擎诊断、文件路径、作弊指令键及第三方库字符串。补充了清单遗漏的 `Hard`、`On`、`Off`、`Fire` 等短标签。
- 工具：REA 6.4.0，Ghidra 12.1.4，固定 `ghidra` 后端；doctor 定向检查 healthy=true。直接分析安装目录真实路径，未向 REA 传入 junction 路径，未修改原始程序。
- 分析输入：`Avadon.exe` SHA-256 `d3d897e0b0608aad52f22e09d9b2174653b5903e6de9b1cc8e396ebc3c72d44e`，PE image base `0x400000`。
- 分析证据：`Analysis/ghidra-functions.json`、`Analysis/ghidra-strings.json`、`Analysis/*_table.json` 等；完整会话快照为忽略文件。DAT 加载函数 `0x4283f0 / 0x4284a0`，初始化函数 `0x4518f0 / 0x451d00 / 0x451f90`。
- 校验：全部映射源字节与原文件一致，CSV 单列往返校验通过。源文件大小和 SHA-256 存在 `Extraction/source_manifest.json`，排除项存在 `Extraction/excluded_strings.json`，统计与边界存在 `Extraction/report.json`。
- 图片交接：已复制导出 721 个原始图片文件，像素去重后 717 张；`ImageText/provenance.json` 记录游戏根目录相对路径和哈希，快照位于忽略的 `ImageText/exported/`、`ImageText/work/`。
- 覆盖边界：这是静态提取首版，不代表实机全覆盖。EXE 字符串未逐条追踪调用，回填须复核调用点、用途与容量；未定义 / 动态生成文本仍需后续实机覆盖检查。

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
- 已建立脚本、DAT 与 EXE 的首版静态语料；尚未完成实机覆盖核对。原生片段依赖拼接和空白，不能逐词随意替换；中文超出原槽容量时须重定位或显示层适配。
- 项目 `Game/` 为安装目录的 junction；后续对其写入将影响实际游戏，回填前须备份。

## 对外发布
- 补丁文件 / 支持版本 / 载荷 / 验证结果：待完成回填和验证后记录。
- 发布目录：`Dispatch/`；当前无发布补丁。

## 版本记录
- 2026-10-26：初始化独立汉化仓库及 Game 目录联接；启用图片文字汉化；补充官方资料、本地资源线索和 Steam 构建标识。
- 2026-10-26：完成常规文本静态提取首版（15,928 条）；保存来源映射、校验报告和 REA Ghidra 证据，导出图片快照并启动本地图片文字流程。
