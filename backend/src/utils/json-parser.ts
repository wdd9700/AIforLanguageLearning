/**
 * @fileoverview JSON 解析工具 (JSON Parser)
 * 
 * 专门用于处理 LLM 返回的非标准 JSON 格式。
 * 能够从包含 Markdown 代码块、解释性文字或格式不规范的响应中提取有效的 JSON 数据。
 * 
 * 主要功能：
 * 1. 直接解析：尝试标准的 JSON.parse
 * 2. 代码块提取：自动识别并提取 ```json ... ``` 或 ``` ... ``` 中的内容
 * 3. 边界提取：查找首个 '{' 和最后一个 '}' 之间的内容进行解析
 * 4. 容错处理：多级降级策略，最大程度保证解析成功率
 * 
 * @author GitHub Copilot
 * @copyright 2024 AiforForeignLanguageLearning
 */

/**
 * 健壮的 JSON 解析器
 * 专门用于处理 LLM 返回的非标准 JSON 格式
 * 能够处理 Markdown 代码块、周围的文本说明等情况
 */
export function parseLLMJson<T = any>(response: string): T {
    // 1. 尝试直接解析
    try {
        return JSON.parse(response);
    } catch (e) {
        // 继续尝试其他提取策略
    }

    // 2. 尝试从 Markdown 代码块中提取
    // 匹配 ```json ... ``` 或 ``` ... ```
    const jsonBlockRegex = /```(?:json)?\s*([\s\S]*?)\s*```/;
    const match = response.match(jsonBlockRegex);
    
    if (match && match[1]) {
        try {
            return JSON.parse(match[1]);
        } catch (e) {
            // 提取的代码块解析失败
        }
    }

    // 3. 尝试查找第一个 '{' 和最后一个 '}' (朴素提取)
    // 适用于 LLM 在 JSON 前后添加了解释性文字的情况
    const firstBrace = response.indexOf('{');
    const lastBrace = response.lastIndexOf('}');
    
    if (firstBrace !== -1 && lastBrace !== -1 && lastBrace > firstBrace) {
        const potentialJson = response.substring(firstBrace, lastBrace + 1);
        try {
            return JSON.parse(potentialJson);
        } catch (e) {
            // 提取的大括号内容解析失败
        }
    }

    throw new Error('Failed to parse JSON from response');
}
