# 翻译操作记录

- 工作流：custom
- 执行路线（codex=SubAgent，api=API）：api
- 原文：项目根目录 `avadon-the-black-fortress_text.csv`
- 正式译文：项目根目录 `avadon-the-black-fortress_text_translated.csv`
- 中间产物：`TranslateFiles/`

由 game-translate 技能调用共用流程程序；路线为 SubAgent（codex）或 API（api）。正文前完成全文术语整理及冻结。
试译：固定随机样本 → pilot_translate → pilot-report → 主 AI pilot-decide；按需 pilot-retry。
试译用于校准流程和风格，不要求逐句零错误；正式译文仍须完整独立审校和导出验收。

- 本次正文 15,928 条已完成正式 API 翻译与独立语义审校，程序最终导出通过。98 条图片文字在独立子工程执行同样流程并正式收回。
- API 必须遵守本机原优先级 `yjapi → vortex → acy7 → deepseek` 及既有故障转移规则；未获明确指定不得使用 `--api` 固定官方或其他接口，存在密钥不构成固定选路授权。恢复与阶段切换同样遵守，不擅自扩大费用边界。
- 用户明确允许必要时输入上限提高至 131,072；修正实际发送包预算后，本次仍以 65,536 完成，无需使用增加额度。
- 正文正式译文 SHA-256：`bf8cb69da9e6f327b9f8a8c9c4e75dcc0168fbf9cdb052241d97f50749a7f6b7`。
- 图片正式译文 SHA-256：`18f9549844c36e9a67b0445d2a78ffcf0f1a22a4007646c2d82009a0864fff74`。
- 已备份安装本地待测载荷；实机验收仍为 pending，由用户测试。未发布、未把离线组件检查当成实机通过。
- 用户发现 retrain 中英混杂后，新增独立 Sol 单 ref 作用域审校：独立原生命令保留，普通句不再全局禁翻。公开 revise-glossary 生成 revision 4；原有无关语义证据和累计尝试保持不变。8 条受影响记录经过 API 定向复审，5 条旧语境例外由程序重新处理，实际仅修改 CSV 1144、1587 两句；其他 15,926 条译文不变。正式程序重新导出通过，载荷已更新安装，仍待用户实测。
