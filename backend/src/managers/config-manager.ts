/**
 * @fileoverview 配置管理器 (Config Manager)
 * @description
 * 该文件负责管理应用程序的动态配置，支持运行时修改和持久化。
 * 
 * 主要功能：
 * 1. 配置加载：启动时从 `dynamic_config.json` 加载配置，若不存在则回退到环境变量默认值
 * 2. 配置合并：将用户自定义配置与系统默认配置进行深度合并，确保配置结构的完整性
 * 3. 动态更新：提供 API 在运行时修改配置（如切换 LLM 模型、更新 Prompt 模板），并立即生效
 * 4. 持久化存储：将修改后的配置保存到磁盘，使用原子写入策略防止文件损坏
 * 5. Prompt 管理：专门的方法用于更新特定业务场景的 Prompt
 * 
 * 核心数据结构 (AppConfig)：
 * - prompts: 各场景的 System Prompts
 * - services: LLM, ASR, TTS 等服务的运行时参数
 * 
 * 待改进项：
 * - [ ] 引入配置版本控制，支持回滚到旧配置
 * - [ ] 增加配置变更通知机制 (Event Emitter)
 * - [ ] 支持配置加密存储 (针对敏感信息)
 * 
 * @author AI for Foreign Language Learning Team
 * @lastModified 2025-12
 */

import * as fs from 'fs';
import * as path from 'path';
import { PROMPTS } from '../config/prompts';
import { config as envConfig } from '../config/env';

export interface AppConfig {
  prompts: typeof PROMPTS;
  services: {
    llm: {
      models: typeof envConfig.services.llm.models;
      endpoints: {
        chat: string;
      };
    };
    asr: {
        modelSize: string;
    };
    tts: {
        promptAudioPath: string;
    };
  };
}

export class ConfigManager {
  private static instance: ConfigManager;
  private configPath: string;
  private config: AppConfig;

  private constructor() {
    this.configPath = path.join(__dirname, '../../data/dynamic_config.json');
    this.config = this.loadConfig();
  }

  /**
   * 获取单例实例
   */
  public static getInstance(): ConfigManager {
    if (!ConfigManager.instance) {
      ConfigManager.instance = new ConfigManager();
    }
    return ConfigManager.instance;
  }

  /**
   * 加载配置
   * 优先读取本地文件，如果失败或不存在则使用默认值
   */
  private loadConfig(): AppConfig {
    try {
      if (fs.existsSync(this.configPath)) {
        const fileContent = fs.readFileSync(this.configPath, 'utf-8');
        let savedConfig: any;
        try {
            savedConfig = JSON.parse(fileContent);
        } catch (parseError) {
            console.error('Failed to parse dynamic config JSON:', parseError);
            return this.getDefaults();
        }
        
        if (typeof savedConfig !== 'object' || savedConfig === null) {
            console.error('Dynamic config is not a valid object');
            return this.getDefaults();
        }

        // 合并保存的配置与默认配置，确保结构完整
        return this.mergeDefaults(savedConfig);
      }
    } catch (error) {
      console.error('Failed to load dynamic config, using defaults:', error);
    }

    return this.getDefaults();
  }

  /**
   * 获取默认配置
   * 基于环境变量和硬编码的默认值
   */
  private getDefaults(): AppConfig {
    return {
      prompts: PROMPTS,
      services: {
        llm: {
          models: envConfig.services.llm.models,
          endpoints: {
            chat: envConfig.services.llm.endpoint
          }
        },
        asr: {
            modelSize: envConfig.services.asr.modelSize
        },
        tts: {
            promptAudioPath: envConfig.services.tts.promptAudioPath
        }
      }
    };
  }

  /**
   * Deep merge helper
   */
  private deepMerge(target: any, source: any): any {
    if (typeof target !== 'object' || target === null) return source;
    if (typeof source !== 'object' || source === null) return target;

    const output = { ...target };
    Object.keys(source).forEach(key => {
        if (Array.isArray(source[key])) {
            output[key] = source[key]; // Arrays are overwritten, not merged
        } else if (typeof source[key] === 'object' && source[key] !== null) {
            if (!(key in target)) {
                Object.assign(output, { [key]: source[key] });
            } else {
                output[key] = this.deepMerge(target[key], source[key]);
            }
        } else {
            Object.assign(output, { [key]: source[key] });
        }
    });
    return output;
  }

  /**
   * 合并配置
   * 将保存的配置覆盖在默认配置之上
   */
  private mergeDefaults(saved: any): AppConfig {
    const defaults = this.getDefaults();
    return this.deepMerge(defaults, saved);
  }

  /**
   * 获取当前配置
   */
  public getConfig(): AppConfig {
    return this.config;
  }

  /**
   * 更新配置
   * 更新内存中的配置并持久化到磁盘
   */
  public updateConfig(partialConfig: Partial<AppConfig>): void {
    this.config = this.mergeDefaults({ ...this.config, ...partialConfig });
    this.saveConfig();
  }

  /**
   * 更新特定 Prompt
   * @param category Prompt 类别 (如 'system', 'user')
   * @param key Prompt 键名
   * @param value 新的 Prompt 内容
   */
  public updatePrompt(category: keyof typeof PROMPTS, key: string, value: any): void {
    // Ensure category exists in prompts
    if (!this.config.prompts[category]) {
        // Initialize if missing, though getDefaults should handle this.
        // Using type assertion to allow dynamic assignment if PROMPTS type is strict
        (this.config.prompts as any)[category] = {};
    }
    
    const promptCategory = this.config.prompts[category] as Record<string, any>;

    if (key === 'all') {
        // 替换整个类别
        (this.config.prompts as any)[category] = value;
    } else {
        // 更新单个条目
        promptCategory[key] = value;
    }
    this.saveConfig();
  }

  /**
   * 重新加载配置
   * 强制从磁盘读取最新配置
   */
  public reload(): void {
    this.config = this.loadConfig();
  }

  /**
   * 保存配置到磁盘
   * 使用原子写入 (写入临时文件 -> 重命名) 防止文件损坏
   */
  private saveConfig(): void {
    try {
      const dir = path.dirname(this.configPath);
      if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
      }
      
      // 原子写入：先写入临时文件，再重命名
      const tempPath = `${this.configPath}.tmp`;
      fs.writeFileSync(tempPath, JSON.stringify(this.config, null, 2), 'utf-8');
      fs.renameSync(tempPath, this.configPath);
      
    } catch (error) {
      console.error('Failed to save dynamic config:', error);
    }
  }
}
