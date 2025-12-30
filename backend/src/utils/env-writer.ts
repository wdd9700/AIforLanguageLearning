/**
 * @fileoverview 环境变量写入工具 (Env Writer)
 * 
 * 提供对 .env 配置文件的安全更新功能。
 * 用于持久化保存运行时修改的配置项 (如 API Key, 端口设置等)。
 * 
 * 主要功能：
 * 1. 变量更新：支持新增或替换 .env 文件中的环境变量
 * 2. 原子写入：使用 "写入临时文件 -> 重命名" 策略，防止文件损坏
 * 3. 格式维护：自动处理换行符，保持文件格式整洁
 * 
 * @author GitHub Copilot
 * @copyright 2024 AiforForeignLanguageLearning
 */

import * as fs from 'fs';
import * as path from 'path';

/**
 * 更新 .env 文件中的变量
 * 用于持久化保存运行时修改的配置 (如 API Key, 端口等)
 * 
 * @param updates 键值对对象，key 为环境变量名，value 为新值
 */
export function updateEnvFile(updates: Record<string, string>): void {
    const envPath = path.resolve(__dirname, '../../../.env');
    let envContent = '';
    
    if (fs.existsSync(envPath)) {
        envContent = fs.readFileSync(envPath, 'utf-8');
    }

    Object.entries(updates).forEach(([key, value]) => {
        const regex = new RegExp(`^${key}=.*`, 'm');
        if (regex.test(envContent)) {
            // 替换已有变量
            envContent = envContent.replace(regex, `${key}=${value}`);
        } else {
            // 新增变量，确保文件末尾有换行符
            if (envContent && !envContent.endsWith('\n')) {
                envContent += '\n';
            }
            envContent += `${key}=${value}\n`;
        }
    });

    // 原子写入：写入临时文件 -> 重命名
    // 防止写入过程中断导致 .env 文件损坏
    const tempPath = `${envPath}.tmp`;
    try {
        fs.writeFileSync(tempPath, envContent.trim() + '\n');
        fs.renameSync(tempPath, envPath);
    } catch (error) {
        console.error('Failed to write .env file:', error);
        // 尝试清理临时文件
        if (fs.existsSync(tempPath)) {
            try { fs.unlinkSync(tempPath); } catch (e) {}
        }
        throw error;
    }
}
