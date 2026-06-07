<template>
  <view class="home-container">
    <!-- 主体功能滚动区 -->
    <scroll-view scroll-y class="main-content">
      
      <!-- 顶部背景与用户信息区域 (跟随滚动) -->
      <view class="header-section">
        <!-- 装饰性背景光晕 -->
        <view class="bg-shape shape-1"></view>
        <view class="bg-shape shape-2"></view>
        
        <!-- 用户资料与操作栏 -->
        <view class="header-top">
          <view class="user-profile" @click="navigateTo('profile')">
            <image class="avatar" src="/static/default-avatar.png" mode="aspectFill"></image>
            <view class="greeting">
              <text class="title">你好，{{ userInfo.name }}</text>
              <text class="subtitle">坚持学习第 {{ userInfo.streak }} 天</text>
            </view>
          </view>
          <!-- 移除了关闭按钮 -->
        </view>
        
        <!-- 极简数据展示，替代原先厚重的白色卡片 -->
        <view class="stats-row">
          <view class="stat-item">
            <text class="stat-num">{{ userInfo.fixedMistakes }}</text>
            <text class="stat-label">累计错题</text>
          </view>
          <view class="divider"></view>
          <view class="stat-item">
            <text class="stat-num">{{ userInfo.masteredMistakes }}</text>
            <text class="stat-label">已掌握错题</text>
          </view>
        </view>
      </view>

      <view class="content-inner">

        <!-- 金刚区：功能快捷入口 -->
        <view class="quick-nav-grid">
          <view class="nav-grid-item" @click="navigateTo('camera')">
            <view class="icon-box bg-blue">
              <uni-icons type="camera-filled" size="28" color="#fff"></uni-icons>
            </view>
            <text class="nav-text">拍照批改</text>
          </view>
          <view class="nav-grid-item" @click="navigateTo('qa')">
            <view class="icon-box bg-orange">
              <uni-icons type="chatbubble-filled" size="28" color="#fff"></uni-icons>
            </view>
            <text class="nav-text">启发答疑</text>
          </view>
          <view class="nav-grid-item" @click="navigateTo('mistakes')">
            <view class="icon-box bg-green">
              <uni-icons type="list" size="28" color="#fff"></uni-icons>
            </view>
            <text class="nav-text">错题本</text>
          </view>
          <view class="nav-grid-item" @click="navigateTo('practice')">
            <view class="icon-box bg-purple">
              <uni-icons type="star-filled" size="28" color="#fff"></uni-icons>
            </view>
            <text class="nav-text">举一反三</text>
          </view>
          <view class="nav-grid-item" @click="navigateTo('parent-tips')">
            <view class="icon-box bg-pink">
              <uni-icons type="heart-filled" size="28" color="#fff"></uni-icons>
            </view>
            <text class="nav-text">家长辅导</text>
          </view>
        </view>

        <!-- 分割线 -->
        <view class="section-divider">
          <text class="divider-text">核心功能探索</text>
        </view>

        <!-- 1. 智能工具：拍照批改与启发答疑 -->
        <view class="section-container">
          <view class="section-header">
            <text class="section-title">我的小助手</text>
            <text class="section-subtitle">哪里不会拍哪里</text>
          </view>
          
          <view class="grid-container core-tools">
            <view class="grid-item primary-card" @click="navigateTo('camera')">
              <view class="icon-circle">
                <uni-icons type="camera-filled" size="32" color="#fff"></uni-icons>
              </view>
              <view class="card-text">
                <text class="item-title">拍照批改</text>
                <text class="item-desc">一键圈出对错</text>
              </view>
              <view class="card-bg-icon">
                <uni-icons type="camera-filled" size="100" color="rgba(255,255,255,0.1)"></uni-icons>
              </view>
            </view>
            
            <view class="grid-item secondary-card" @click="navigateTo('qa')">
              <view class="icon-circle">
                <uni-icons type="chatbubble-filled" size="32" color="#fff"></uni-icons>
              </view>
              <view class="card-text">
                <text class="item-title">启发答疑</text>
                <text class="item-desc">AI老师教我思考</text>
              </view>
              <view class="card-bg-icon">
                <uni-icons type="chatbubble-filled" size="100" color="rgba(255,255,255,0.1)"></uni-icons>
              </view>
            </view>
          </view>
        </view>

        <!-- 2. 巩固练习：错题本与举一反三 -->
        <view class="section-container">
          <view class="section-header">
            <text class="section-title">进步大本营</text>
            <text class="section-subtitle">消灭错题，稳步提升</text>
          </view>
          
          <view class="list-container">
            <view class="list-item" @click="navigateTo('mistakes')">
              <view class="item-icon bg-blue">
                <uni-icons type="list" size="24" color="#fff"></uni-icons>
              </view>
              <view class="item-content">
                <text class="item-title">智能错题本</text>
                <text class="item-desc">自动整理易错知识点</text>
              </view>
              <uni-icons type="right" size="18" color="#BDBDBD"></uni-icons>
            </view>
            
            <view class="list-item" @click="navigateTo('practice')">
              <view class="item-icon bg-orange">
                <uni-icons type="star-filled" size="24" color="#fff"></uni-icons>
              </view>
              <view class="item-content">
                <text class="item-title">举一反三</text>
                <text class="item-desc">做透一类题，不盲目刷题</text>
              </view>
              <uni-icons type="right" size="18" color="#BDBDBD"></uni-icons>
            </view>
          </view>
        </view>

        <!-- 3. 家长专属：辅导建议与学习报告 -->
        <view class="section-container">
          <view class="section-header">
            <text class="section-title">家长加油站</text>
            <text class="section-subtitle">更懂孩子，更懂教育</text>
          </view>
          
          <view class="parent-section">
            <!-- 辅导话术建议 (点击进入专门的家长智囊台页面) -->
            <view class="tip-card" @click="navigateTo('parent-dashboard')">
              <view class="tip-header">
                <view class="tip-badge">
                  <uni-icons type="heart-filled" size="16" color="#E57373"></uni-icons>
                  <text class="badge-text">家长智囊台</text>
                </view>
              </view>
              <text class="tip-content">{{ parentData.ai_analysis.tutoring_advice || '加载中...' }}</text>
              <view class="tip-footer">
                <text class="tip-action">查看详细学习报告与辅导建议</text>
                <uni-icons type="arrow-right" size="14" color="#E57373"></uni-icons>
              </view>
            </view>
          </view>
        </view>

      </view>
    </scroll-view>

    <!-- 底部悬浮导航栏 -->
    <view class="floating-nav">
      <view class="nav-item active">
        <uni-icons type="home-filled" size="26" color="#3F51B5"></uni-icons>
        <text>首页</text>
      </view>
      <view class="nav-item" @click="navigateTo('practice')">
        <uni-icons type="flag" size="26" color="#BDBDBD"></uni-icons>
        <text>练习</text>
      </view>
      <view class="nav-item" @click="navigateTo('profile')">
        <uni-icons type="person" size="26" color="#BDBDBD"></uni-icons>
        <text>我的</text>
      </view>
    </view>
  </view>
