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
- 已完成本地 OCR、选择性 Qwen 复核及所需范围的对话 Agent 看图核对；正式导出为已确认子集，仍有 10 张局部未决，未决部分不翻译。
- 98 条确认子集现已完成 API 翻译和全量独立语义审校，正式导出 `avadon-the-black-fortress_images_text_translated.csv`，SHA-256 `18f9549844c36e9a67b0445d2a78ffcf0f1a22a4007646c2d82009a0864fff74`。未知区域仍不算已翻译。

## 技术栈
| 环节 | 工具 | 版本 / 状态 |
|------|------|------|
| 初始化 | start-translate / Python / Git | 2026-10-26 / 3.12.10 / 2.55.0.windows.5 |
| 常规提取 | game-unpack / Python / REA + Ghidra | 3.12.10 / 6.4.0 + 12.1.4；已导出 15,928 条 |
| 图片提取 | game-image-extract / RapidOCR / ORT GPU / Qwen3-VL | v0.5 / 3.10.0 / 1.31.0 / 8B Instruct Q4_K_M；98 条确认子集 |
| 翻译 | game-translate / translation_workflow.py | API；按原优先级；正文 15,928 条、图片 98 条正式验收导出 |
| 图片合入 | game-image-repack / Pillow / Noto Sans SC | build-v4；19 张纹理，94 处修改、39 处保留 |
| 回填 | REA + Ghidra / MSVC x86 / MinHook | 6.4.0 + 12.1.4 / 14.51.36231 / v1.3.4；已安装，实机待用户验证 |
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
- 独立图片翻译工作区：`TranslateFiles/image-text/`；已完成正式翻译，未重置常规文本状态。

## 翻译
- 执行路线：用户已选择 API，必须由程序遵守本机已有接口优先级和故障转移配置，默认不得传 `--api` 固定接口。先前 Agent 在代理接口失败后擅自固定官方 DeepSeek，此行为未经用户授权，已于用户指出后停止。凭据不进入项目。
- 进度：337 个有效提取批次覆盖 15,928 条原文；152 个术语审校批次全部完成，冻结 287 个角色 / 881 个术语 / 48 项禁翻。冻结文件 `TranslateFiles/glossary/r3/freeze_9ac86720/built/glossary_reviewed.json`，SHA-256 `831317812e8e871f1e0ec360c9ca6534425d4a1f258bb0d4bfc11f375f7b0f5b`。
- 试译：固定随机 150 条、4 个 API 批次已完成，机械失败 0；主 Agent 已阅读全部原译对照，接受总体流程和文风，意见见 `TranslateFiles/reports/pilot_assessment.json`。接受是全文校准，不表示逐句零错，正文仍需全量独立审校。
- 正文：376 个 API 批次已保存全部 15,928 条草稿。首次全量检查后修复了普通格式/术语问题；对 18 条说明书标题的反复失败定位为项目排除正则错误，而非译文丢失 `$`。
- 正式导出：全部 15,928 条完成独立六维语义审校，首轮及常规修复合计 1,079 个审校批次；2 项明确遗留疑点经新 Sol 实例裁决（1 项语境认可 / 1 项通过），最终闭环批准后由程序 export 通过结构、术语及审校覆盖门槛。正式译文 `avadon-the-black-fortress_text_translated.csv`，SHA-256 `8eacdf92ed763cb581209315c61c7db8168548004b04704a8d4f3f76868270a8`；源文 SHA-256 `f3c99d2b389528373bc9dbc8f55a13bf132e5f167b0dad86ae34e35e231bb991`。未额外全文润色，实机验证为 pending_repack。
- 图片子工程：98 条已独立完成术语、试译、翻译和全量语义审校；状态位于 `TranslateFiles/image-text/TranslateFiles/`。19 项技术字形、教程字母/数字、资源与品牌字串精确保留；35 个相关已审专名作为背景参考。正式验收见其 `reports/final_validation.json`。
- 用户授权补充：随后明确允许必要时输入上限提高至 131,072；当前实际包可在 65,536 内完成，未因此提高上限，也不改变接口优先级。
- 保护规则修复：`[_|]|\$(?=[A-Za-z])` 改为 `[_|$]`。公共修复入口逐条证明 15,928 条源文的保护族、匹配字串和位置完全不变，并对 18 条已有候选运行完整检查；通过后仅作废尚未执行的错误修复任务，保留所有候选、身份和累计尝试。全库复查 `full_draft_scan.json` 为 15,928 / 15,928、失败 0。随后已完成独立语义审校和正式导出，程序检查本身未代替语义审校。
- 恢复：失败范围依次拆至 128 / 32 / 12 条，保留成功结果和历史尝试；经诊断将尝试上限从 3 增至 5。最后 18 个提取批次全部通过。恢复范围及原因见 `TranslateFiles/reports/extract*20261026.json`。
- 规则：保护 `_`、`|`、文档标题 `$` 及原有格式变量；`$` 后标题正文需要翻译。原生拼接片段保留有意义空白，不自行补齐成句。上下文由提取映射逐条提供，不以 CSV 邻接推断剧情。
- 审校输入：此前将未发送的内部 canonical 包计入 API 预算，导致高频 Avadon 约 9.5 万 Token 的误判；实际 API 包约 5.4 万 Token。已修正为按实际完整发送包计数，内部计数保留审计；原上限 65,536 不变，无候选或出处截断。通过公共恢复接口与原位降低上限保留修订号、所有任务和尝试历史。
- 恢复说明：用户已澄清继续翻译，禁止的是绕过优先级，而非停止全部翻译。后续命令不带 `--api`，程序按原 `yjapi → vortex → acy7 → deepseek` 优先级及故障转移规则运行；不擅自修改选路、重试或 Token 预算。
- 协议恢复：一份真实 API 审校回复仅省略外层 decisions，程序按完整原始字段恢复包装并通过相同引用及语义证据校验，无新增模型请求。另一个缺少术语等级的提案由 API 在剩余原预算内重新审校。
- 同形多义：Corruption 的地名/状态和 Charm 的状态/道具由真实审校分别给出译名和范围。仅当 whole_record 与带可见前后缀的 literal_context、或两组 literal_context 可机械证明互不重叠时允许同源词并存；重叠/无范围/跨表冲突仍拒绝。已做针对性回归，未由程序代填语义通过。
- 用户负责游戏实测；本流程只做静态验证，完成回填后交付测试清单，发布前停止。
- 正式译文：`avadon-the-black-fortress_text_translated.csv`，与源文逐条对应。
- 图片源文 / 译文：`avadon-the-black-fortress_images_text.csv` / `avadon-the-black-fortress_images_text_translated.csv`，来源及坐标独立保存为 mapping。
- 术语、占位符规则、语义审校和校验报告保存在 `TranslateFiles/`；缓存、备份和凭据不入库。

