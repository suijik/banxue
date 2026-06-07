<template>
  <view class="parent-dashboard">
    <!-- 顶部导航栏 -->
    <view class="custom-navbar" :style="{ paddingTop: statusBarHeight + 'px' }">
      <view class="navbar-left" @tap="goBack">
        <uni-icons type="back" size="24" color="#fff" />
      </view>
      <view class="navbar-title-container">
        <text class="navbar-title">家长智囊台</text>
      </view>
      <view class="navbar-right"></view>
    </view>

    <!-- 背景装饰 -->
    <view class="bg-shape shape-1"></view>
    <view class="bg-shape shape-2"></view>

    <scroll-view scroll-y class="dashboard-content" :style="{ height: `calc(100vh - ${statusBarHeight + 54}px)` }">
      <view class="hero-card">
        <view class="hero-texts">
          <text class="hero-title">家长智囊台</text>
          <text class="hero-subtitle">AI 情绪辅导与学习周报</text>
          <text class="hero-date">{{ parentData.report_date_range || '正在生成本周学习画像...' }}</text>
        </view>
        <view class="hero-badge">成长追踪</view>
      </view>

      <view class="stats-grid">
        <view class="stat-mini-card">
          <text class="stat-mini-num">{{ parentData.stats.mistakes_count }}</text>
          <text class="stat-mini-label">本周错题</text>
        </view>
        <view class="stat-mini-card">
          <text class="stat-mini-num">{{ parentData.stats.new_kps_count }}</text>
          <text class="stat-mini-label">新增知识点</text>
        </view>
        <view class="stat-mini-card">
          <text class="stat-mini-num">{{ parentData.stats.practices_count }}</text>
          <text class="stat-mini-label">练习次数</text>
        </view>
      </view>

      <view v-if="isLoading" class="loading-board">
        <view class="skeleton-card skeleton-lg"></view>
        <view class="skeleton-card skeleton-md"></view>
        <view class="skeleton-card skeleton-md"></view>
      </view>

      <block v-else>
      <!-- 辅导话术建议 -->
      <view class="section tip-card">
        <view class="tip-header">
          <uni-icons type="heart-filled" size="18" color="#E57373"></uni-icons>
          <text class="tip-title">AI 辅导锦囊</text>
        </view>
        <text class="tip-content">{{ parentData.ai_analysis.tutoring_advice || '正在为您生成辅导建议，请稍候...' }}</text>
      </view>

      <!-- 学习周报 -->
      <view class="section report-card">
        <view class="report-header">
          <text class="report-title">本周学习报告</text>
          <text class="report-date">{{ parentData.report_date_range || '加载中...' }}</text>
        </view>
        
        <block v-if="hasData">
          <!-- 饼图：错题归因分析 -->
          <view class="chart-box">
            <text class="chart-title">错题归因分析</text>
            <view class="chart-content">
              <qiun-data-charts 
                type="pie"
                :opts="pieOpts"
                :chartData="pieData"
              />
            </view>
          </view>
          
          <!-- 折线图：举一反三掌握率趋势 -->
          <view class="chart-box mt-15">
            <text class="chart-title">举一反三掌握率趋势 (近7天)</text>
            <view class="chart-content">
              <qiun-data-charts 
                type="line"
                :opts="lineOpts"
                :chartData="lineData"
              />
            </view>
          </view>
        </block>

        <view v-else class="empty-data-box mt-15">
          <uni-icons type="info-filled" size="40" color="#CFD8DC"></uni-icons>
          <text class="empty-text">近期数据积累中，暂无法生成统计图表</text>
          <text class="empty-subtext">让孩子多做些练习，再来看看吧~</text>
        </view>

        <!-- AI 总结与建议 -->
        <view class="ai-summary-box mt-15">
          <view class="summary-item">
            <uni-icons type="info-filled" size="16" color="#5C6BC0"></uni-icons>
            <text class="summary-text">AI总结：{{ parentData.ai_analysis.summary || '分析中...' }}</text>
          </view>
          <view class="summary-item mt-8">
            <uni-icons type="flag-filled" size="16" color="#66BB6A"></uni-icons>
            <text class="summary-text">下周建议：{{ parentData.ai_analysis.suggestion || '规划中...' }}</text>
          </view>
        </view>
      </view>
      </block>
    </scroll-view>
  </view>
