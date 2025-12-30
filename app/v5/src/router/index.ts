/**
 * @fileoverview 路由配置模块 (Vue Router)
 * @description 定义前端应用的路由规则，映射 URL 路径到具体的页面组件。
 *              使用 Hash 模式以确保在 Electron 环境下的兼容性。
 */

import { createRouter, createWebHashHistory, RouteRecordRaw } from 'vue-router'

// 引入页面组件
import HomeView from '../views/HomeView.vue'
import VoiceView from '../views/VoiceView.vue'
import AnalysisView from '../views/AnalysisView.vue'
import SettingsView from '../views/SettingsView.vue'
import EssayView from '../views/EssayView.vue'

/**
 * 路由表定义
 */
const routes: Array<RouteRecordRaw> = [
  {
    path: '/',
    name: 'home',
    component: HomeView,
    meta: { title: '首页' }
  },
  {
    path: '/essay',
    name: 'essay',
    component: EssayView,
    meta: { title: '作文批改' }
  },
  {
    path: '/voice',
    name: 'voice',
    component: VoiceView,
    meta: { title: '语音对话' }
  },
  {
    path: '/analysis',
    name: 'analysis',
    component: AnalysisView,
    meta: { title: '学习分析' }
  },
  {
    path: '/settings',
    name: 'settings',
    component: SettingsView,
    meta: { title: '设置' }
  }
]

/**
 * 创建路由实例
 * 
 * 使用 createWebHashHistory (Hash 模式)，URL 中会包含 '#'。
 * 这种模式不需要服务器端配置重定向，非常适合 Electron 这种本地文件系统环境。
 */
const router = createRouter({
  history: createWebHashHistory(), 
  routes
})

export default router
