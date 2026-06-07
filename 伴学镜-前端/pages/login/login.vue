<template>
  <view class="login-container">
    <!-- 背景装饰 -->
    <view class="bg-shape shape-1"></view>
    <view class="bg-shape shape-2"></view>

    <view class="login-content">
      <!-- 头部区域 -->
      <view class="header-section">
        <view class="logo-box">
          <image class="logo-img" src="/static/logo.png" mode="aspectFill"></image>
        </view>
        <text class="main-title">欢迎来到伴学镜</text>
        <text class="sub-title">智能辅导，让学习更轻松高效</text>
      </view>

      <!-- 登录表单卡片 -->
      <view class="form-card">
        <uni-forms ref="form" :model="loginForm" :rules="rules">
          <uni-forms-item name="username">
            <view class="custom-input-group">
              <view class="input-icon">
                <uni-icons type="person-filled" size="22" color="#5C6BC0"></uni-icons>
              </view>
              <input 
                class="custom-input" 
                v-model="loginForm.username" 
                placeholder="请输入用户名/学号" 
                placeholder-class="input-placeholder"
              />
            </view>
          </uni-forms-item>
          
          <uni-forms-item name="password">
            <view class="custom-input-group">
              <view class="input-icon">
                <uni-icons type="locked-filled" size="22" color="#5C6BC0"></uni-icons>
              </view>
              <input 
                class="custom-input" 
                v-model="loginForm.password" 
                type="password" 
                placeholder="请输入密码" 
                placeholder-class="input-placeholder"
              />
            </view>
          </uni-forms-item>

          <view class="forgot-pwd-row">
            <text class="forgot-text" @tap="goToReset">忘记密码？</text>
          </view>

          <button class="primary-btn" @tap="handleLogin">登 录</button>
        </uni-forms>

        <!-- 底部注册指引 -->
        <view class="register-guide">
          <text class="guide-text">还没有账号？</text>
          <text class="guide-link" @tap="goToRegister">立即注册</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { ref, reactive } from 'vue';
import { authAPI } from '@/api';

export default {
  setup() {
    const form = ref(null);
    const loginForm = reactive({
      username: '',
      password: ''
    });
    
    const rules = reactive({
      username: {
        rules: [{
          required: true,
          errorMessage: '请输入用户名'
        }]
      },
      password: {
        rules: [{
          required: true,
          errorMessage: '请输入密码'
        }]
      }
    });
    
    const handleLogin = async () => {
      try {
        // 表单验证
        if (!loginForm.username || !loginForm.password) {
          uni.showToast({
            title: '请输入用户名和密码',
            icon: 'none'
          });
          return;
        }

        // 显示加载提示
        uni.showLoading({
          title: '登录中...'
        });

        // 调用登录接口
        const res = await authAPI.login(loginForm);
        //console.log('响应:', res);
        if (!res.success) {
          uni.hideLoading();
          uni.showToast({
            title: res.message || '账号或密码错误',
            icon: 'none'
          });
          return;
        }
        
        // 保存用户信息到本地存储
        const profile = res.data.profile || {};
        const userData = {
          username: res.data.username || loginForm.username,
          email: res.data.email || '',
          avatar: '/static/default-avatar.png'
        };
        // 注意这里：后端返回的 token 字段名叫 access_token，而不是 token
        // 根据 backend/routes/auth.py 中的代码： 'access_token': access_token
        uni.setStorageSync('user', JSON.stringify(userData));
        uni.setStorageSync('token', res.data.access_token);
        
        // 隐藏加载提示
        uni.hideLoading();
        
        // 显示成功提示
        uni.showToast({
          title: '登录成功',
          icon: 'success'
        });
        
        // 跳转到首页
        uni.reLaunch({
          url: '/pages/home/home'
        });
      } catch (error) {
        uni.hideLoading();
        uni.showToast({
          title: error.message || '登录失败',
          icon: 'none'
        });
      }
    };
    
    const goToRegister = () => {
      uni.navigateTo({
        url: '/pages/register/register',
        success: () => {
          console.log('成功跳转到注册页面');
        },
        fail: (err) => {
          console.error('跳转注册页面失败:', err);
          // 如果直接导航失败，尝试使用reLaunch
          uni.reLaunch({
            url: '/pages/register/register',
            fail: (err2) => {
              console.error('注册页面reLaunch也失败:', err2);
              uni.showToast({
                title: '页面跳转失败',
                icon: 'none'
              });
            }
          });
        }
      });
    };
    
    const goToReset = () => {
      uni.showLoading({
        title: '加载中...'
      });
      
      uni.reLaunch({
        url: '/pages/reset/reset',
        success: () => {
          console.log('成功跳转到重置密码页面');
          uni.hideLoading();
        },
        fail: (err) => {
          console.error('跳转重置密码页面失败:', err);
          uni.hideLoading();
          uni.showToast({
            title: '页面跳转失败',
            icon: 'none'
          });
        }
      });
    };
    
    return {
      form,
      loginForm,
      rules,
      handleLogin,
      goToRegister,
      goToReset
    };
  }
};
</script>

