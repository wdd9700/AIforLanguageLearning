# 知识图谱API参考文档

## 基础信息
- **Base URL**: `http://localhost:8000/v1/vocab`
- **Content-Type**: `application/json`

---

## 1. 词汇关系查询

### GET /relations/{word}
获取词汇的所有关系

**参数**:
- `word` (path): 查询的词汇
- `relation_type` (query): 关系类型 (synonym/antonym/cognate/similar_form/all)
- `limit` (query): 返回数量限制，默认10

**示例**:
```bash
curl "http://localhost:8000/v1/vocab/relations/unhappy?relation_type=antonym&limit=5"
```

**响应**:
```json
{
  "word": "unhappy",
  "relations": [
    {
      "word": "happy",
      "relation_type": "antonym",
      "strength": 0.95,
      "meaning": null
    }
  ],
  "total": 1
}
```

---

## 2. 词汇推荐

### POST /recommend
基于用户画像智能推荐词汇

**请求体**:
```json
{
  "user_id": "user_001",
  "count": 5,
  "user_level": 2,
  "weak_points": ["happy"],
  "learned_words": ["good", "bad"]
}
```

**响应**:
```json
{
  "user_id": "user_001",
  "recommendations": [
    {
      "word": "joyful",
      "reason": "'happy'的同义词，帮助巩固薄弱点",
      "score": 0.81,
      "relation_type": "synonym"
    }
  ],
  "total": 5
}
```

---

## 3. 同根词分析

### POST /cognates/analyze
分析词汇的词根词缀

**请求体**:
```json
{
  "word": "unhappiness"
}
```

**响应**:
```json
{
  "word": "unhappiness",
  "cognates": [
    {
      "word": "happiness",
      "type": "prefix",
      "affix": "un",
      "meaning": "否定"
    }
  ],
  "total": 1
}
```

---

## 4. 学习路径生成

### POST /learning-path
生成词汇学习路径 (A*算法)

**请求体**:
```json
{
  "start_word": "happy",
  "target_word": "excited",
  "max_depth": 5
}
```

**响应**:
```json
{
  "start_word": "happy",
  "target_word": "excited",
  "path": [
    {
      "from": "happy",
      "to": "joyful",
      "relation": "synonym",
      "strength": 0.9
    }
  ],
  "total_steps": 1,
  "found": true
}
```

---

## 5. 添加词汇关系

### POST /relations/add
手动添加词汇关系

**请求体**:
```json
{
  "source": "happy",
  "target": "joyful",
  "relation_type": "synonym",
  "strength": 0.9
}
```

**响应**:
```json
{
  "success": true,
  "message": "Relation added successfully"
}
```

---

## 6. 查词 (集成知识图谱)

### POST /lookup
查词并自动构建知识图谱关系

**请求体**:
```json
{
  "term": "rebuild",
  "session_id": "session_001"
}
```

**响应**:
```json
{
  "term": "rebuild",
  "definition": "释义：重建...",
  "from_public_vocab": false
}
```

**注意**: 查词后会自动识别词根词缀并建立关系

---

## 错误处理

所有API遵循统一错误格式:

```json
{
  "detail": "错误描述信息"
}
```

常见状态码:
- `200`: 成功
- `400`: 请求参数错误
- `500`: 服务器内部错误
