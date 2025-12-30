/**
 * @fileoverview Vue 应用入口文件 (Application Entry Point)
 * @description 这是整个前端应用 (V5 版本) 的启动入口。
 *              主要职责包括：
 *              1. 创建 Vue 应用实例。
 *              2. 初始化并挂载 Pinia 状态管理库。
 *              3. 初始化并挂载 Vue Router 路由管理。
 *              4. 引入全局样式文件。
 *              5. 将应用挂载到 DOM 节点 (#app)。
 * 
 * @version 5.0.0
 */

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import './style.css' // 引入 Tailwind CSS 及全局自定义样式
import App from './App.vue'

// 创建 Vue 应用实例
const app = createApp(App)

// 注册 Pinia 状态管理插件
// Pinia 用于管理全局状态，如用户信息、应用配置等
app.use(createPinia())

// 注册 Vue Router 插件
// Router 负责处理页面导航和 URL 映射
app.use(router)

// 挂载应用到 HTML 页面中的 #app 元素
app.mount('#app')

