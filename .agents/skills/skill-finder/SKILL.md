---
name: skill-finder
description: 找 skill 的 skill。当用户说"有没有干X的skill/帮我找个skill/还有哪些skill能用/怎么装skill"时，在本地已下载的 skill 目录里检索匹配，给出用途+来源+安装方法。
---

# 找 skill 的 skill (skill-finder)

帮卡夏在"已下载的 skill 库"里找到能用的，并给安装方法。**不要凭空编 skill 名**，只报库里真实存在的。

## 本地已下的 skill 库（检索这些）

| 库 | 路径 | 内容 |
|---|---|---|
| 官方 skills | `_refs/anthropics-skills/` | 17个真 skill：docx/pdf/pptx/xlsx/canvas-design/algorithmic-art/mcp-builder/skill-creator/frontend-design/webapp-testing/theme-factory/web-artifacts-builder… |
| 视频 skills | `_refs/jianshuo-Codex-skills/` | 王建硕全套：剪辑/字幕/配音/横转竖/切片/封面/发布… |
| Awesome 索引 | `_refs/awesome-Codex-skills/README.md` | 全网 skill 精选目录（带链接，按分类） |
| Awesome 索引2 | `_refs/awesome-agent-skills/` | 1000+ agent skill 目录（跨 Codex/Codex/Cursor） |

## 检索流程（Codex 执行）
1. 把用户需求转成关键词（中英都试），`Grep` 上面四个库的 SKILL.md / README。
2. 命中后报：**skill 名 + 一句用途 + 在哪个库 + 怎么用**。
3. 库里没有就**老实说没有**，再去 awesome 索引的链接里找在线的，给 GitHub 地址。

## 安装方法（告诉用户三选一）
- **官方/marketplace**：在交互式 `Codex` 终端跑 `/plugin marketplace add anthropics/skills`，再 `/plugin install <名>`
- **本地目录**：把某个 skill 文件夹复制进本项目 `.Codex/skills/<名>/`（含 SKILL.md），重启 CCD 生效
- **从 _refs 采用**：`_refs` 里的是参考；要正式用就复制进 `.Codex/skills/`（像我们移植 reframe 那样，注意 mac/bash → Windows/PowerShell 适配）

## 注意
- `_refs/` 是只读参考区，**不直接当生效 skill**；生效的在 `.Codex/skills/`。
- mac/bash 写的 skill（jianshuo 那套）在本机要改：路径、字体、`.sh`→`.ps1`、编码。
- 必剪/剪映这类 GUI App **没有 skill 可装**（无 API），只能手动精修或喂标记给它。
