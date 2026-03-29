# 09 - 项目熵管理

> **开发方法论**: Agentic Engineering + BMAD-METHOD + SDD  
> **版本**: v1.0  
> **最后更新**: 2026-03-30

---

## 一、项目熵的概念

### 1.1 什么是项目熵?

项目熵衡量的是项目混乱程度的指标，包括：
- **代码熵**: 代码复杂度、重复度、技术债务
- **文档熵**: 文档陈旧、不一致、缺失
- **流程熵**: 流程混乱、沟通低效、决策延迟
- **架构熵**: 架构腐化、边界模糊、依赖混乱

### 1.2 熵增定律

> 如果不主动管理，项目熵会自然增加，导致开发效率下降、缺陷率上升。

---

## 二、熵的度量

### 2.1 代码熵指标

| 指标 | 工具 | 目标值 | 告警阈值 |
|------|------|--------|----------|
| 代码复杂度 | radon | < 10 | > 15 |
| 重复代码 | jscpd | < 3% | > 5% |
| 测试覆盖率 | pytest | > 80% | < 70% |
| 类型覆盖率 | mypy | > 90% | < 80% |
| 代码异味 | pylint | 0 | > 10 |

### 2.2 文档熵指标

| 指标 | 检查方式 | 目标值 |
|------|----------|--------|
| API文档覆盖率 | 自动检查 | 100% |
| 代码注释率 | 工具统计 | > 20% |
| 文档更新及时性 | 版本对比 | < 1周 |
| 架构文档完整性 | 人工检查 | 完整 |

### 2.3 架构熵指标

| 指标 | 检查方式 | 目标值 |
|------|----------|--------|
| 循环依赖 | import-linter | 0 |
| 模块耦合度 | 架构评审 | 低耦合 |
| 接口稳定性 | 版本控制 | 向后兼容 |
| 技术债务率 | 代码审查 | < 10% |

---

## 三、熵减策略

### 3.1 代码熵减

#### 持续重构

```python
# 重构前 - 高熵代码
def process(data):
    result = []
    for i in range(len(data)):
        if data[i]['type'] == 'A':
            x = data[i]['value'] * 2
            if x > 10:
                result.append({'id': data[i]['id'], 'val': x})
    return result

# 重构后 - 低熵代码
from typing import List, Dict, Any
from dataclasses import dataclass

@dataclass
class DataItem:
    id: str
    type: str
    value: float

@dataclass  
class ProcessedItem:
    id: str
    value: float

def process_type_a_items(items: List[DataItem]) -> List[ProcessedItem]:
    """Process type A items with value doubling."""
    THRESHOLD = 10
    MULTIPLIER = 2
    
    processed = []
    for item in items:
        if item.type != 'A':
            continue
            
        doubled_value = item.value * MULTIPLIER
        if doubled_value > THRESHOLD:
            processed.append(ProcessedItem(
                id=item.id,
                value=doubled_value
            ))
    
    return processed
```

#### 重构检查清单

- [ ] 函数长度 < 50 行
- [ ] 嵌套深度 < 4 层
- [ ] 参数数量 < 5 个
- [ ] 每个函数单一职责
- [ ] 有意义的命名
- [ ] 必要的注释

### 3.2 文档熵减

#### 文档即代码

```yaml
# .github/workflows/docs.yml
name: Documentation

on:
  push:
    paths:
      - 'docs/**'
      - '**.py'
      - '**.ts'
      - '**.vue'

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Check API docs coverage
        run: |
          python scripts/check_api_docs.py
      
      - name: Check doc freshness
        run: |
          python scripts/check_doc_freshness.py --max-days 7
      
      - name: Generate API docs
        run: |
          python -m scripts.generate_api_docs
```

#### 文档更新触发器

| 触发条件 | 必须更新的文档 |
|----------|----------------|
| API变更 | 接口定义文档 |
| 数据库变更 | 数据模型文档 |
| 架构变更 | 架构设计文档 |
| 新功能 | 用户手册 |
| Bug修复 | 变更日志 |

### 3.3 架构熵减

#### 架构守护规则

