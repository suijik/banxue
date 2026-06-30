import { ref } from 'vue';

// API基础配置
export const baseURL = 'http://127.0.0.1:5000/api'; // 根据实际API地址修改
export const serverURL = 'http://127.0.0.1:5000'; // 后端服务基础地址

// 创建请求函数
const request = (options) => {
  return new Promise((resolve, reject) => {
    // 处理URL参数
    let url = baseURL + options.url;
    if (options.params) {
      const queryString = Object.keys(options.params)
        .filter(key => options.params[key] !== null && options.params[key] !== undefined)
        .map(key => `${encodeURIComponent(key)}=${encodeURIComponent(options.params[key])}`)
        .join('&');
      if (queryString) {
        url += (url.includes('?') ? '&' : '?') + queryString;
      }
    }
    
    // 解决本地开发环境跨域问题
    const headers = {
      'Content-Type': 'application/json'
    };
    
    // 添加token认证
    const token = uni.getStorageSync('token');
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    
    console.log(`发送请求: ${options.method || 'GET'} ${url}`);
    
    uni.request({
      url: url,
      method: options.method || 'GET',
      data: options.data,
      header: headers,
      success: (res) => {
        console.log(`请求成功: ${url}`, res.data);
        
        // 统一处理后端 Token 失效或未授权 (401)
        if (res.statusCode === 401 || (res.data && res.data.code === 401)) {
          // 清除失效的本地登录状态
          uni.removeStorageSync('token');
          uni.removeStorageSync('user');
          
          uni.showToast({
            title: '登录已过期，请重新登录',
            icon: 'none'
          });
          
          // 延迟跳转，确保提示能看到
          setTimeout(() => {
            uni.reLaunch({ url: '/pages/login/login' });
          }, 1000);
          
          reject({ success: false, message: '登录已过期' });
          return;
        }

        // 直接返回后端响应
        resolve(res.data);
      },
      fail: (err) => {
        console.error('API请求失败:', err);
        // 返回标准化的错误响应
        reject({
          success: false,
          message: err.errMsg || '网络请求失败'
        });
      }
    });
  });
};

// 统一的错误拦截处理，如果后端返回401（未授权），可以在这里加一个拦截跳回登录。

// 认证相关API
const authAPI = {
  // 登录
  login: (data) => request({
    url: '/login',
    method: 'POST',
    data
  }),
  
  // 注册
  register: (data) => request({
    url: '/register',
    method: 'POST',
    data
  }),
  
  // 发送验证码
  sendCode: (email) => request({
    url: '/send_code',
    method: 'POST',
    data: { email }
  }),
  
  // 重置密码
  resetPassword: (data) => request({
    url: '/reset-password',
    method: 'POST',
    data
  }),
  
  // 获取用户信息
  getUserInfo: () => request({
    url: '/user/info'
  }),
  
  // 更新用户信息
  updateUserInfo: (data) => request({
    url: '/update_userinfo',
    method: 'POST',
    data
  }),
  
  // 退出登录
  logout: () => request({
    url: '/logout',
    method: 'POST'
  })
};

// 试卷分析相关API
const examAPI = {
  // 上传试卷
  uploadExamPaper: (data) => request({
    url: '/upload_exam_paper',
    method: 'POST',
    data
  }),
  
  // 获取分析结果
  getAnalysisResult: (analysisId) => request({
    url: `/exam_analysis/${analysisId}`
  }),
  
  // 获取历史分析记录
  getHistory: () => request({
    url: '/exam_analyses'
  }),
  
  // 获取用户科目列表
  getSubjects: () => request({
    url: '/subjects'
  }),

  // 删除分析记录
  deleteAnalysis: (analysisId) => request({
    url: `/exam_analysis/${analysisId}`,
    method: 'DELETE'
  })
};

// 错题本相关API
const mistakeAPI = {
  // 获取错题列表
  getMistakes: (params) => request({
    url: '/mistakes',
    params: params
  }),
  
  // 获取单个错题详情
  getMistake: (params) => request({
    url: `/mistakes/${params.id}`
  }),
  
  // 获取错题详情（无需验证登录状态）
  getMistakeDetail: (id) => request({
    url: `/mistakes/detail/${id}`
  }),
  
  // 更新错题状态
  updateMistake: (id, data) => request({
    url: `/mistakes/${id}`,
    method: 'PUT',
    data
  }),
  
  // 删除错题
  deleteMistake: (id) => request({
    url: `/mistakes/${id}`,
    method: 'DELETE'
  }),

  // 删除整张试卷下的错题
  deleteMistakeGroup: (data) => request({
    url: '/mistakes/group',
    method: 'DELETE',
    data
  })
};

// 知识库相关API
const knowledgeAPI = {
  // 获取知识点列表
  getKnowledgePoints: (params) => request({
    url: '/knowledge-points',
    method: 'get',
    params
  }),
  
  // 获取相关知识点
  getRelatedPoints: (id) => request({
    url: `/knowledge-points/${id}/related`,
    method: 'GET'
  }),
  
  // 获取练习题列表
  getPracticeQuestions: (params) => request({
    url: '/practice-questions',
    method: 'get',
    params
  }),
  
  // 更新练习题掌握状态
  updatePracticeMastery: (questionId, data) => request({
    url: `/practice-questions/${questionId}`,
    method: 'PUT',
    data
  }),
  
  // 删除练习题
  deletePracticeQuestion: (questionId, data) => request({
    url: `/practice-questions/${questionId}`,
    method: 'DELETE',
    data
  }),
  
  // 更新知识点掌握状态
  updateMastery: (id, data) => request({
    url: `/knowledge-points/${id}/toggle-mastery`,
    method: 'PUT',
    data
  }),
  
  // 报告资源问题
  reportResourceIssue: (data) => request({
    url: '/knowledge/report-resource-issue',
    method: 'POST',
    data
  })
};

// 报告相关API
const reportAPI = {
  // 获取家长辅导面板数据
  getParentDashboard: () => request({
    url: '/report/parent-dashboard',
    method: 'GET'
  })
};

// 答疑相关API
const qaAPI = {
  chat: (data) => request({
    url: '/qa/chat',
    method: 'POST',
    data
  })
};

// 统一导出所有API
export {
  authAPI,
  examAPI,
  mistakeAPI,
  knowledgeAPI,
  getLearningData,
  reportAPI,
  qaAPI
};

// 学习报告相关API
const getLearningData = (params) => request({
  url: `/report/learning-trends`,
  params: {
    start_date: params.start_date,
    end_date: params.end_date
  }
});

// 日期格式化辅助函数
function formatDate(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
} 
