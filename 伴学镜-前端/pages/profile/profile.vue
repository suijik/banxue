<template>
  <view class="profile-page">
    <scroll-view scroll-y class="profile-scroll">
      <view class="hero-section">
        <view class="hero-bg hero-bg-1"></view>
        <view class="hero-bg hero-bg-2"></view>

        <view class="top-bar">
          <view class="back-btn" @tap="goBack">
            <uni-icons type="left" size="20" color="#FFFFFF"></uni-icons>
          </view>
          <text class="page-title">个人中心</text>
          <view class="placeholder"></view>
        </view>

        <view class="profile-card">
          <image class="avatar" src="/static/default-avatar.png" mode="aspectFill"></image>
          <view class="profile-main">
            <text class="username">{{ profile.username || '同学' }}</text>
            <text class="subtitle">已陪伴学习 {{ profile.learning_days }} 天</text>
            <text class="email">{{ profile.email || '暂未绑定邮箱' }}</text>
          </view>
        </view>

        <view class="hero-stats">
          <view class="hero-stat">
            <text class="hero-num">{{ profile.stats.exam_count }}</text>
            <text class="hero-label">批改试卷</text>
          </view>
          <view class="hero-divider"></view>
          <view class="hero-stat">
            <text class="hero-num">{{ profile.stats.mistake_count }}</text>
            <text class="hero-label">累计错题</text>
          </view>
          <view class="hero-divider"></view>
          <view class="hero-stat">
            <text class="hero-num">{{ profile.stats.mastered_count }}</text>
            <text class="hero-label">掌握提升</text>
          </view>
        </view>
      </view>

      <view class="content">
        <view class="section-card">
          <view class="section-title-row">
            <text class="section-title">学习概览</text>
            <text class="section-tip">记录每一点成长</text>
          </view>
          <view class="overview-grid">
            <view class="overview-item blue">
              <text class="overview-num">{{ profile.learning_days }}</text>
              <text class="overview-label">使用天数</text>
            </view>
            <view class="overview-item orange">
              <text class="overview-num">{{ profile.stats.exam_count }}</text>
              <text class="overview-label">批改试卷</text>
            </view>
            <view class="overview-item green">
              <text class="overview-num">{{ profile.stats.mistake_count }}</text>
              <text class="overview-label">累计错题</text>
            </view>
            <view class="overview-item purple">
              <text class="overview-num">{{ profile.stats.mastered_count }}</text>
              <text class="overview-label">已掌握题目</text>
            </view>
          </view>
        </view>
      </view>
    </scroll-view>
    <view class="logout-bar">
      <button class="logout-btn" @tap="handleLogout">退出登录</button>
    </view>
  </view>
</template>

<script>
import { authAPI } from '@/api';

const defaultProfile = () => ({
  username: '',
  email: '',
  avatar: '/static/default-avatar.png',
  created_at: '',
  created_at_label: '',
  learning_days: 1,
  stats: {
    exam_count: 0,
    mistake_count: 0,
    mastered_count: 0,
    knowledge_point_count: 0,
    practice_count: 0,
    subject_count: 0
  }
});

export default {
  data() {
    return {
      profile: defaultProfile()
    };
  },
  onShow() {
    this.fetchProfile();
  },
  methods: {
    getStoredUser() {
      const user = uni.getStorageSync('user');
      if (!user) {
        return null;
      }

      if (typeof user === 'string') {
        try {
          return JSON.parse(user);
        } catch (error) {
          return null;
        }
      }

      return user;
    },
    syncLocalUser(profile) {
      const localUser = {
        username: profile.username || '',
        email: profile.email || '',
        avatar: '/static/default-avatar.png'
      };
      uni.setStorageSync('user', JSON.stringify(localUser));
    },
    async fetchProfile() {
      const localUser = this.getStoredUser();
      if (localUser) {
        this.profile = {
          ...defaultProfile(),
          ...this.profile,
          username: localUser.username || this.profile.username,
          email: localUser.email || this.profile.email,
          avatar: '/static/default-avatar.png'
        };
      }

      try {
        const res = await authAPI.getUserInfo();
        if (res.success && res.data) {
          this.profile = {
            ...defaultProfile(),
            ...res.data,
            stats: {
              ...defaultProfile().stats,
              ...(res.data.stats || {})
            }
          };
          this.syncLocalUser(this.profile);
        }
      } catch (error) {
        console.error('获取个人中心信息失败', error);
      }
    },
    async handleLogout() {
      uni.showModal({
        title: '退出登录',
        content: '退出后将返回登录页，确定继续吗？',
        confirmColor: '#E57373',
        success: async (res) => {
          if (!res.confirm) {
            return;
          }

          try {
            await authAPI.logout();
          } catch (error) {
            console.error('退出登录接口调用失败', error);
          }

          uni.removeStorageSync('token');
          uni.removeStorageSync('user');
          uni.reLaunch({ url: '/pages/login/login' });
        }
      });
    },
    goBack() {
      const pages = getCurrentPages();
      if (pages.length > 1) {
        uni.navigateBack();
      } else {
        uni.reLaunch({ url: '/pages/home/home' });
      }
    }
  }
};
</script>

