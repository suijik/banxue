<template>
  <view class="reset-container">
    <view class="reset-header">
      <view class="back-btn" @click="goToLogin">
        <uni-icons type="left" size="24" color="#5C6BC0"></uni-icons>
      </view>
      <view class="logo-box">
        <image class="logo" src="/static/logo.png" mode="aspectFill"></image>
      </view>
      <text class="title">重置密码</text>
      <text class="subtitle">别担心，我们帮您找回</text>
    </view>
    
    <view class="reset-box">
      <uni-forms ref="form" :model="resetForm" :rules="rules" validateTrigger="submit">
        <view class="form-desc" v-if="stepIndex === 0">请输入您的注册邮箱，我们将向您发送验证码</view>
        <view class="form-desc" v-else-if="stepIndex === 1">已向您的邮箱发送验证码，请查收</view>
        <view class="form-desc" v-else>请输入您的新密码</view>
        
        <template v-if="stepIndex === 0 || stepIndex === 1">
          <uni-forms-item name="email">
            <view class="input-wrapper">
              <uni-easyinput 
                v-model="resetForm.email" 
                placeholder="请输入注册邮箱"
                prefixIcon="email"
                @blur="validateEmail"
                :inputBorder="false"
                :disabled="stepIndex > 0"
              />
            </view>
          </uni-forms-item>
        </template>
        
        <template v-if="stepIndex === 1">
          <uni-forms-item name="code">
            <view class="input-wrapper code-wrapper">
              <uni-easyinput 
                v-model="resetForm.code" 
                placeholder="请输入验证码"
                prefixIcon="locked"
                maxlength="6"
                :inputBorder="false"
              >
                <template v-slot:right>
                  <button 
                    class="code-btn" 
                    :disabled="isCodeSent || !isEmailValid"
                    @tap="sendCode"
                  >
                    {{ isCodeSent ? `${countdown}s` : '获取验证码' }}
                  </button>
                </template>
              </uni-easyinput>
            </view>
          </uni-forms-item>
        </template>
        
        <template v-if="stepIndex >= 2">
          <uni-forms-item name="password">
            <view class="input-wrapper">
              <uni-easyinput 
                v-model="resetForm.password" 
                type="password"
                placeholder="请输入新密码（至少8位）"
                prefixIcon="locked"
                :inputBorder="false"
              />
            </view>
          </uni-forms-item>
          
          <view class="password-strength" v-if="resetForm.password">
            <text class="strength-label">密码强度</text>
            <view class="strength-bar">
              <view 
                class="strength-progress" 
                :style="{width: passwordStrengthPercent + '%'}"
                :class="passwordStrengthClass"
              ></view>
            </view>
            <text class="strength-text" :class="passwordStrengthClass">{{passwordStrengthText}}</text>
          </view>
          
          <uni-forms-item name="confirmPassword">
            <view class="input-wrapper">
              <uni-easyinput 
                v-model="resetForm.confirmPassword" 
                type="password"
                placeholder="请确认新密码"
                prefixIcon="locked"
                :inputBorder="false"
              />
            </view>
          </uni-forms-item>
        </template>
        
        <view class="buttons-container">
          <template v-if="stepIndex === 0">
            <button class="primary-btn" @tap="goToStep(1)">下 一 步</button>
          </template>
          
          <template v-else-if="stepIndex === 1">
            <button class="secondary-btn" @tap="goToStep(0)">上 一 步</button>
            <button class="primary-btn" @tap="verifyCode">下 一 步</button>
          </template>
          
          <template v-else>
            <button class="secondary-btn" @tap="goToStep(1)">上 一 步</button>
            <button class="primary-btn" @tap="handleReset">重 置 密 码</button>
          </template>
        </view>
      </uni-forms>
    </view>
  </view>
</template>

<script>
import { ref, reactive, computed } from 'vue';
import { authAPI } from '@/api';

