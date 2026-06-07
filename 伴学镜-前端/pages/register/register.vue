<template>
  <view class="register-container">
    <!-- 背景装饰 -->
    <view class="bg-shape shape-1"></view>
    <view class="bg-shape shape-2"></view>

    <view class="register-content">
      <!-- 头部区域 -->
      <view class="header-section">
        <view class="logo-box">
          <image class="logo-img" src="/static/logo.png" mode="aspectFill"></image>
        </view>
        <text class="main-title">加入伴学镜</text>
        <text class="sub-title">开启智能辅导新体验</text>
      </view>

      <!-- 注册表单卡片 -->
      <view class="form-card">
        <uni-forms ref="form" :model="registerForm" :rules="rules">
          <uni-forms-item name="username">
            <view class="custom-input-group">
              <view class="input-icon">
                <uni-icons type="person-filled" size="22" color="#5C6BC0"></uni-icons>
              </view>
              <input 
                class="custom-input" 
                v-model="registerForm.username" 
                placeholder="请输入用户名" 
                placeholder-class="input-placeholder"
              />
            </view>
          </uni-forms-item>
          
          <uni-forms-item name="email">
            <view class="custom-input-group">
              <view class="input-icon">
                <uni-icons type="email-filled" size="22" color="#5C6BC0"></uni-icons>
              </view>
              <input 
                class="custom-input" 
                v-model="registerForm.email" 
                placeholder="请输入邮箱" 
                placeholder-class="input-placeholder"
              />
            </view>
          </uni-forms-item>
          
          <uni-forms-item name="code">
            <view class="custom-input-group code-group">
              <view class="input-icon">
                <uni-icons type="locked-filled" size="22" color="#5C6BC0"></uni-icons>
              </view>
              <input 
                class="custom-input" 
                v-model="registerForm.code" 
                placeholder="请输入验证码" 
                placeholder-class="input-placeholder"
              />
              <button 
                class="code-btn" 
                :disabled="isCodeSent"
                @click="sendCode"
              >
                {{ isCodeSent ? `${countdown}s` : '获取验证码' }}
              </button>
            </view>
          </uni-forms-item>
          
          <uni-forms-item name="password">
            <view class="custom-input-group">
              <view class="input-icon">
                <uni-icons type="locked-filled" size="22" color="#5C6BC0"></uni-icons>
              </view>
              <input 
                class="custom-input" 
                v-model="registerForm.password" 
                type="password" 
                placeholder="请输入密码" 
                placeholder-class="input-placeholder"
              />
            </view>
          </uni-forms-item>
          
          <uni-forms-item name="confirmPassword">
            <view class="custom-input-group">
              <view class="input-icon">
                <uni-icons type="locked-filled" size="22" color="#5C6BC0"></uni-icons>
              </view>
              <input 
                class="custom-input" 
                v-model="registerForm.confirmPassword" 
                type="password" 
                placeholder="请确认密码" 
                placeholder-class="input-placeholder"
              />
            </view>
          </uni-forms-item>
          
          <button class="primary-btn" @click="handleRegister">注 册</button>
        </uni-forms>

        <!-- 底部登录指引 -->
        <view class="login-guide">
          <text class="guide-text">已有账号？</text>
          <text class="guide-link" @click="goToLogin">去登录</text>
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
    const registerForm = reactive({
      username: '',
      email: '',
      code: '',
      password: '',
      confirmPassword: ''
    });
    
    const isCodeSent = ref(false);
    const countdown = ref(60);
    
    const validateUsername = (rule, value, callback) => {
      const pattern = /^[A-Za-z][A-Za-z0-9]*$/;
      if (!pattern.test(value)) {
        callback('用户名只能由大小写字母和数字组成，且必须以字母开头');
      }
      return true;
    };
    
    const rules = reactive({
      username: {
        rules: [{
          required: true,
          errorMessage: '请输入用户名'
        }, {
          validateFunction: validateUsername
        }]
      },
      email: {
        rules: [{
          required: true,
          errorMessage: '请输入邮箱'
        }, {
          format: 'email',
          errorMessage: '邮箱格式不正确'
        }]
      },
      code: {
        rules: [{
          required: true,
          errorMessage: '请输入验证码'
        }]
      },
      password: {
        rules: [{
          required: true,
          errorMessage: '请输入密码'
        }, {
          minLength: 8,
          errorMessage: '密码长度不能小于8位'
        }]
      },
      confirmPassword: {
        rules: [{
          required: true,
          errorMessage: '请确认密码'
        }, {
          validateFunction: function(rule, value, data, callback) {
            if (value !== registerForm.password) {
              callback('两次输入的密码不一致');
            }
            return true;
          }
        }]
      }
    });
    
    const startCountdown = () => {
      const timer = setInterval(() => {
        if (countdown.value > 0) {
          countdown.value--;
        } else {
          clearInterval(timer);
          isCodeSent.value = false;
          countdown.value = 60;
        }
      }, 1000);
    };
    
    const sendCode = () => {
      form.value.validateField('email').then(async () => {
        let loadingShown = false;
        try {
          loadingShown = true;
          uni.showLoading({
            title: '发送中...',
            mask: true
          });
          
          const response = await authAPI.sendCode(registerForm.email);
          console.log('响应',response);
          
          if (response.success) {
            uni.showToast({
              title: '验证码已发送',
              icon: 'success'
            });
            isCodeSent.value = true;
            startCountdown();
          } else {
            uni.showToast({
              title: response.message || '发送失败',
              icon: 'none'
            });
          }
        } catch (error) {
          console.error('发送验证码失败:', error);
          const errorMessage = error.response?.data.message || '发送失败，请检查网络连接';
          uni.showToast({
            title: errorMessage,
            icon: 'none'
          });
        } finally {
          if (loadingShown) {
            uni.hideLoading();
          }
        }
      }).catch(err => {
        console.log('邮箱验证失败:', err);
      });
    };
    
    const handleRegister = () => {
      form.value.validate().then(async () => {
        let loadingShown = false;
        try {
          loadingShown = true;
          uni.showLoading({
            title: '注册中...',
            mask: true
          });
          
          const response = await authAPI.register(registerForm);
          
          if (response.success) {
            uni.showToast({
              title: '注册成功',
              icon: 'success',
              duration: 2000
            });
            
            setTimeout(() => {
              uni.navigateBack();
            }, 2000);
          } else {
            uni.showToast({
              title: response.message || '注册失败',
              icon: 'none',
              duration: 2000
            });
          }
        } catch (error) {
          console.error('注册失败:', error);
          const errorMessage = error.response?.data?.message || '注册失败，请检查网络连接';
          uni.showToast({
            title: errorMessage,
            icon: 'none',
            duration: 2000
          });
        } finally {
          if (loadingShown) {
            uni.hideLoading();
          }
        }
      }).catch(err => {
        console.log('表单验证失败:', err);
      });
    };
    
    const goToLogin = () => {
      uni.navigateBack();
    };
    
    return {
      form,
      registerForm,
      rules,
      isCodeSent,
      countdown,
      sendCode,
      handleRegister,
      goToLogin
    };
  }
};
</script>