<style lang="scss" scoped>
.profile-page {
  height: 100vh;
  background: #f5f7fb;
  display: flex;
  flex-direction: column;
}

.profile-scroll {
  flex: 1;
}

.hero-section {
  position: relative;
  overflow: hidden;
  padding: 48px 18px 24px;
  background: linear-gradient(135deg, #4a5fd1 0%, #6f7ce8 100%);
  border-radius: 0 0 28px 28px;
}

.hero-bg {
  position: absolute;
  border-radius: 50%;
  filter: blur(42px);
  opacity: 0.6;
}

.hero-bg-1 {
  width: 180px;
  height: 180px;
  top: -40px;
  right: -40px;
  background: rgba(255, 255, 255, 0.22);
}

.hero-bg-2 {
  width: 140px;
  height: 140px;
  left: -20px;
  bottom: -30px;
  background: rgba(255, 255, 255, 0.16);
}

.top-bar {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.back-btn,
.placeholder {
  width: 32px;
  height: 32px;
}

.back-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.14);
}

.page-title {
  font-size: 17px;
  font-weight: 700;
  color: #ffffff;
}

.profile-card {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  margin-bottom: 18px;
}

.avatar {
  width: 74px;
  height: 74px;
  border-radius: 37px;
  border: 3px solid rgba(255, 255, 255, 0.22);
  background: #ffffff;
  margin-right: 14px;
}

.profile-main {
  display: flex;
  flex-direction: column;
}

.username {
  font-size: 22px;
  font-weight: 700;
  color: #ffffff;
  margin-bottom: 4px;
}

.subtitle,
.email {
  color: rgba(255, 255, 255, 0.9);
}

.subtitle {
  font-size: 13px;
  margin-bottom: 4px;
}

.email {
  font-size: 12px;
}

.hero-stats {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  padding: 16px 12px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.12);
  backdrop-filter: blur(8px);
}

.hero-stat {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.hero-num {
  font-size: 22px;
  font-weight: 700;
  color: #ffffff;
  margin-bottom: 4px;
}

.hero-label {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.9);
}

.hero-divider {
  width: 1px;
  height: 28px;
  background: rgba(255, 255, 255, 0.22);
}

.content {
  padding: 16px 16px 110px;
}

.section-card {
  background: #ffffff;
  border-radius: 18px;
  padding: 16px;
  margin-bottom: 14px;
  box-shadow: 0 6px 24px rgba(31, 45, 61, 0.05);
}

.section-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}

.section-title {
  font-size: 16px;
  font-weight: 700;
  color: #25324b;
}

.section-tip {
  font-size: 11px;
  color: #97a1b5;
}

.overview-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.overview-item {
  border-radius: 16px;
  padding: 16px 14px;
  color: #ffffff;
}

.overview-item.blue {
  background: linear-gradient(135deg, #4e8ef7 0%, #3b6de8 100%);
}

.overview-item.orange {
  background: linear-gradient(135deg, #ffb258 0%, #ff8c37 100%);
}

.overview-item.green {
  background: linear-gradient(135deg, #56c88c 0%, #2ea86f 100%);
}

.overview-item.purple {
  background: linear-gradient(135deg, #8f79ff 0%, #6d5cf3 100%);
}

.overview-num {
  display: block;
  font-size: 22px;
  font-weight: 700;
  margin-bottom: 6px;
}

.overview-label {
  font-size: 12px;
  opacity: 0.92;
}

.logout-btn {
  height: 48px;
  line-height: 48px;
  border-radius: 24px;
  border: none;
  color: #ffffff;
  font-size: 16px;
  font-weight: 600;
  background: linear-gradient(135deg, #ff7d72 0%, #f05b59 100%);
  box-shadow: 0 10px 20px rgba(240, 91, 89, 0.2);
}

.logout-bar {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  padding: 12px 16px 20px;
  background: linear-gradient(180deg, rgba(245, 247, 251, 0) 0%, rgba(245, 247, 251, 0.96) 30%, #f5f7fb 100%);
}
</style>