</template>

<script>
import { reportAPI } from '@/api/index.js';

export default {
  data() {
    return {
      statusBarHeight: uni.getSystemInfoSync().statusBarHeight,
      parentData: {
        report_date_range: '',
        ai_analysis: {
          tutoring_advice: '',
          summary: '',
          suggestion: ''
        },
        stats: {
          mistakes_count: 0,
          new_kps_count: 0,
          practices_count: 0
        }
      },
      isLoading: true,
      hasData: true,
      pieData: {},
      pieOpts: {
        color: ["#5C6BC0", "#FFB74D", "#66BB6A", "#EF5350", "#8E24AA", "#999999"],
        padding: [5, 5, 5, 5],
        enableScroll: false,
        extra: {
          pie: {
            activeOpacity: 0.5,
            activeRadius: 10,
            offsetAngle: 0,
            labelWidth: 15,
            border: false,
            borderWidth: 3,
            borderColor: "#FFFFFF"
          }
        }
      },
      lineData: {},
      lineOpts: {
        color: ["#42A5F5"],
        padding: [5, 10, 10, 10],
        enableScroll: false,
        legend: {
          show: true,
          position: "top",
          float: "right",
          margin: 5
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
  onLoad() {
    const user = this.getStoredUser();
    if (user && user.username) {
      this.fetchParentDashboard(user.username);
    } else {
      this.fetchParentDashboard('test');
    }
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
    async fetchParentDashboard(username) {
      try {
        this.isLoading = true;
        uni.showLoading({ title: '加载报告中...' });
        const res = await reportAPI.getParentDashboard(username);
        if (res.success) {
          const data = res.data;
          this.parentData.report_date_range = data.report_date_range;
          this.parentData.ai_analysis = data.ai_analysis;
          this.parentData.stats = data.stats || {
            mistakes_count: 0,
            new_kps_count: 0,
            practices_count: 0
          };
          
          this.hasData = data.stats && (data.stats.mistakes_count > 0 || data.stats.practices_count > 0);

          this.pieData = {
            series: data.pie_chart.series
          };

          this.lineData = {
            categories: data.line_chart.categories,
            series: data.line_chart.series
          };
        }
      } catch (err) {
        console.error('获取家长面板数据失败', err);
        uni.showToast({ title: '获取数据失败', icon: 'none' });
      } finally {
        this.isLoading = false;
        uni.hideLoading();
      }
    },
    goBack() {
      uni.navigateBack({
        delta: 1,
        fail: () => {
          uni.switchTab({ url: '/pages/home/home' });
        }
      });
    }
  }
};
</script>

<style lang="scss" scoped>
view, text, scroll-view, image {
  box-sizing: border-box;
}

.parent-dashboard {
  height: 100vh;
  width: 100%;
  background-color: #F5F7FA;
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
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

/* 背景装饰 */
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
  background: rgba(92, 107, 192, 0.15);
  top: -50px;
  right: -50px;
}
.shape-2 {
  width: 150px;
  height: 150px;
  background: rgba(63, 81, 181, 0.1);
  bottom: 20%;
  left: -50px;
}

.dashboard-content {
  flex: 1;
  width: 100%;
  padding: 20px 16px 40px;
  position: relative;
  z-index: 1;
}

.hero-card {
  position: relative;
  overflow: hidden;
  background: linear-gradient(135deg, #5C6BC0 0%, #3F51B5 100%);
  border-radius: 22px;
  padding: 20px 18px;
  margin-bottom: 16px;
  box-shadow: 0 14px 28px rgba(63, 81, 181, 0.18);
}

.hero-card::after {
  content: '';
  position: absolute;
  right: -20px;
  top: -20px;
  width: 120px;
  height: 120px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.12);
}

.hero-texts {
  position: relative;
  z-index: 1;
}

.hero-title {
  display: block;
  font-size: 24px;
  font-weight: 700;
  color: #fff;
  margin-bottom: 6px;
}

.hero-subtitle {
  display: block;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.9);
  margin-bottom: 12px;
}

.hero-date {
  display: inline-block;
  font-size: 12px;
  color: #fff;
  background: rgba(255, 255, 255, 0.16);
  border-radius: 999px;
  padding: 6px 10px;
}

.hero-badge {
  position: absolute;
  right: 16px;
  bottom: 16px;
  z-index: 1;
  font-size: 12px;
  color: #fff;
  background: rgba(255, 255, 255, 0.16);
  padding: 6px 10px;
  border-radius: 999px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.stat-mini-card {
  background: rgba(255, 255, 255, 0.88);
  border-radius: 16px;
  padding: 14px 10px;
  box-shadow: 0 8px 20px rgba(15, 23, 42, 0.05);
  text-align: center;
}

.stat-mini-num {
  display: block;
  font-size: 20px;
  font-weight: 700;
  color: #334155;
  margin-bottom: 4px;
}

.stat-mini-label {
  display: block;
  font-size: 11px;
  color: #718096;
}

.loading-board {
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin-bottom: 8px;
}

.skeleton-card {
  border-radius: 18px;
  background: linear-gradient(90deg, #EEF2FF 25%, #F8FAFC 37%, #EEF2FF 63%);
  background-size: 400% 100%;
  animation: skeletonMove 1.4s ease infinite;
}

.skeleton-lg {
  height: 120px;
}

.skeleton-md {
  height: 220px;
}

@keyframes skeletonMove {
  0% { background-position: 100% 50%; }
  100% { background-position: 0 50%; }
}

.section {
  background: #fff;
  border-radius: 16px;
  padding: 16px;
  margin-bottom: 16px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04);
}

.tip-card {
  background: linear-gradient(135deg, #FFF8F8 0%, #FFEAEA 100%);
  border: 1px solid rgba(229, 115, 115, 0.2);
  
  .tip-header {
    display: flex;
    align-items: center;
    margin-bottom: 12px;
    
    .tip-title {
      font-size: 16px;
      font-weight: bold;
      color: #E57373;
      margin-left: 6px;
    }
  }
  
  .tip-content {
    font-size: 14px;
    color: #555;
    line-height: 1.6;
    font-style: italic;
    display: block;
  }
}

.report-card {
  .report-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    
    .report-title {
      font-size: 16px;
      font-weight: bold;
      color: #333;
    }
    .report-date {
      font-size: 12px;
      color: #888;
      background: #F5F7FA;
      padding: 4px 10px;
      border-radius: 12px;
    }
  }
  
  .chart-box {
    background: #F8F9FA;
    border-radius: 12px;
    padding: 16px;
    
    .chart-title {
      font-size: 14px;
      color: #555;
      font-weight: bold;
      margin-bottom: 12px;
      display: block;
      text-align: center;
    }
    
    .chart-content {
      width: 100%;
      height: 220px;
    }
  }
  
  .ai-summary-box {
    background: rgba(92, 107, 192, 0.05);
    padding: 16px;
    border-radius: 12px;
    
    .summary-item {
      display: flex;
      align-items: flex-start;
      
      .summary-text {
        font-size: 13px;
        color: #4C5C9C;
        line-height: 1.5;
        margin-left: 8px;
        flex: 1;
      }
    }
  }

  .empty-data-box {
    background: #F8F9FA;
    border-radius: 12px;
    padding: 40px 20px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    
    .empty-text {
      font-size: 15px;
      font-weight: bold;
      color: #666;
      margin-top: 16px;
      margin-bottom: 8px;
    }
    
    .empty-subtext {
      font-size: 13px;
      color: #999;
    }
  }
  
  .mt-8 { margin-top: 8px; }
  .mt-15 { margin-top: 15px; }
}
</style>
