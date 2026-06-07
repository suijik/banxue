import { createApp } from 'vue'
import App from './App.vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import axios from 'axios'

const app = createApp(App)

// 注册所有图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

// 创建axios实例
const api = axios.create({
  baseURL: '/api',
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 直接API实例
const directApi = axios.create({
  baseURL: 'http://101.43.79.198:5000/api',
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器 - 代理API
api.interceptors.request.use(
  config => {
    console.log('【代理请求】:', config.method.toUpperCase(), config.url, config.data)
    const token = uni.getStorageSync('token')
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`
    }
    return config
  },
  error => {
    console.error('【代理请求错误】:', error)
    return Promise.reject(error)
  }
)

// 请求拦截器 - 直接API
directApi.interceptors.request.use(
  config => {
    console.log('【直接请求】:', config.method.toUpperCase(), config.url, config.data)
    const token = uni.getStorageSync('token')
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`
    }
    return config
  },
  error => {
    console.error('【直接请求错误】:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器 - 代理API
api.interceptors.response.use(
  response => {
    console.log('【代理响应】:', response.status, response.data)
    return response
  },
  error => {
    console.error('【代理响应错误】:', error)
    logResponseError(error)
    return Promise.reject(error)
  }
)

// 响应拦截器 - 直接API
directApi.interceptors.response.use(
  response => {
    console.log('【直接响应】:', response.status, response.data)
    return response
  },
  error => {
    console.error('【直接响应错误】:', error)
    logResponseError(error)
    return Promise.reject(error)
  }
)

// 日志记录响应错误的辅助函数
const logResponseError = (error) => {
  if (error.response) {
    console.error('错误状态码:', error.response.status)
    console.error('错误数据:', error.response.data)
    if (error.response.data && error.response.data.message) {
      uni.showToast({
        title: error.response.data.message,
        icon: 'none'
      })
    }
  } else if (error.request) {
    console.error('未收到响应:', error.request)
    uni.showToast({
      title: '服务器未响应，请检查网络连接',
      icon: 'none'
    })
  } else {
    console.error('请求配置错误:', error.message)
    uni.showToast({
      title: '请求配置错误: ' + error.message,
      icon: 'none'
    })
  }
}

// 认证相关API
const authAPI = {
  login: (data) => api.post('/login', data),
  register: (data) => api.post('/register', data),
  resetPassword: (data) => api.post('/reset', data),
  sendCode: (email) => api.post('/send_code', { email }),
  updateUserInfo: (data) => api.post('/update_userinfo', data),
  getUserInfo: () => api.get('/userinfo'),
  logout: () => api.post('/logout'),
  
  // 试卷分析相关API
  uploadExamPaper: (data) => api.post('/upload_exam_paper', data),
  getExamAnalyses: (username) => api.get('/exam_analyses', { params: { username } }),
  getExamAnalysisDetail: (analysisId) => api.get(`/exam_analysis/${analysisId}`),
  
  // 错题本相关API
  getMistakes: (params) => api.get('/mistakes', { params }),
  createMistake: (data) => api.post('/mistakes', data),
  updateMistake: (id, data) => api.put(`/mistakes/${id}`, data),
  deleteMistake: (id) => api.delete(`/mistakes/${id}`),
  
  // 知识点相关API
  getKnowledgePoints: (params) => api.get('/knowledge-points', { params }),
  createKnowledgePoint: (data) => api.post('/knowledge-points', data),
  updateKnowledgePoint: (id, data) => api.put(`/knowledge-points/${id}`, data)
}

// 直接使用Axios进行请求的备用方法
const directAPI = {
  login: (data) => directApi.post('/login', data),
  register: (data) => directApi.post('/register', data),
  resetPassword: (data) => directApi.post('/reset', data),
  sendCode: (email) => directApi.post('/send_code', { email }),
  updateUserInfo: (data) => directApi.post('/update_userinfo', data),
  getUserInfo: () => directApi.get('/userinfo'),
  logout: () => directApi.post('/logout'),
  
  // 试卷分析相关API
  uploadExamPaper: (data) => directApi.post('/upload_exam_paper', data),
  getExamAnalyses: (username) => directApi.get('/exam_analyses', { params: { username } }),
  getExamAnalysisDetail: (analysisId) => directApi.get(`/exam_analysis/${analysisId}`),
  
  // 错题本相关API
  getMistakes: (params) => directApi.get('/mistakes', { params }),
  createMistake: (data) => directApi.post('/mistakes', data),
  updateMistake: (id, data) => directApi.put(`/mistakes/${id}`, data),
  deleteMistake: (id) => directApi.delete(`/mistakes/${id}`),
  
  // 知识点相关API
  getKnowledgePoints: (params) => directApi.get('/knowledge-points', { params }),
  createKnowledgePoint: (data) => directApi.post('/knowledge-points', data),
  updateKnowledgePoint: (id, data) => directApi.put(`/knowledge-points/${id}`, data)
}

// 将API实例添加到全局属性
app.config.globalProperties.$authAPI = authAPI
app.config.globalProperties.$directAPI = directAPI

// === 稳定版全局路由守卫 ===
// 白名单：不需要登录就可以访问的页面
const whiteList = [
  '/pages/login/login',
  '/pages/register/register',
  '/pages/reset/reset',
  '/pages/home/home' // 首页可以公开访问
];

function hasPermission(url) {
  if (!url) return true;
  // 提取路径部分（去掉查询参数）
  const path = url.split('?')[0];
  
  // 1. 如果在白名单内，直接放行
  if (whiteList.includes(path)) {
    return true;
  }
  
  // 2. 如果不在白名单内，检查登录状态
  const token = uni.getStorageSync('token');
  const user = uni.getStorageSync('user');
  
  // 必须同时有 token 和 user 缓存才算登录
  if (token && user) {
    return true;
  }
  
  return false;
}

// 统一的路由拦截处理函数
const routeInterceptor = {
  invoke(e) {
    // e.url 就是要跳转的路径
    if (!hasPermission(e.url)) {
      uni.showToast({
        title: '请先登录',
        icon: 'none'
      });
      // 延迟一点点跳转，让 Toast 能显示出来
      setTimeout(() => {
        uni.navigateTo({
          url: '/pages/login/login'
        });
      }, 500);
      
      return false; // 拦截本次跳转
    }
    return true; // 放行
  }
};

// 注册路由拦截器（使用 UniApp 官方 API）
uni.addInterceptor('navigateTo', routeInterceptor);
uni.addInterceptor('redirectTo', routeInterceptor);
uni.addInterceptor('switchTab', routeInterceptor);
uni.addInterceptor('reLaunch', routeInterceptor);
// ========================

app.use(ElementPlus)
app.mount('#app')