## 回填
- 状态：2026-10-26 已安装本地待测版本。22 个载荷文件全部逐字节哈希核验；11 个原资源文件先备份后覆盖，另新增 11 个文件。记录为 `Repack/INSTALLATION.json` / `INSTALL_VERIFICATION.json`，原件备份位于忽略的 `Repack/Backups/20261026T062100012657Z/`。
- 正文方案：新增 x86 `winmm.dll` 转发 DLL，通过游戏既有 timeGetTime 导入初始化离线显示适配。转发本机系统 winmm 的全部 193 个导出，系统 DLL 不复制、不修改。MinHook v1.3.4 固定提交 `c3fcafdc10146beb5919319d0683e44e3c30d537` 静态链接，保留 BSD 许可；构建脚本为 `Repack/build_patch.py`。
- 版本绑定：仅支持当前 EXE SHA-256 `d3d897e0b0608aad52f22e09d9b2174653b5903e6de9b1cc8e396ebc3c72d44e`。运行时再次检查完整 EXE 哈希和两个入口原字节；其他版本、词典缺失或 `AvadonChinese/disabled.flag` 存在时仅转发系统函数。
- 显示路径：REA + Ghidra 证明 `0x46e080` 在原生换行、单字节清洗前接收完整原文，ECX 为对齐、栈上 7 个参数；`0x46df00` 为 EDX 输入的宽度查询。使用 MinHook 的线程协调与 trampoline，同时替换绘制和测宽。全部 15,928 条原文小于原生 512 字节输入限制。
- 词典：正式译文编译为 `AvadonChinese/translations.bin`，21,808 个键；原文精确匹配优先，另有已证明的引号解码、标题标记和旧显示清洗变体。87 个格式模板仅匹配已支持的参数类型；未知文本回退原渲染，并最多记录 1,000 条唯一原文供后续补漏。所有正式 CSV 保持不变。
- 字体与排版：系统 Microsoft YaHei，GDI 灰阶字形生成 OpenGL 纹理；支持中文换行、原生颜色/透明度、裁剪、`|` 换行和 `[N]` 姓名展开。采用完整段落布局，未使用逐词替换；不改脚本、DAT 固定槽或游戏内部标识。
- 图片适配：`0x471290` 按 BMP → PNG → JPG 探测。原 JPG 的中文候选以同名 PNG 优先加载，保留原 JPG；G169 仍为真实 BMP。引擎纯白色键会清除 RGB 255,255,255，最终中文字使用 245,240,220，透明资产保留 alpha。
- 离线验证：`Repack/verify_patch.py` 核验正式源文/译文、词典全部标准键、贴图及载荷，并运行自建 `self_test.exe`。检查 193 个导出、3,126 个字符、x86 栈/寄存器、未知原文回退、GL 状态恢复、中文换行/裁剪及姓名占位符。测试只运行自建组件与合成函数，不启动 Avadon、不执行游戏测试。证据见 `Repack/STATIC_VALIDATION.json` 和 `NativeTests/report.json`。
- 安装核验：原 EXE、279 个脚本、DAT 共 281 个提取源文件哈希全部不变；G290 原字形图集不变；全部备份与安装文件哈希一致。原始 JPG 也全部保留。
- 实机状态：**未启动游戏、未实机通过**；字体视觉效果、选项热区、任务推进、动态拼接、保存/载入及显卡兼容性由用户测试。详见 `Repack/测试清单.md`；两份 `USER_GAME_CHECK_*.pending.json` 保持 pending，未调用 record-game-check 冒记通过。未生成发布包。

