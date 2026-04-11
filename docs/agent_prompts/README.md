# Agent Prompt 使用指南

> **工作模式声明**：本项目所有 agent 本质上都是 Copilot 会话。
> 
> 1. 我将 prompt 落入 md 文档中
> 2. 你（用户）手动在 Copilot 会话中执行这些 prompt
> 3. 你将执行结果汇总到 md 文档中反馈给我
> 4. 我基于汇总结果继续下一步工作

---

## 文档结构

```
docs/agent_prompts/
├── README.md                          # 本文件
├── phase_1_dead_code_cleanup/         # 阶段1：死代码清理与有效代码迁移
│   ├── expert_01_archaeologist.md     # 专家：代码考古学家
│   ├── expert_02_migration_planner.md # 专家：迁移规划师
│   └── subagent_01_migrator.md        # 执行：代码迁移工
│
├── phase_2_module_integration/        # 阶段2：新模块整合
│   ├── expert_03_integrator.md        # 专家：模块整合顾问
│   └── subagent_02_integrator.md      # 执行：模块整合工
│
├── phase_3_infrastructure/            # 阶段3：基础设施加固/重写
│   ├── expert_04_infrastructure.md    # 专家：基础设施架构师
│   └── subagent_03_infrastructure.md  # 执行：基础设施工程师
│
└── shared/
    ├── context_template.md            # 共享上下文模板
    └── output_template.md             # 输出格式模板
```

---

## 执行顺序

### 第一轮（阶段1准备）
1. `expert_01_archaeologist.md` — 让专家评估旧代码状态
2. `expert_02_migration_planner.md` — 让专家制定迁移计划
3. 将两位专家的输出汇总到 `phase_1_results.md`
4. 反馈给我，我生成 `subagent_01_migrator.md` 的执行指令

### 第二轮（阶段1执行）
5. `subagent_01_migrator.md` — 执行代码迁移
6. 将迁移结果汇总到 `phase_1_results.md`
7. 反馈给我，我进入阶段2

### 第三轮（阶段2准备+执行）
8. `expert_03_integrator.md` — 评估模块整合风险
9. `subagent_02_integrator.md` — 执行模块整合
10. 结果汇总到 `phase_2_results.md`

### 第四轮（阶段3准备+执行）
11. `expert_04_infrastructure.md` — 评估基础设施需求
12. `subagent_03_infrastructure.md` — 执行基础设施加固
13. 结果汇总到 `phase_3_results.md`

---

## 输出规范

每次执行 agent prompt 后，请按以下格式汇总结果：

```markdown
## Agent 执行结果汇总

**执行时间**: YYYY-MM-DD HH:MM
**Agent 名称**: [名称]
**Prompt 文件**: [路径]

### 主要结论
[3-5条核心结论]

### 关键发现
[详细发现，带代码引用和文件路径]

### 风险与建议
[识别的问题和建议]

### 下一步行动
[明确的可执行任务]
```
