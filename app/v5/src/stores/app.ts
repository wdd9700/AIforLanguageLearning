/**
 * @fileoverview 应用全局状态管理 (App Store)
 * @description 使用 Pinia 管理应用的全局 UI 状态，如侧边栏开关、主题设置等。
 */

import { defineStore } from 'pinia';
import { ref } from 'vue';

export const useAppStore = defineStore('app', () => {
  // 侧边栏展开/收起状态
  const isSidebarOpen = ref(true);
  
  // 当前主题模式 ('dark' | 'light')
  const theme = ref('dark');
  
  /**
   * 切换侧边栏显示状态
   */
  const toggleSidebar = () => {
    isSidebarOpen.value = !isSidebarOpen.value;
  };

  return {
    isSidebarOpen,
    theme,
    toggleSidebar
  };
});
