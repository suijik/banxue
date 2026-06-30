<template>
  <view class="qa-container">
    <!-- 顶部导航栏 -->
    <view class="custom-navbar" :style="{ paddingTop: statusBarHeight + 'px' }">
      <view class="navbar-left" @tap="goBack">
        <uni-icons type="back" size="24" color="#fff" />
      </view>
      <view class="navbar-title-container">
        <text class="navbar-title">AI 小伴</text>
      </view>
      <view class="navbar-right"></view>
    </view>

    <!-- 聊天记录区域 -->
    <scroll-view 
      class="chat-scroll-view" 
      scroll-y 
      :scroll-top="scrollTop" 
      :scroll-with-animation="true"
      @click="hideKeyboard"
    >
      <view class="chat-list" id="chat-list">
        <view class="message-item" v-for="(msg, index) in messages" :key="index" :class="msg.role">
          <!-- AI 头像 -->
          <image v-if="msg.role === 'assistant'" class="avatar" src="/static/logo.png" mode="aspectFill"></image>
          
          <view class="message-content">
            <!-- 用户发送的图片 -->
            <image 
              v-if="msg.image" 
              class="msg-image" 
              :src="msg.image" 
              mode="widthFix" 
              @click="previewImage(msg.image)"
            ></image>
            
            <!-- 消息文本 -->
            <view v-if="msg.content" class="bubble">
              <text class="bubble-text" :user-select="true">{{ msg.content }}</text>
            </view>
          </view>
          
          <!-- 用户头像 -->
          <image v-if="msg.role === 'user'" class="avatar user-avatar" :src="userInfo.avatar || '/static/default-avatar.png'" mode="aspectFill"></image>
        </view>
        
        <!-- 加载中动画 -->
        <view class="message-item assistant" v-if="isThinking">
          <image class="avatar" src="/static/logo.png" mode="aspectFill"></image>
          <view class="message-content">
            <view class="bubble typing-bubble">
              <view class="typing-dot"></view>
              <view class="typing-dot"></view>
              <view class="typing-dot"></view>
            </view>
          </view>
        </view>
      </view>
    </scroll-view>

    <!-- 底部输入区域 -->
    <view class="input-area" :style="{ paddingBottom: safeAreaBottom + 'px' }">
      <!-- 预览选中的图片 -->
      <view class="preview-box" v-if="selectedImage">
        <image class="preview-img" :src="selectedImage" mode="aspectFill"></image>
        <view class="delete-btn" @click="removeImage">
          <uni-icons type="closeempty" size="14" color="#fff"></uni-icons>
        </view>
      </view>
      
      <view class="input-row">
        <!-- 上传图片按钮 -->
        <view class="action-btn" @click="chooseImage">
          <uni-icons type="camera" size="28" color="#666"></uni-icons>
        </view>
        
        <!-- 文本输入框 -->
        <input 
          class="chat-input" 
          type="text" 
          v-model="inputText" 
          placeholder="问点学习上的问题吧..." 
          confirm-type="send"
          @confirm="sendMessage"
          :adjust-position="true"
        />
        
        <!-- 发送按钮 -->
        <view class="send-btn" :class="{ 'active': inputText.trim() || selectedImage }" @click="sendMessage">
          <uni-icons type="paperplane-filled" size="24" :color="(inputText.trim() || selectedImage) ? '#fff' : '#999'"></uni-icons>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { qaAPI } from '@/api/index.js';

export default {
  data() {
    return {
      statusBarHeight: uni.getSystemInfoSync().statusBarHeight,
      safeAreaBottom: uni.getSystemInfoSync().safeAreaInsets?.bottom || 0,
      userInfo: {},
      inputText: '',
      selectedImage: null,
      selectedImageBase64: null,
      messages: [
        {
          role: 'assistant',
          content: '你好！我是你的AI老师小伴。如果你在学习上遇到难题，或者需要思路启发，随时可以问我哦。支持发送题目图片~'
        }
      ],
      isThinking: false,
      scrollTop: 0,
      systemInfo: uni.getSystemInfoSync()
    };
  },
  onLoad() {
    const userStr = uni.getStorageSync('user');
    if (userStr) {
      this.userInfo = JSON.parse(userStr);
    }
  },
  methods: {
    goBack() {
      uni.navigateBack({
        delta: 1,
        fail: () => {
          uni.switchTab({ url: '/pages/home/home' });
        }
      });
    },
    hideKeyboard() {
      uni.hideKeyboard();
    },
    scrollToBottom() {
      setTimeout(() => {
        const query = uni.createSelectorQuery().in(this);
        query.select('#chat-list').boundingClientRect(res => {
          if (res) {
            this.scrollTop = res.height + 100;
          }
        }).exec();
      }, 100);
    },
    chooseImage() {
      uni.chooseImage({
        count: 1,
        sizeType: ['compressed'],
        sourceType: ['album', 'camera'],
        success: (res) => {
          this.selectedImage = res.tempFilePaths[0];
          // 转base64
          uni.getFileSystemManager().readFile({
            filePath: this.selectedImage,
            encoding: 'base64',
            success: (data) => {
              this.selectedImageBase64 = 'data:image/jpeg;base64,' + data.data;
            }
          });
        }
      });
    },
    removeImage() {
      this.selectedImage = null;
      this.selectedImageBase64 = null;
    },
    previewImage(url) {
      uni.previewImage({
        urls: [url]
      });
    },
    async sendMessage() {
      if (!this.inputText.trim() && !this.selectedImage) return;
      if (this.isThinking) return;
      
      const userContent = this.inputText.trim();
      const userImage = this.selectedImage;
      const userImageBase64 = this.selectedImageBase64;
      
      // 添加用户消息到列表
      this.messages.push({
        role: 'user',
        content: userContent,
        image: userImage
      });
      
      // 清空输入框
      this.inputText = '';
      this.removeImage();
      this.scrollToBottom();
      
      this.isThinking = true;
      this.scrollToBottom();
      
      try {
        // 构造要发送给后端的历史记录，只传纯文本用于上下文
        const apiMessages = this.messages.map(m => ({
          role: m.role,
          content: m.content || (m.image ? "[用户发送了一张图片]" : "")
        }));
        
        const res = await qaAPI.chat({
          messages: apiMessages,
          image_base64: userImageBase64
        });
        
        if (res.success) {
          this.messages.push({
            role: 'assistant',
            content: res.data.reply
          });
        } else {
          this.messages.push({
            role: 'assistant',
            content: '抱歉，我遇到了一点小问题，请稍后再试。'
          });
        }
      } catch (err) {
        console.error('聊天失败:', err);
        this.messages.push({
          role: 'assistant',
          content: '网络似乎出了点问题，没能收到你的消息呢。'
        });
      } finally {
        this.isThinking = false;
        this.scrollToBottom();
      }
    }
  }
};
</script>

