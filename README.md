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
- 已完成本地 OCR、选择性 Qwen 复核及所需范围的对话 Agent 看图核对；正式导出为已确认子集，仍有 10 张局部未决，尚未翻译。

## 技术栈
| 环节 | 工具 | 版本 / 状态 |
|------|------|------|
| 初始化 | start-translate / Python / Git | 2026-10-26 / 3.12.10 / 2.55.0.windows.5 |
| 常规提取 | game-unpack / Python / REA + Ghidra | 3.12.10 / 6.4.0 + 12.1.4；已导出 15,928 条 |
| 图片提取 | game-image-extract / RapidOCR / ORT GPU / Qwen3-VL | v0.5 / 3.10.0 / 1.31.0 / 8B Instruct Q4_K_M；98 条确认子集 |
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

## 图片文字提取
- 2026-10-26 导出原始贴图 721 个，像素精确去重后 717 张；来源与哈希见 `ImageText/provenance.json`，原图和工作快照不入库。
- 校准：实际查看 40 张初始样本、其余 Core 图集联系表及关键全尺寸原图；新字体族仍保持 unknown，未用高分自动放行。策略 / 依据见 `ImageText/policy.json` 和 `ImageText/calibration_notes.json`。
- L1：全量 717 张 GPU PP-OCRv6 medium，扫描 226.016 秒（含初始化总计 235.912 秒），12,205 个疑似框，错误 0。大量精灵与地形形状误报，框数不是有效文字数。`ImageText/gpu_report.json` 记录真实 CUDA 内核证据；没有静默退回 CPU。
- L2：分流 305 张，含 20 张未检出 / 10 张低信号抽查；本地 Qwen 真实请求 305 次、推理累计 428.236 秒，22 个 text / 283 个 no_text 建议，付费 API 请求 0。OCR 子进程退出后才加载 Qwen；模型信息、GPU 驻留与报告摘要见 `ImageText/report.json`，原始回复和缓存保留在忽略的 work 目录。
- L3：当前对话 Agent 实际查看 275 张绑定图像 / 清晰联系表，关键小字另看全图及放大；导入 22 张有字确认、252 张无字确认、1 张未决。已确认有字图中另有 9 张存在局部残字，共 10 张未决。
- 正式输出：`avadon-the-black-fortress_images_text.csv`，**98 条去重原文 / 133 个位置**；独立坐标与来源为 `avadon-the-black-fortress_images_text.mapping.json`。
- 导出明确使用 `--allow-partial`：只收已看清的区域，不补写被遮挡或截断的字。当前范围是 confirmed subset，不是全图转写完成。10 张未决来源 / 原因详列 `ImageText/report.json`。
- 412 张筛选排除及 30 张模型 no_text 抽查未当作 Agent 确认无字；不宣称全游戏无漏字。Core G201 的单字母徽记已在校准记录为保留美术，不默认翻译。
- `ImageText/visual_decisions.json`、`ImageText/visual_reviews/` 记录实际 Agent 裁决；并非用户人工确认，`human_approval=false`。
- 翻译交接：`ImageText/translation_notes.md`、`ImageText/preserve_rows.json`；数字、教程字母、字体字形表、资源标记等需正式纳入后续保护规则。图集 G290 是拉丁位图字形资源，中文字体适配须另查渲染逻辑。
- 独立图片翻译工作区：`TranslateFiles/image-text/`；仅准备源文快照 / 图片上下文，不启动正文翻译。

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
- 图片原文为确认子集：10 张局部残字、遮挡、字形或特殊药瓶标签未决；细项与来源见 ImageText/report.json，不能标成全图无漏字。
- 尚未确认中文编码及排版限制；已发现 G290 拉丁位图字形图集，不能默认替换字体文件即可支持中文。
- 已建立脚本、DAT 与 EXE 的首版静态语料；尚未完成实机覆盖核对。原生片段依赖拼接和空白，不能逐词随意替换；中文超出原槽容量时须重定位或显示层适配。
- 项目 `Game/` 为安装目录的 junction；后续对其写入将影响实际游戏，回填前须备份。

## 对外发布
- 补丁文件 / 支持版本 / 载荷 / 验证结果：待完成回填和验证后记录。
- 发布目录：`Dispatch/`；当前无发布补丁。

## 版本记录
- 2026-10-26：初始化独立汉化仓库及 Game 目录联接；启用图片文字汉化；补充官方资料、本地资源线索和 Steam 构建标识。
- 2026-10-26：完成常规文本静态提取首版（15,928 条）；保存来源映射、校验报告和 REA Ghidra 证据，导出图片快照并启动本地图片文字流程。
- 2026-10-26：完成图片全量 GPU OCR、305 张本地 Qwen 复核和 275 张视觉核对；导出 98 条 / 133 处确认子集，记录 10 张未决。