<style lang="scss">
.login-container {
  min-height: 100vh;
  position: relative;
  background-color: #F5F7FA;
  overflow: hidden;
  display: flex;
  justify-content: center;
  align-items: center;
}

/* 背景装饰图形 */
.bg-shape {
  position: absolute;
  border-radius: 50%;
  filter: blur(60px);
  z-index: 0;
}
.shape-1 {
  width: 300px;
  height: 300px;
  background: rgba(92, 107, 192, 0.15);
  top: -100px;
  right: -50px;
}
.shape-2 {
  width: 250px;
  height: 250px;
  background: rgba(255, 183, 77, 0.15);
  bottom: -50px;
  left: -80px;
}

.login-content {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 420px;
  padding: 0 24px;
  box-sizing: border-box;
}

.header-section {
  text-align: center;
  margin-bottom: 40px;
}

.logo-box {
  width: 80px;
  height: 80px;
  margin: 0 auto 20px;
  background: #fff;
  border-radius: 24px;
  box-shadow: 0 8px 24px rgba(92, 107, 192, 0.15);
  display: flex;
  justify-content: center;
  align-items: center;
  overflow: hidden;
}

.logo-img {
  width: 100%;
  height: 100%;
  transform: scale(1.18);
}

.main-title {
  display: block;
  font-size: 28px;
  font-weight: 800;
  color: #2C3E50;
  margin-bottom: 10px;
  letter-spacing: 1px;
}

.sub-title {
  display: block;
  font-size: 15px;
  color: #7F8C8D;
  letter-spacing: 0.5px;
}

.form-card {
  background: #FFFFFF;
  border-radius: 24px;
  padding: 32px 24px;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.05);
}

.custom-input-group {
  display: flex;
  align-items: center;
  background-color: #F8F9FA;
  border-radius: 16px;
  padding: 0 16px;
  height: 56px;
  border: 2px solid transparent;
  transition: all 0.3s ease;

  &:focus-within {
    background-color: #FFFFFF;
    border-color: #5C6BC0;
    box-shadow: 0 4px 12px rgba(92, 107, 192, 0.1);
  }
}

.input-icon {
  margin-right: 12px;
  display: flex;
  align-items: center;
}

.custom-input {
  flex: 1;
  height: 100%;
  font-size: 16px;
  color: #2C3E50;
  background: transparent;
  border: none;
  outline: none;
}

.input-placeholder {
  color: #AAB7C4;
  font-size: 15px;
}

.forgot-pwd-row {
  display: flex;
  justify-content: flex-end;
  margin-top: -8px;
  margin-bottom: 24px;
}

.forgot-text {
  font-size: 14px;
  color: #95A5A6;
  padding: 4px;
  
  &:active {
    opacity: 0.7;
  }
}

.primary-btn {
  width: 100%;
  height: 56px;
  line-height: 56px;
  background: linear-gradient(135deg, #5C6BC0 0%, #3F51B5 100%);
  color: #FFFFFF;
  border-radius: 28px;
  font-size: 18px;
  font-weight: 600;
  border: none;
  box-shadow: 0 8px 20px rgba(63, 81, 181, 0.3);
  transition: all 0.3s ease;
  
  &:active {
    transform: scale(0.98);
    box-shadow: 0 4px 12px rgba(63, 81, 181, 0.2);
  }
}

.register-guide {
  display: flex;
  justify-content: center;
  align-items: center;
  margin-top: 24px;
}

.guide-text {
  font-size: 14px;
  color: #7F8C8D;
}

.guide-link {
  font-size: 14px;
  color: #5C6BC0;
  font-weight: 600;
  margin-left: 8px;
  padding: 4px;
  
  &:active {
    opacity: 0.7;
  }
}

:deep(.uni-forms-item) {
  margin-bottom: 20px;
}

:deep(.uni-forms-item__label) {
  display: none !important;
}

/* 响应式平板适配 */
@media screen and (min-width: 768px) {
  .login-content {
    max-width: 480px;
  }
  .form-card {
    padding: 40px 32px;
  }
}

/* 暗黑模式适配 */
@media (prefers-color-scheme: dark) {
  .login-container {
    background-color: #121212;
  }
  .form-card {
    background-color: #1E1E1E;
    box-shadow: 0 12px 32px rgba(0, 0, 0, 0.4);
  }
  .main-title {
    color: #FFFFFF;
  }
  .sub-title {
    color: #A0AAB7;
  }
  .custom-input-group {
    background-color: #2A2A2A;
    
    &:focus-within {
      background-color: #1E1E1E;
      border-color: #7986CB;
    }
  }
  .custom-input {
    color: #FFFFFF;
  }
  .input-placeholder {
    color: #6C7A89;
  }
  .logo-box {
    background: #1E1E1E;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
  }
}
</style> 
