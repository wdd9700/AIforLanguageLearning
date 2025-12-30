/**
 * @fileoverview 提示词管理器 (Prompt Manager)
 * @description
 * 负责管理和渲染 LLM 使用的提示词模板。
 * 模板文件存储在 `backend/src/prompts` 目录下，支持 Markdown (.md) 和文本 (.txt) 格式。
 * 
 * 主要功能：
 * 1. 模板加载 (Load): 从文件系统读取模板内容，并提供内存缓存机制。
 * 2. 模板渲染 (Render): 使用简单的数据插值语法 (Mustache-style `{{key}}`) 将动态数据填充到模板中。
 * 3. 缓存管理 (Cache): 支持清除缓存以热加载修改后的模板。
 * 
 * @author AI for Foreign Language Learning Team
 * @lastModified 2025-01
 */

import fs from 'fs/promises';
import path from 'path';
import { createLogger } from '../utils/logger';

const logger = createLogger('PromptManager');

export class PromptManager {
  private promptsDir: string;
  private cache: Map<string, string> = new Map();

  constructor() {
    this.promptsDir = path.join(__dirname, '../prompts');
  }

  /**
   * 加载提示词模板
   * 
   * 从文件系统中读取指定名称的提示词模板。
   * 优先查找 .md 文件，其次查找 .txt 文件。
   * 读取成功后会将内容缓存到内存中。
   * 
   * @param name 提示词模板名称 (相对路径，如 'analysis/learning_report')
   * @returns Promise<string> 模板原始内容
   * @throws Error 如果模板文件不存在
   */
  private async loadTemplate(name: string): Promise<string> {
    if (this.cache.has(name)) {
      return this.cache.get(name)!;
    }

    try {
      // Try .md first, then .txt
      let filePath = path.join(this.promptsDir, `${name}.md`);
      try {
        await fs.access(filePath);
      } catch {
        filePath = path.join(this.promptsDir, `${name}.txt`);
      }

      const content = await fs.readFile(filePath, 'utf-8');
      this.cache.set(name, content);
      return content;
    } catch (error) {
      logger.error({ name, error }, 'Failed to load prompt template');
      throw new Error(`Prompt template not found: ${name}`);
    }
  }

  /**
   * 渲染提示词
   * 
   * 加载指定模板，并使用提供的数据对象替换模板中的占位符。
   * 支持嵌套属性访问，例如 `{{user.name}}`。
   * 
   * @param name 提示词模板名称
   * @param data 用于填充模板的数据对象
   * @returns Promise<string> 渲染后的完整提示词字符串
   */
  public async render(name: string, data: Record<string, any> = {}): Promise<string> {
    let template = await this.loadTemplate(name);

    // Simple mustache-style replacement {{key}}
    // Supports nested keys like {{user.name}}
    return template.replace(/\{\{([\w\.]+)\}\}/g, (match, key) => {
      const keys = key.split('.');
      let value: any = data;
      for (const k of keys) {
        if (value === undefined || value === null) return match;
        value = value[k];
      }
      return value !== undefined ? String(value) : match;
    });
  }

  /**
   * 清除模板缓存
   * 
   * 清空内存中的所有已加载模板。
   * 通常在开发模式下或更新模板文件后调用。
   */
  public clearCache() {
    this.cache.clear();
  }
}