<style lang="scss" scoped>
view, text, scroll-view, image {
  box-sizing: border-box;
}

.qa-container {
  height: 100vh;
  width: 100vw;
  background-color: #F5F7FA;
  display: flex;
  flex-direction: column;
}

/* 顶部导航 */
.custom-navbar {
  position: relative;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  height: 54px;
  box-sizing: content-box;
  background: linear-gradient(135deg, #3F51B5 0%, #5C6BC0 100%);
  
  .navbar-left {
    width: 40px;
    height: 100%;
    display: flex;
    align-items: center;
  }
  .navbar-title-container {
    flex: 1;
    text-align: center;
    .navbar-title {
      font-size: 17px;
      font-weight: bold;
      color: #fff;
    }
  }
  .navbar-right {
    width: 40px;
  }
}

.chat-scroll-view {
  flex: 1;
  width: 100%;
  padding: 16px;
  height: 0;
}

.chat-list {
  padding-bottom: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.message-item {
  display: flex;
  align-items: flex-start;
  max-width: 90%;
  
  &.assistant {
    align-self: flex-start;
    .message-content {
      align-items: flex-start;
    }
    .bubble {
      background-color: #fff;
      color: #333;
      border-radius: 0 16px 16px 16px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
  }
  
  &.user {
    align-self: flex-end;
    flex-direction: row;
    .message-content {
      align-items: flex-end;
    }
    .bubble {
      background: linear-gradient(135deg, #5C6BC0 0%, #3F51B5 100%);
      color: #fff;
      border-radius: 16px 0 16px 16px;
      box-shadow: 0 2px 8px rgba(63,81,181,0.2);
    }
  }
}

.avatar {
  width: 36px;
  height: 36px;
  border-radius: 18px;
  flex-shrink: 0;
  
  &.user-avatar {
    margin-left: 12px;
  }
  &:not(.user-avatar) {
    margin-right: 12px;
  }
}

.message-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.msg-image {
  max-width: 200px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.bubble {
  padding: 12px 16px;
  max-width: 100%;
  word-break: break-all;
  
  .bubble-text {
    font-size: 15px;
    line-height: 1.5;
  }
}

/* 输入区域 */
.input-area {
  background-color: #fff;
  border-top: 1px solid #EEE;
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  z-index: 100;
  
  .preview-box {
    position: relative;
    width: 60px;
    height: 60px;
    margin-bottom: 10px;
    
    .preview-img {
      width: 100%;
      height: 100%;
      border-radius: 8px;
    }
    
    .delete-btn {
      position: absolute;
      top: -6px;
      right: -6px;
      width: 20px;
      height: 20px;
      border-radius: 10px;
      background-color: rgba(0,0,0,0.6);
      display: flex;
      align-items: center;
      justify-content: center;
    }
  }
  
  .input-row {
    display: flex;
    align-items: center;
    gap: 12px;
    
    .action-btn {
      padding: 4px;
    }
    
    .chat-input {
      flex: 1;
      height: 40px;
      background-color: #F5F7FA;
      border-radius: 20px;
      padding: 0 16px;
      font-size: 14px;
    }
    
    .send-btn {
      width: 40px;
      height: 40px;
      border-radius: 20px;
      background-color: #E0E0E0;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: background-color 0.2s;
      
      &.active {
        background-color: #3F51B5;
      }
    }
  }
}

/* 正在输入动画 */
.typing-bubble {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 14px 18px !important;
  height: 44px;
  
  .typing-dot {
    width: 6px;
    height: 6px;
    background-color: #999;
    border-radius: 50%;
    animation: typing 1.4s infinite ease-in-out both;
    
    &:nth-child(1) { animation-delay: -0.32s; }
    &:nth-child(2) { animation-delay: -0.16s; }
  }
}

@keyframes typing {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}
</style>
