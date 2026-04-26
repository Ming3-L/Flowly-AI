# Flowly AI - Cursor Skills Configuration

本目录包含项目专用的Cursor Agent Skills配置。

## 目录结构

```
.cursor/
├── rules/              # Cursor规则文件
│   └── README-Update-Rule.md
└── skills/            # 项目级Skill配置
    ├── agent-browser/
    ├── changelog-maintenance/
    ├── code-refactoring/
    ├── context7-docs/
    ├── docx-processing/
    ├── frontend-design/
    ├── gpt-researcher/
    ├── marketing-skills/
    ├── pdf-processing/
    ├── planning-with-files/
    ├── security-audit/
    ├── skill-creator/
    ├── software-architecture/
    ├── superpowers/
    │   └── skills/
    │       ├── brainstorming/
    │       ├── code-reviewer/
    │       ├── dispatching-parallel-agents/
    │       ├── executing-plans/
    │       ├── finishing-a-development-branch/
    │       ├── receiving-code-review/
    │       ├── subagent-driven-development/
    │       ├── using-git-worktrees/
    │       └── writing-plans/
    ├── systematic-debugging/
    ├── tavily-search/
    ├── tmux-terminal/
    ├── ui-ux-pro-max/
    ├── web-interface-guidelines/
    └── webapp-testing/
```

## Skills功能说明

### 开发流程类
| Skill | 功能 |
|-------|------|
| superpowers | 核心技能库，包含完整的开发工作流 |
| brainstorming | 创意头脑风暴，设计评审 |
| writing-plans | 创建详细的实施计划 |
| executing-plans | 执行实施计划 |
| subagent-driven-development | 子代理驱动开发 |
| finishing-a-development-branch | 完成开发分支 |
| using-git-worktrees | Git worktree隔离工作区 |

### 代码质量类
| Skill | 功能 |
|-------|------|
| code-refactoring | 代码重构技术 |
| code-reviewer | 代码审查 |
| receiving-code-review | 接收代码审查反馈 |
| security-audit | 安全审计 |
| systematic-debugging | 系统化调试 |

### 文档与报告类
| Skill | 功能 |
|-------|------|
| changelog-maintenance | 维护CHANGELOG |
| docx-processing | Word文档处理 |
| pdf-processing | PDF文件处理 |
| gpt-researcher | AI研究代理 |

### 前端开发类
| Skill | 功能 |
|-------|------|
| frontend-design | 前端设计 |
| ui-ux-pro-max | UI/UX设计系统生成 |
| web-interface-guidelines | Web界面指南 |
| webapp-testing | Web应用测试 |

### 架构与规划类
| Skill | 功能 |
|-------|------|
| software-architecture | 软件架构设计 |
| planning-with-files | 文件规划系统 |

### 搜索与研究类
| Skill | 功能 |
|-------|------|
| context7-docs | Context7文档获取 |
| tavily-search | Tavily搜索集成 |
| agent-browser | 浏览器自动化 |

### 工具类
| Skill | 功能 |
|-------|------|
| marketing-skills | 营销策略 |
| skill-creator | 创建新Skill |
| tmux-terminal | Tmux终端管理 |

### Cursor内置Skills (全局配置)
以下Skills位于全局目录，无需项目级配置：
- `babysit` - PR维护
- `create-hook` - 创建Cursor Hooks
- `create-rule` - 创建Cursor规则
- `create-skill` - 创建新Skill
- `statusline` - 状态行配置
- `update-cli-config` - CLI配置更新
- `update-cursor-settings` - Cursor设置更新

## 使用说明

### 在项目中使用Skills
当用户提出相关任务时，Cursor Agent会自动识别并使用相应的Skill。例如：
- 用户要求"帮我重构这段代码" → 自动使用 `code-refactoring` Skill
- 用户要求"创建一个新功能" → 自动使用 `brainstorming` → `writing-plans` 工作流
- 用户要求"审查这段代码" → 自动使用 `code-reviewer` Skill

### 让其它项目也复用这套Skills（推荐）
如果你希望“所有项目”都使用同一套 `.cursor/skills` 与 `.cursor/rules`，可以在其它项目里创建目录联接（junction）指向本仓库的配置。

在本仓库根目录执行（PowerShell）：

```powershell
# 方式1：用路径文件（推荐，能更好处理中文路径/编码）
powershell -NoProfile -ExecutionPolicy Bypass -File .\.cursor\install-shared-skills.ps1 `
  -ProjectsFile .\.cursor\projects.example.txt -Force

# 方式2：直接传参
powershell -NoProfile -ExecutionPolicy Bypass -File .\.cursor\install-shared-skills.ps1 `
  -Projects "E:\桌面\project\AI自动回复","E:\project\textpy" -Force
```

执行后，会在目标项目下生成：
- `.cursor/skills` → 指向 `Flowly-AI/.cursor/skills`
- `.cursor/rules` → 指向 `Flowly-AI/.cursor/rules`

### 添加新Skill
如需添加新Skill：
1. 在对应目录下创建新文件夹（如 `my-custom-skill/`）
2. 创建 `SKILL.md` 文件，包含frontmatter和内容
3. 遵循Skill创建规范（参考 `skill-creator` Skill）

## 注意事项

- 项目级Skills位于 `.cursor/skills/` 目录
- 这些Skills会被版本控制，与项目一起分享
- 全局Skills位于 `~/.cursor/skills/` 目录
- Cursor内置Skills位于 `~/.cursor/skills-cursor/` 目录（不可修改）