</template>

<script>
import { reportAPI, authAPI } from '@/api/index.js';

export default {
  data() {
    return {
      userInfo: {
        name: '小明',
        avatar: '/static/default-avatar.png',
        streak: 1,
        fixedMistakes: 0,
        masteredMistakes: 0
      },
      // 家长辅导面板数据
      parentData: {
        report_date_range: '',
        ai_analysis: {
          tutoring_advice: '',
          summary: '',
          suggestion: ''
        }
      },
      // 雷达图数据
      radarData: {},
      radarOpts: {
        color: ["#5C6BC0"],
        padding: [10, 10, 10, 10],
        enableScroll: false,
        extra: {
          radar: {
            max: 100,
            gridType: "radar",
            gridColor: "#CCCCCC",
            labelColor: "#666666",
            opacity: 0.2
          }
        }
      },
      // 折线图数据
      lineData: {},
      lineOpts: {
        color: ["#42A5F5", "#66BB6A"],
        padding: [10, 10, 10, 10],
        enableScroll: false,
        legend: {
          show: true,
          position: "top",
          float: "right",
        },
        xAxis: {
          disableGrid: true
        },
        yAxis: {
          gridType: "dash",
          dashLength: 2,
          data: [{ min: 0, max: 100 }]
        },
        extra: {
          line: {
            type: "curve",
            width: 2
          }
        }
      }
    };
  },
  onShow() {
    this.initUserInfo();
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
    async initUserInfo() {
      const user = this.getStoredUser();
      if (user && user.username) {
        this.userInfo.name = user.username;
        this.userInfo.avatar = '/static/default-avatar.png';
        await this.fetchProfileSummary();
        this.fetchParentDashboard(user.username);
      } else {
        this.fetchParentDashboard('test');
      }
    },
    async fetchProfileSummary() {
      try {
        const res = await authAPI.getUserInfo();
        if (res.success && res.data) {
          this.userInfo.name = res.data.username || this.userInfo.name;
          this.userInfo.avatar = '/static/default-avatar.png';
          this.userInfo.streak = res.data.learning_days || this.userInfo.streak;
          this.userInfo.fixedMistakes = res.data.stats?.mistake_count ?? this.userInfo.fixedMistakes;
          this.userInfo.masteredMistakes = res.data.stats?.mastered_count ?? this.userInfo.masteredMistakes;
        }
      } catch (error) {
        console.error('获取首页个人信息失败', error);
      }
    },
    async fetchParentDashboard(username) {
      try {
        const res = await reportAPI.getParentDashboard(username);
        if (res.success) {
          const data = res.data;
          this.parentData.report_date_range = data.report_date_range;
          this.parentData.ai_analysis = data.ai_analysis;

          // 填充雷达图数据
          this.radarData = {
            categories: data.radar_chart.categories,
            series: data.radar_chart.series
          };

          // 填充折线图数据
          this.lineData = {
            categories: data.line_chart.categories,
            series: data.line_chart.series
          };
        }
      } catch (err) {
        console.error('获取家长面板数据失败', err);
      }
    },
    navigateTo(page) {
      if (page === 'profile') {
        uni.navigateTo({
          url: '/pages/profile/profile'
        });
      } else if (page === 'camera') {
        uni.navigateTo({
          url: '/pages/exam-analysis/exam-analysis'
        });
      } else if (page === 'mistakes') {
        uni.navigateTo({
          url: '/pages/mistake-book/mistake-book'
        });
      } else if (page === 'practice') {
        uni.navigateTo({
          url: '/pages/practice/practice'
        });
      } else if (page === 'qa') {
        uni.navigateTo({
          url: '/pages/qa/qa'
        });
      } else if (page === 'parent-dashboard' || page === 'parent-tips') {
        uni.navigateTo({
          url: '/pages/parent-dashboard/parent-dashboard'
        });
      } else {
        uni.showToast({ title: `功能模块 [${page}] 开发中...`, icon: 'none' });
      }
    },
    handleLogout() {
      uni.showModal({
        title: '退出登录',
        content: '确定要退出当前账号吗？',
        confirmColor: '#E57373',
        success: (res) => {
          if (res.confirm) {
            // 真实场景下清理 Storage
            // uni.clearStorageSync();
            uni.reLaunch({ url: '/pages/login/login' });
          }
        }
      });
    }
  }
};
</script>