```python
# archguard/rules.py
import ast
from typing import List

class ArchitectureGuard:
    """Enforces architectural constraints."""
    
    # 允许的依赖方向
    ALLOWED_DEPENDENCIES = {
        'app.api': ['app.services', 'app.models'],
        'app.services': ['app.models', 'app.infrastructure'],
        'app.models': [],
        'app.infrastructure': [],
    }
    
    # 禁止的导入
    FORBIDDEN_IMPORTS = [
        ('app.api', 'app.infrastructure'),  # API不能直接访问基础设施
    ]
    
    @classmethod
    def check_import(cls, from_module: str, to_module: str) -> bool:
        """Check if import is allowed."""
        for forbidden_from, forbidden_to in cls.FORBIDDEN_IMPORTS:
            if from_module.startswith(forbidden_from) and \
               to_module.startswith(forbidden_to):
                return False
        return True
```

---

## 四、熵监控仪表盘

### 4.1 监控指标

```python
# metrics/entropy_metrics.py
from prometheus_client import Gauge, Counter, Histogram

# 代码熵指标
code_complexity = Gauge(
    'code_complexity_avg',
    'Average code complexity',
    ['module']
)

code_duplication = Gauge(
    'code_duplication_percent',
    'Code duplication percentage'
)

test_coverage = Gauge(
    'test_coverage_percent',
    'Test coverage percentage',
    ['module']
)

# 文档熵指标
doc_freshness = Gauge(
    'doc_freshness_days',
    'Days since last doc update',
    ['document']
)

api_doc_coverage = Gauge(
    'api_doc_coverage_percent',
    'API documentation coverage'
)

# 架构熵指标
architecture_violations = Counter(
    'architecture_violations_total',
    'Total architecture violations',
    ['rule']
)

circular_dependencies = Gauge(
    'circular_dependencies_count',
    'Number of circular dependencies'
)
```

### 4.2 仪表盘配置

```json
{
  "dashboard": {
    "title": "Project Entropy Monitor",
    "panels": [
      {
        "title": "Code Complexity Trend",
        "type": "graph",
        "targets": [
          {
            "expr": "code_complexity_avg",
            "legendFormat": "{{module}}"
          }
        ],
        "alert": {
          "conditions": [
            {
              "evaluator": {
                "params": [15],
                "type": "gt"
              }
            }
          ]
        }
      },
      {
        "title": "Test Coverage",
        "type": "gauge",
        "targets": [
          {
            "expr": "test_coverage_percent"
          }
        ],
        "fieldConfig": {
          "thresholds": {
            "steps": [
              {"color": "red", "value": 0},
              {"color": "yellow", "value": 70},
              {"color": "green", "value": 80}
            ]
          }
        }
      }
    ]
  }
}
```

---

## 五、熵减工作流程

### 5.1 日常熵减

```
每日:
  □ 代码提交前运行 linter
  □ 修复新产生的代码异味
  □ 更新相关文档

每周:
  □ 代码审查会议
  □ 技术债务评估
  □ 文档更新检查

每月:
  □ 架构评审
  □ 重构计划制定
  □ 熵指标回顾
```

### 5.2 专项熵减

| 类型 | 频率 | 负责人 | 输出 |
|------|------|--------|------|
| 代码重构 | 每 Sprint | 开发团队 | 重构PR |
| 文档更新 | 每两周 | 技术写作者 | 更新文档 |
| 架构清理 | 每月 | 架构师 | 架构决策记录 |
| 依赖升级 | 每季度 | DevOps | 升级报告 |

---

## 六、熵预算管理

### 6.1 技术债务预算

| Sprint | 新功能占比 | 技术债务占比 |
|--------|------------|--------------|
| 正常 | 80% | 20% |
| 还债 | 50% | 50% |
| 重构 | 20% | 80% |

### 6.2 熵增控制红线

| 指标 | 红线 | 触发动作 |
|------|------|----------|
| 测试覆盖率 | < 70% | 停止新功能开发 |
| 代码复杂度 | > 15 | 强制重构 |
| 文档陈旧 | > 2周 | 文档更新Sprint |
| 架构违规 | > 5个 | 架构评审会议 |

---

## 七、变更日志

| 版本 | 日期 | 变更内容 | 作者 |
|------|------|----------|------|
| v1.0 | 2026-03-30 | 初始版本 | GitHub Copilot |
