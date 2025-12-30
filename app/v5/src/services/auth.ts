/**
 * @fileoverview 认证服务模块 (Authentication Service)
 * @description 封装用户登录、自动登录保活等身份验证相关的业务逻辑。
 */

import api from './api';

export const AuthService = {
  /**
   * 用户登录
   * 
   * 向后端发送用户名和密码进行验证。
   * 验证成功后，将 Access Token 和用户信息保存到 LocalStorage。
   * 
   * @param {string} username - 用户名
   * @param {string} password - 密码
   * @returns {Promise<boolean>} 登录成功返回 true，失败返回 false
   */
  async login(username: string, password: string): Promise<boolean> {
    try {
      const response = await api.post('/api/auth/login', { username, password });
      // 由于 api 拦截器已经解包了 response.data，这里直接获取业务数据
      const data = response as any; 
      
      if (data.success) {
        // 保存 Token 用于后续请求鉴权
        localStorage.setItem('auth_token', data.data.accessToken);
        // 保存用户信息用于 UI 展示
        localStorage.setItem('auth_user', JSON.stringify(data.data.user));
        return true;
      }
      return false;
    } catch (e) {
      console.error('登录请求失败:', e);
      return false;
    }
  },

  /**
   * 确保用户已登录 (自动登录/保活)
   * 
   * 检查本地是否存在 Token。
   * 如果不存在，尝试使用默认凭证 (admin/admin) 进行自动登录。
   * 注意：此逻辑主要用于开发环境或演示模式，生产环境应跳转至登录页。
   * 
   * @returns {Promise<boolean>} 如果最终处于登录状态返回 true
   */
  async ensureLogin(): Promise<boolean> {
    const token = localStorage.getItem('auth_token');
    if (!token) {
      console.log('未检测到 Token，正在尝试默认自动登录...');
      return await this.login('admin', 'admin');
    }
    return true;
  }
};