export default {
  setup() {
    const form = ref(null);
    const resetForm = reactive({
      email: '',
      code: '',
      password: '',
      confirmPassword: ''
    });
    
    const stepIndex = ref(0);
    const isCodeSent = ref(false);
    const countdown = ref(60);
    const isEmailValid = ref(false);
    const isCodeVerified = ref(false);
    
    // 密码强度计算
    const passwordStrength = computed(() => {
      if (!resetForm.password) return 0;
      
      let score = 0;
      // 长度得分
      if (resetForm.password.length >= 8) score += 1;
      if (resetForm.password.length >= 12) score += 1;
      
      // 复杂度得分
      if (/[A-Z]/.test(resetForm.password)) score += 1; // 大写字母
      if (/[a-z]/.test(resetForm.password)) score += 1; // 小写字母
      if (/[0-9]/.test(resetForm.password)) score += 1; // 数字
      if (/[^A-Za-z0-9]/.test(resetForm.password)) score += 1; // 特殊字符
      
      return score;
    });
    
    const passwordStrengthPercent = computed(() => {
      return (passwordStrength.value / 6) * 100;
    });
    
    const passwordStrengthClass = computed(() => {
      if (passwordStrength.value <= 2) return 'weak';
      if (passwordStrength.value <= 4) return 'medium';
      return 'strong';
    });
    
    const passwordStrengthText = computed(() => {
      if (passwordStrength.value <= 2) return '弱';
      if (passwordStrength.value <= 4) return '中';
      return '强';
    });
    
    const rules = reactive({
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
        }, {
          pattern: /^\d{6}$/,
          errorMessage: '验证码应为6位数字'
        }]
      },
      password: {
        rules: [{
          required: true,
          errorMessage: '请输入新密码'
        }, {
          minLength: 8,
          errorMessage: '密码长度不能小于8位'
        }]
      },
      confirmPassword: {
        rules: [{
          required: true,
          errorMessage: '请确认新密码'
        }, {
          validateFunction: function(rule, value, data, callback) {
            if (value !== resetForm.password) {
              callback('两次输入的密码不一致');
            }
            return true;
          }
        }]
      }
    });
    
    const validateEmail = () => {
      if (resetForm.email) {
        form.value.validateField('email').then(res => {
          isEmailValid.value = true;
        }).catch(err => {
          isEmailValid.value = false;
        });
      } else {
        isEmailValid.value = false;
      }
    };
    
    const goToStep = (index) => {
      if (index > stepIndex.value) {
        // 前进需要验证
        if (index === 1) {
          form.value.validateField('email').then(res => {
            stepIndex.value = index;
          }).catch(err => {
            uni.showToast({
              title: '请输入有效的邮箱',
              icon: 'none'
            });
          });
        } else if (index === 2 && !isCodeVerified.value) {
          verifyCode();
        } else {
          stepIndex.value = index;
        }
      } else {
        // 后退不需要验证
        stepIndex.value = index;
      }
    };
    
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
          
          const response = await authAPI.sendCode(resetForm.email);
          
          if (response && response.success) {
            uni.showToast({
              title: '验证码已发送',
              icon: 'success'
            });
            isCodeSent.value = true;
            startCountdown();
          } else {
            uni.showToast({
              title: response?.message || '发送失败',
              icon: 'none'
            });
          }
        } catch (error) {
          console.error('发送验证码失败:', error);
          uni.showToast({
            title: error.message || '发送失败，请检查网络连接',
            icon: 'none'
          });
        } finally {
          if (loadingShown) {
            uni.hideLoading();
          }
        }
      }).catch(err => {
        uni.showToast({
          title: '请输入有效的邮箱',
          icon: 'none'
        });
      });
    };
    
    const verifyCode = () => {
      form.value.validateField(['email', 'code']).then(async () => {
        let loadingShown = false;
        try {
          loadingShown = true;
          uni.showLoading({
            title: '验证中...',
            mask: true
          });
          
          // 这里可以添加验证码验证逻辑
          // 为演示直接设置为已验证
          isCodeVerified.value = true;
          stepIndex.value = 2;
          
          uni.hideLoading();
        } catch (error) {
          console.error('验证码验证失败:', error);
          uni.showToast({
            title: error.message || '验证失败，请重试',
            icon: 'none'
          });
        } finally {
          if (loadingShown) {
            uni.hideLoading();
          }
        }
      }).catch(err => {
        console.log('表单验证失败:', err);
        uni.showToast({
          title: '请输入正确的验证码',
          icon: 'none'
        });
      });
    };
    
    const handleReset = () => {
      if (!isCodeVerified.value) {
        uni.showToast({
          title: '请先验证验证码',
          icon: 'none'
        });
        return;
      }
      
      form.value.validate().then(async () => {
        let loadingShown = false;
        try {
          loadingShown = true;
          uni.showLoading({
            title: '提交中...',
            mask: true
          });
          
          const response = await authAPI.resetPassword({
            email: resetForm.email,
            code: resetForm.code,
            password: resetForm.password
          });
          
          if (response && response.success) {
            uni.showToast({
              title: '密码重置成功',
              icon: 'success',
              duration: 2000
            });
            
            setTimeout(() => {
              goToLogin();
            }, 2000);
          } else {
            uni.showToast({
              title: response?.message || '重置失败',
              icon: 'none'
            });
          }
        } catch (error) {
          console.error('重置密码失败:', error);
          uni.showToast({
            title: error.message || '重置失败，请检查网络连接',
            icon: 'none'
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
      const pages = getCurrentPages();
      if (pages.length > 1) {
        uni.navigateBack({
          delta: 1
        });
        return;
      }

      uni.reLaunch({
        url: '/pages/login/login'
      });
    };
    
    return {
      form,
      resetForm,
      rules,
      stepIndex,
      isCodeSent,
      countdown,
      isEmailValid,
      passwordStrength,
      passwordStrengthPercent,
      passwordStrengthClass,
      passwordStrengthText,
      validateEmail,
      sendCode,
      verifyCode,
      handleReset,
      goToLogin,
      goToStep
    };
  }
};
</script>

<style lang="scss">
.reset-container {
  position: relative;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
  background: linear-gradient(135deg, #E0EAFC 0%, #CFDEF3 100%);
  padding: 72px 20px 40px;
  box-sizing: border-box;
}

.reset-header {
  margin-top: 0;
  margin-bottom: 30px;
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
  width: 100%;
  max-width: 360px;
}

.back-btn {
  position: fixed;
  left: 16px;
  top: calc(16px + env(safe-area-inset-top));
  padding: 10px;
  z-index: 20;
  
  &:active {
    opacity: 0.7;
  }
}

.logo-box {
  width: 76px;
  height: 76px;
  margin-bottom: 12px;
  border-radius: 20px;
  overflow: hidden;
  box-shadow: 0 8px 16px rgba(92, 107, 192, 0.2);
  background: #fff;
}

.logo {
  width: 100%;
  height: 100%;
  transform: scale(1.18);
}

.title {
  font-size: 26px;
  font-weight: 800;
  color: #333;
  margin-bottom: 6px;
  letter-spacing: 2px;
}

.subtitle {
  font-size: 14px;
  color: #666;
  letter-spacing: 1px;
}

.reset-box {
  width: calc(100% - 28px);
  max-width: 360px;
  background-color: #ffffff;
  border-radius: 24px;
  padding: 30px 25px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.08);
  
  @media screen and (max-width: 480px) {
    padding: 25px 20px;
  }
  
  @media screen and (min-width: 481px) and (max-width: 1024px) {
    width: 60%;
    max-width: 420px;
    padding: 35px 30px;
  }
}

.form-desc {
  font-size: 14px;
  color: #666;
  margin-bottom: 20px;
  text-align: center;
}

.input-wrapper {
  background-color: #F5F7FA;
  border-radius: 12px;
  padding: 2px 5px;
  transition: all 0.3s ease;
  border: 1px solid transparent;

  &:focus-within {
    background-color: #fff;
    border-color: #5C6BC0;
    box-shadow: 0 0 0 3px rgba(92, 107, 192, 0.1);
  }
}

.code-wrapper {
  display: flex;
  align-items: center;
}

.code-btn {
  height: 36px;
  line-height: 36px;
  padding: 0 12px;
  font-size: 13px;
  background: #5C6BC0;
  color: #fff;
  border-radius: 8px;
  border: none;
  margin-right: 5px;
  
  &:active {
    opacity: 0.8;
  }
  
  &[disabled] {
    background: #c0c4cc;
    color: #fff;
  }
}

.buttons-container {
  display: flex;
  gap: 15px;
  margin-top: 25px;
}

.secondary-btn, .primary-btn {
  flex: 1;
  height: 48px;
  line-height: 48px;
  border-radius: 12px;
  font-size: 16px;
  font-weight: bold;
  border: none;
  transition: all 0.3s ease;
  
  &:active {
    opacity: 0.9;
    transform: scale(0.98);
  }
}

.secondary-btn {
  background-color: #F5F7FA;
  color: #666;
  
  &:active {
    background-color: #E4E7ED;
  }
}

.primary-btn {
  background: linear-gradient(135deg, #7986CB 0%, #3F51B5 100%);
  color: #fff;
  box-shadow: 0 6px 16px rgba(63, 81, 181, 0.3);
  
  &:active {
    box-shadow: 0 2px 8px rgba(63, 81, 181, 0.2);
  }
}

.password-strength {
  margin-top: -5px;
  margin-bottom: 15px;
  display: flex;
  align-items: center;
  font-size: 12px;
  color: #666;
  padding: 0 5px;
  
  .strength-label {
    margin-right: 5px;
  }

  .strength-bar {
    flex: 1;
    height: 4px;
    background-color: #E4E7ED;
    border-radius: 2px;
    margin: 0 10px;
    overflow: hidden;
  }
  
  .strength-progress {
    height: 100%;
    transition: width 0.3s ease, background-color 0.3s ease;
    
    &.weak {
      background-color: #F56C6C;
    }
    
    &.medium {
      background-color: #E6A23C;
    }
    
    &.strong {
      background-color: #67C23A;
    }
  }
  
  .strength-text {
    width: 20px;
    text-align: right;

    &.weak {
      color: #F56C6C;
    }
    
    &.medium {
      color: #E6A23C;
    }
    
    &.strong {
      color: #67C23A;
    }
  }
}

:deep(.uni-forms-item__label) {
  padding: 0 !important;
}

:deep(.uni-easyinput__content) {
  border-radius: 12px !important;
  height: 45px !important;
  background-color: transparent !important;
  
  .uni-easyinput__placeholder-class {
    font-size: 14px;
    color: #A0AAB7;
  }
  
  .uni-easyinput__content-input {
    font-size: 15px;
    color: #333;
  }
}

:deep(.uni-forms-item) {
  margin-bottom: 16px;
  
  &:last-child {
    margin-bottom: 0;
  }
}

:deep(.uni-icons) {
  color: #5C6BC0 !important;
  font-size: 20px !important;
}

@media (prefers-color-scheme: dark) {
  .reset-container {
    background: linear-gradient(135deg, #1A1A2E 0%, #16213E 100%);
  }
  .title { color: #fff; }
  .subtitle, .form-desc { color: #aaa; }
  .reset-box {
    background-color: #24243E;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
  }
  .input-wrapper {
    background-color: #1A1A2E;
    &:focus-within {
      background-color: #16213E;
      border-color: #7986CB;
    }
  }
  .secondary-btn {
    background-color: #1A1A2E;
    color: #ddd;
    &:active {
      background-color: #16213E;
    }
  }
  .password-strength .strength-bar {
    background-color: #4a4a4a;
  }
  :deep(.uni-easyinput__content-input) { color: #fff; }
}
</style> 