## 图片文字合入
- 当前候选：`ImagePatch/build-v4/IMAGE_PATCH_MANIFEST.json`，19 张同尺寸 RGBA PNG、94 处中文绘制区域；39 处明确保留原文的技术字形 / 数字 / 教程字母 / 品牌维持原像素，G290 位图字形图集不重绘。
- 字体：工作区 `Tools/Fonts/NotoSC/NotoSansSC-variable.ttf`，请求字重 400；字形覆盖检查通过，字体哈希记入清单。未复制字体文件到游戏。
- 透明资产：清除原文字像素后在透明背景绘制中文，保留原矩形外像素；其余不透明区域使用灰色蒙版覆盖英文。v1 / v2 / v3 均已弃用，不安装；v4 改用暖白以避开引擎纯白透明色键。
- 静态检查：已查看 19 张联系表及透明菜单全图；同尺寸、矩形外像素不变检查全部通过，最终中文字字号均不低于 10 像素。两处 G176 微小地图标签扩展绘制区域，已看原图确认间距；派生映射与理由在 `ImagePatch/layout-input/layout_review.json`，原始提取 mapping 保持不变。
- 图片换行：8 处地图标题按源哈希绑定为单行逻辑译文，由合入工具在矩形内重新排版；教程原换行保留。未以改源文或删语义检查绕过翻译验收。
- 状态：图片工具清单仍为 `ready_for_engine_adapter`、`installed=false`，表示其自身阶段边界；后续引擎适配已实际完成并安装，权威安装记录在 `Repack/INSTALLATION.json`。用户游戏实测待进行。

## 已知问题
- 图片原文为确认子集：10 张局部残字、遮挡、字形或特殊药瓶标签未决；细项与来源见 ImageText/report.json，不能标成全图无漏字。
- 已实现独立中文绘制和测宽，绕过 G290 拉丁字形限制；尚待实际显卡和游戏场景验证，不承诺全部 UI 无截断。中文输入法和自定义中文姓名支持未验证。
- 已建立脚本、DAT 与 EXE 的首版静态语料；尚未完成实机覆盖核对。原生片段依赖拼接和空白，不能逐词随意替换；中文超出原槽容量时须重定位或显示层适配。
- 项目 `Game/` 为安装目录的 junction；后续对其写入将影响实际游戏，回填前须备份。

## 对外发布
- 补丁文件 / 支持版本 / 载荷 / 验证结果：待完成回填和验证后记录。
- 发布目录：`Dispatch/`；当前无发布补丁。

## 版本记录
- 2026-10-26：初始化独立汉化仓库及 Game 目录联接；启用图片文字汉化；补充官方资料、本地资源线索和 Steam 构建标识。
- 2026-10-26：完成常规文本静态提取首版（15,928 条）；保存来源映射、校验报告和 REA Ghidra 证据，导出图片快照并启动本地图片文字流程。
- 2026-10-26：完成图片全量 GPU OCR、305 张本地 Qwen 复核和 275 张视觉核对；导出 98 条 / 133 处确认子集，记录 10 张未决。
- 2026-10-26：完成正文 15,928 条与图片 98 条正式 API 翻译及独立审校；按原接口优先级执行，输出正式 CSV。
- 2026-10-26：完成 REA 渲染路径分析、x86 离线显示适配、build-v4 图片和组件静态检查；备份并安装 22 个文件，交用户实测，发布前停止。