<style lang="scss" scoped>
/* 全局修正 box-sizing 解决溢出问题 */
view, text, scroll-view, image {
  box-sizing: border-box;
}

.home-container {
  height: 100vh;
  width: 100vw;
  overflow: hidden;
  background-color: #F5F7FA;
  display: flex;
  flex-direction: column;
}

/* 顶部区域 (包裹在scroll-view中，跟随页面滚动) */
.header-section {
  position: relative;
  z-index: 1;
  background: linear-gradient(135deg, #3F51B5 0%, #5C6BC0 100%);
  /* 顶部留足安全区或状态栏高度 */
  padding: 40px 20px 20px;
  /* 减小下方圆角 */
  border-radius: 0 0 16px 16px;
  overflow: hidden;
  /* 移除 box-shadow 解决白边感 */
  margin-bottom: 0;
  
  .bg-shape {
    position: absolute;
    border-radius: 50%;
    filter: blur(40px);
    z-index: 0;
    pointer-events: none;
  }
  .shape-1 {
    width: 200px;
    height: 200px;
    background: rgba(255, 255, 255, 0.15);
    top: -50px;
    right: -50px;
  }
  .shape-2 {
    width: 150px;
    height: 150px;
    background: rgba(255, 255, 255, 0.1);
    bottom: -20px;
    left: -20px;
  }

  .header-top {
    position: relative;
    z-index: 1;
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
  }

  .user-profile {
    display: flex;
    align-items: center;
    
    .avatar {
      width: 48px;
      height: 48px;
      border-radius: 24px;
      border: 2px solid rgba(255, 255, 255, 0.4);
      background-color: #fff;
      margin-right: 12px;
    }
    
    .greeting {
      display: flex;
      flex-direction: column;
      
      .title {
        font-size: 18px;
        font-weight: bold;
        color: #FFFFFF;
        margin-bottom: 2px;
      }
      .subtitle {
        font-size: 12px;
        color: rgba(255, 255, 255, 0.85);
      }
    }
  }

  .header-actions {
    .action-btn {
      width: 32px;
      height: 32px;
      border-radius: 16px;
      background: rgba(255, 255, 255, 0.15);
      display: flex;
      align-items: center;
      justify-content: center;
      backdrop-filter: blur(4px);
      
      &:active {
        background: rgba(255, 255, 255, 0.25);
      }
    }
  }

  /* 极简透明数据行 */
  .stats-row {
    position: relative;
    z-index: 1;
    background: rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    padding: 10px 16px;
    display: flex;
    align-items: center;
    backdrop-filter: blur(8px);
    
    .stat-item {
      flex: 1;
      display: flex;
      align-items: baseline;
      justify-content: center;
      gap: 6px;
      
      .stat-num {
        font-size: 20px;
        font-weight: 800;
        color: #fff;
      }
      .stat-label {
        font-size: 11px;
        color: rgba(255, 255, 255, 0.85);
      }
    }
    
    .divider {
      width: 1px;
      height: 20px;
      background-color: rgba(255, 255, 255, 0.3);
    }
  }
}

/* 主体内容区 */
.main-content {
  flex: 1;
  width: 100vw;
  height: 0; /* 必须设置，让 scroll-view 正常工作 */
  /* 让滚动区背景为统一颜色，避免白边 */
  background-color: #F5F7FA;
}

.content-inner {
  padding: 16px 16px 100px; /* 顶部外边距减小，底部留白给悬浮导航栏 */
  width: 100%;
}

/* 金刚区 (快捷导航网格) */
.quick-nav-grid {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0 24px;
  width: 100%;
}

.nav-grid-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  flex: 1;

  .icon-box {
    width: 48px;
    height: 48px;
    border-radius: 16px;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
    
    &.bg-blue { background: linear-gradient(135deg, #42A5F5, #1E88E5); }
    &.bg-orange { background: linear-gradient(135deg, #FFB74D, #F57C00); }
    &.bg-green { background: linear-gradient(135deg, #66BB6A, #43A047); }
    &.bg-purple { background: linear-gradient(135deg, #AB47BC, #8E24AA); }
    &.bg-pink { background: linear-gradient(135deg, #EF5350, #E53935); }
  }

  .nav-text {
    font-size: 12px;
    color: #333;
    font-weight: 500;
  }
  
  &:active {
    opacity: 0.7;
  }
}

/* 分割标题 */
.section-divider {
  display: flex;
  align-items: center;
  margin-bottom: 24px;
  
  &::before, &::after {
    content: '';
    flex: 1;
    height: 1px;
    background: #EAEAEA;
  }
  
  .divider-text {
    padding: 0 16px;
    font-size: 12px;
    color: #999;
    letter-spacing: 1px;
  }
}

.section-container {
  margin-bottom: 24px;
  width: 100%;
}

.section-header {
  display: flex;
  align-items: flex-end;
  margin-bottom: 12px;
  padding: 0 4px;
  
  .section-title {
    font-size: 17px;
    font-weight: bold;
    color: #333;
    margin-right: 8px;
  }
  .section-subtitle {
    font-size: 11px;
    color: #888;
    margin-bottom: 2px;
  }
}

/* 核心工具卡片 */
.grid-container.core-tools {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  width: 100%;
  
  @media screen and (min-width: 768px) {
    grid-template-columns: 1fr 1fr;
  }
}

.grid-item {
  position: relative;
  border-radius: 16px;
  padding: 16px;
  height: 120px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
  transition: transform 0.2s ease;
  
  &:active {
    transform: scale(0.96);
  }

  .icon-circle {
    width: 40px;
    height: 40px;
    border-radius: 20px;
    background: rgba(255, 255, 255, 0.2);
    display: flex;
    align-items: center;
    justify-content: center;
    backdrop-filter: blur(4px);
  }
  
  .card-text {
    z-index: 1;
    display: flex;
    flex-direction: column;
    
    .item-title {
      font-size: 15px;
      font-weight: bold;
      color: #fff;
      margin-bottom: 2px;
    }
    .item-desc {
      font-size: 11px;
      color: rgba(255, 255, 255, 0.85);
      line-height: 1.3;
    }
  }

  .card-bg-icon {
    position: absolute;
    right: -15px;
    bottom: -15px;
    z-index: 0;
    transform: rotate(-15deg);
  }
}

.primary-card {
  background: linear-gradient(135deg, #5C6BC0 0%, #3F51B5 100%);
}

.secondary-card {
  background: linear-gradient(135deg, #42A5F5 0%, #1E88E5 100%);
}

/* 列表卡片 (巩固练习) */
.list-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
  
  @media screen and (min-width: 768px) {
    flex-direction: row;
    .list-item { flex: 1; }
  }
}

.list-item {
  background: #fff;
  border-radius: 16px;
  padding: 12px 16px;
  display: flex;
  align-items: center;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
  transition: background-color 0.2s ease;
  width: 100%;
  
  &:active {
    background-color: #F8F9FA;
  }
  
  .item-icon {
    width: 44px;
    height: 44px;
    border-radius: 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-right: 12px;
    flex-shrink: 0;
    
    &.bg-blue { background: linear-gradient(135deg, #7986CB, #5C6BC0); }
    &.bg-orange { background: linear-gradient(135deg, #FFB74D, #F57C00); }
  }
  
  .item-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    
    .item-title {
      font-size: 15px;
      font-weight: bold;
      color: #333;
      margin-bottom: 2px;
    }
    .item-desc {
      font-size: 11px;
      color: #888;
    }
  }
}

/* 家长赋能模块 */
.parent-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
  width: 100%;
  
  @media screen and (min-width: 768px) {
    flex-direction: row;
    .tip-card, .report-card { flex: 1; }
  }
}

.tip-card {
  background: linear-gradient(135deg, #FFF8F8 0%, #FFEAEA 100%);
  border-radius: 16px;
  padding: 16px;
  border: 1px solid rgba(229, 115, 115, 0.2);
  
  .tip-header {
    margin-bottom: 10px;
    .tip-badge {
      display: inline-flex;
      align-items: center;
      background: rgba(229, 115, 115, 0.1);
      padding: 4px 8px;
      border-radius: 12px;
      
      .badge-text {
        font-size: 11px;
        font-weight: bold;
        color: #E57373;
        margin-left: 4px;
      }
    }
  }
  
  .tip-content {
    font-size: 13px;
    color: #555;
    line-height: 1.5;
    font-style: italic;
    margin-bottom: 12px;
    display: block;
  }
  
  .tip-footer {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    
    .tip-action {
      font-size: 11px;
      color: #E57373;
      font-weight: bold;
      margin-right: 4px;
    }
  }
}

.report-card {
  background: #fff;
  border-radius: 16px;
  padding: 16px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
  
  .report-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 14px;
    
    .report-title {
      font-size: 15px;
      font-weight: bold;
      color: #333;
    }
    .report-date {
      font-size: 11px;
      color: #888;
      background: #F5F7FA;
      padding: 2px 8px;
      border-radius: 10px;
    }
  }
  
  .charts-container {
    display: flex;
    flex-direction: column;
    
    .chart-box {
      background: #F8F9FA;
      border-radius: 12px;
      padding: 10px;
      
      .chart-title {
        font-size: 12px;
        color: #666;
        font-weight: bold;
        margin-bottom: 8px;
        display: block;
      }
      
      .chart-content {
        width: 100%;
        height: 180px;
      }
    }
    
    .mt-10 {
      margin-top: 10px;
    }
  }
  
  .report-summary {
    display: flex;
    flex-direction: column;
    background: rgba(92, 107, 192, 0.05);
    padding: 12px;
    border-radius: 8px;
    
    .summary-item {
      display: flex;
      align-items: flex-start;
      
      .summary-text {
        font-size: 12px;
        color: #5C6BC0;
        line-height: 1.4;
        margin-left: 6px;
        flex: 1;
      }
    }
    
    .mt-5 {
      margin-top: 5px;
    }
    
    .mt-10 {
      margin-top: 10px;
    }
  }
}

/* 底部悬浮导航栏 */
.floating-nav {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  width: 85%;
  max-width: 400px;
  height: 64px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-radius: 32px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
  display: flex;
  justify-content: space-around;
  align-items: center;
  z-index: 100;
  padding: 0 10px;

  .nav-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 4px;
    width: 60px;

    text {
      font-size: 10px;
      color: #BDBDBD;
      transition: color 0.2s ease;
    }

    &.active {
      text {
        color: #3F51B5;
        font-weight: bold;
      }
    }
    
    &:active {
      opacity: 0.7;
    }
  }
}
</style>
