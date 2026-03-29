# 成员F：用户行为数据收集和监控日志 - 技术栈要求

## 角色定位
负责构建全链路用户行为追踪和系统监控告警体系。

---

## 技术栈深度要求

| 技术 | 深度要求 | 具体掌握内容 |
|------|----------|--------------|
| **Prometheus** | ⭐⭐⭐⭐⭐ 精通 | 指标类型(Counter/Gauge/Histogram)、exporters、告警规则 |
| **Grafana** | ⭐⭐⭐⭐ 熟练 | Dashboard设计、变量模板、告警通知、数据源配置 |
| **ELK Stack** | ⭐⭐⭐⭐ 熟练 | Filebeat采集、Logstash解析、Elasticsearch存储、Kibana查询 |
| **ClickHouse/TimescaleDB** | ⭐⭐⭐⭐ 熟练 | 时序数据模型、分区策略、聚合查询 |
| **Sentry** | ⭐⭐⭐ 了解 | 错误上报、Release追踪、性能监控 |

---

## 必须深入理解的概念

### 1. 指标(Metrics) vs 日志(Logs) vs 追踪(Traces)的区别
- Metrics：可聚合的数值型数据(QPS、延迟)
- Logs：离散的事件记录(错误日志、访问日志)
- Traces：请求链路的完整路径(分布式追踪)
- 三者的使用场景和存储方式

### 2. 时序数据库的降采样和保留策略
- 原始数据的高成本存储
- 降采样(Rollup)减少数据量
- 分级保留策略(hot/warm/cold)
- 数据生命周期管理

### 3. P50/P90/P99延迟百分位的含义
- 百分位数的统计意义
- 长尾延迟的影响
- 如何选择合适的SLA指标
- 直方图(Histogram)vs摘要(Summary)

---

## 核心技能检查清单

### Prometheus
- [ ] 掌握四种指标类型(Counter/Gauge/Histogram/Summary)
- [ ] 能编写PromQL查询语句
- [ ] 能配置Recording Rule和Alerting Rule
- [ ] 能编写自定义Exporter
- [ ] 理解服务发现和目标配置

### Grafana
- [ ] 能设计直观的Dashboard
- [ ] 掌握变量和模板的使用
- [ ] 能配置告警通道(邮件/钉钉/企业微信)
- [ ] 能进行多数据源关联展示

### ELK Stack
- [ ] 能配置Filebeat日志采集
- [ ] 能编写Logstash解析规则
- [ ] 能设计ES索引模板
- [ ] 能使用Kibana进行日志分析

### 时序数据库
- [ ] 理解时序数据的特点
- [ ] 能设计高效的数据模型
- [ ] 掌握分区策略
- [ ] 能进行聚合查询优化

---

## Copilot引导关键词

```
"使用Prometheus client暴露API指标"
"配置Grafana Dashboard展示QPS和延迟"
"实现结构化JSON日志输出到ELK"
"设计ClickHouse时序数据表结构"
"配置Prometheus告警规则"
```

---

## 推荐学习资源

| 资源类型 | 名称 | 优先级 |
|----------|------|--------|
| 官方文档 | Prometheus官方文档 | ⭐⭐⭐⭐⭐ |
| 官方文档 | Grafana官方文档 | ⭐⭐⭐⭐⭐ |
| 官方文档 | Elastic Stack文档 | ⭐⭐⭐⭐ |
| 书籍 | 《分布式系统监控》 | ⭐⭐⭐⭐ |

---

## 验收标准

- [ ] 全链路追踪可追溯任意请求
- [ ] 告警响应时间<5分钟
- [ ] 监控Dashboard实时刷新<10秒
- [ ] 日志查询支持秒级检索
