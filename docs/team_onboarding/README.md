# 团队入职指南

本目录包含AI外语学习系统开发团队的入职资料，分为两个部分：

## 📁 目录结构

```
team_onboarding/
├── README.md                          # 本文件
├── skill_requirements/                # 技术栈要求
│   ├── member_a_database_es.md       # 成员A：数据库和ES
│   ├── member_b_infrastructure.md    # 成员B：缓存/消息队列/存储
│   ├── member_c_knowledge_graph.md   # 成员C：知识图谱和推荐
│   ├── member_d_security.md          # 成员D：安全认证
│   ├── member_e_model_routing.md     # 成员E：模型路由
│   ├── member_f_monitoring.md        # 成员F：监控日志
│   └── member_g_core_features.md     # 成员G：核心功能
├── vc_prompts/                        # VC引导Prompt
│   ├── vc_prompt_database_es.md
│   ├── vc_prompt_infrastructure.md
│   ├── vc_prompt_knowledge_graph.md
│   ├── vc_prompt_security.md
│   ├── vc_prompt_model_routing.md
│   ├── vc_prompt_monitoring.md
│   └── vc_prompt_core_features.md
└── shared_knowledge.md                # 团队共享知识
```

## 🎯 使用方式

### 对于团队成员
1. 首先阅读 `shared_knowledge.md` 了解项目全局
2. 根据分配找到对应的技术栈要求文件，评估自身技能差距
3. 将对应的VC引导prompt复制到Copilot Chat中使用

### 对于团队负责人
1. 根据成员技能分配对应模块
2. 将对应的技术栈要求和VC prompt分别发给成员
3. 定期对照验收标准检查进度

## 📋 模块分配速查

| 成员 | 模块 | 技术栈文件 | VC Prompt文件 |
|------|------|-----------|---------------|
| A | 数据库和ElasticSearch | `member_a_database_es.md` | `vc_prompt_database_es.md` |
| B | 缓存/消息队列/文件存储 | `member_b_infrastructure.md` | `vc_prompt_infrastructure.md` |
| C | 知识图谱和推荐引擎 | `member_c_knowledge_graph.md` | `vc_prompt_knowledge_graph.md` |
| D | 安全认证 | `member_d_security.md` | `vc_prompt_security.md` |
| E | 模型路由和上下文管理 | `member_e_model_routing.md` | `vc_prompt_model_routing.md` |
| F | 用户行为数据收集和监控日志 | `member_f_monitoring.md` | `vc_prompt_monitoring.md` |
| G | 核心功能开发 | `member_g_core_features.md` | `vc_prompt_core_features.md` |

## ⚠️ 重要提示

1. **依赖关系**：模块间存在依赖，建议按以下顺序启动：
   - 第1周：A(数据库) + B(基础设施) + D(安全) 并行
   - 第2周：E(模型路由) + C(知识图谱) 启动
   - 第3周：G(核心功能) 开发（基础设施已就绪）
   - F(监控) 可与各模块并行

2. **实时助教模块**：作为项目亮点，建议核心功能完成后再投入开发

3. **技能共享**：鼓励成员了解相邻模块的基础知识，便于协作