<style lang="scss">
.register-container {
  min-height: 100vh;
  position: relative;
  background-color: #F5F7FA;
  overflow: hidden;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 40px 0;
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
  top: -50px;
  right: -50px;
}
.shape-2 {
  width: 250px;
  height: 250px;
  background: rgba(255, 183, 77, 0.15);
  bottom: 0px;
  left: -80px;
}

.register-content {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 420px;
  padding: 0 24px;
  box-sizing: border-box;
}

.header-section {
  text-align: center;
  margin-bottom: 30px;
}

.logo-box {
  width: 70px;
  height: 70px;
  margin: 0 auto 16px;
  background: #fff;
  border-radius: 20px;
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
  font-size: 26px;
  font-weight: 800;
  color: #2C3E50;
  margin-bottom: 8px;
  letter-spacing: 1px;
}

.sub-title {
  display: block;
  font-size: 14px;
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
  font-size: 15px;
  color: #2C3E50;
  background: transparent;
  border: none;
  outline: none;
}

.input-placeholder {
  color: #AAB7C4;
  font-size: 14px;
}

.code-group {
  padding-right: 8px;
}

.code-btn {
  height: 40px;
  line-height: 40px;
  padding: 0 16px;
  font-size: 14px;
  background: #5C6BC0;
  color: #fff;
  border-radius: 12px;
  border: none;
  margin-left: 8px;
  white-space: nowrap;
  
  &:active {
    opacity: 0.8;
  }
  
  &[disabled] {
    background: #E0E5EC;
    color: #95A5A6;
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
  margin-top: 24px;
  
  &:active {
    transform: scale(0.98);
    box-shadow: 0 4px 12px rgba(63, 81, 181, 0.2);
  }
}

.login-guide {
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
  margin-bottom: 16px;
}

:deep(.uni-forms-item__label) {
  display: none !important;
}

/* 响应式平板适配 */
@media screen and (min-width: 768px) {
  .register-content {
    max-width: 480px;
  }
  .form-card {
    padding: 40px 32px;
  }
}

/* 暗黑模式适配 */
@media (prefers-color-scheme: dark) {
  .register-container {
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
  .code-btn[disabled] {
    background: #333333;
    color: #6C7A89;
  }
}
</style> 
