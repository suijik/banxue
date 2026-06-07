<template>
  <view class="history-container">
    <!-- 顶部导航栏 -->
    <view class="custom-navbar" :style="{ paddingTop: statusBarHeight + 'px' }">
      <view class="navbar-left" @tap="goBack">
        <uni-icons type="back" size="24" color="#333" />
      </view>
      <view class="navbar-title-container">
        <text class="navbar-title">批改历史分类</text>
      </view>
      <view class="navbar-right"></view>
    </view>

    <!-- 科目分类筛选栏 -->
    <view class="subject-filter-bar" @click="toggleSubjectPicker">
      <text class="current-subject">{{ currentSubject === 'all' ? '全部科目' : currentSubject }}</text>
      <uni-icons :type="showSubjectPicker ? 'top' : 'bottom'" size="16" color="#333333"></uni-icons>
    </view>

    <!-- 下拉选择遮罩与内容 -->
    <view class="subject-picker-mask" v-if="showSubjectPicker" @click="toggleSubjectPicker"></view>
    <view class="subject-picker-content" :class="{ 'show': showSubjectPicker }" :style="{ top: statusBarHeight + 44 + 40 + 'px' }">
      <view 
        class="picker-item" 
        :class="{ active: currentSubject === 'all' }" 
        @click="switchSubject('all')"
      >
        全部科目
      </view>
      <view 
        v-for="(subject, index) in uniqueSubjects" 
        :key="index"
        class="picker-item" 
        :class="{ active: currentSubject === subject }"
        @click="switchSubject(subject)"
      >
        {{ subject }}
      </view>
    </view>

    <!-- 记录列表 -->
    <scroll-view class="history-list-view" scroll-y :style="{ height: `calc(100vh - ${statusBarHeight + 94}px)` }">
      <view v-if="isLoading" class="loading-state">
        <uni-icons type="spinner-cycle" size="24" color="#5C6BC0" class="spin-icon" />
        <text>加载记录中...</text>
      </view>

      <view v-else-if="filteredAnalyses.length === 0" class="empty-state">
        <uni-icons type="info-filled" size="48" color="#DCDFE6" />
        <text>暂无该科目的批改记录</text>
      </view>

      <view v-else class="history-list">
        <view 
          class="history-item" 
          v-for="(analysis, index) in filteredAnalyses" 
          :key="analysis.id" 
          @click="viewAnalysis(analysis.id, analysis.status)"
        >
          <view class="item-left">
            <view class="item-icon" :class="['bg-color-' + (index % 4)]">
              <text>{{ analysis.subject ? analysis.subject.substring(0, 1) : analysis.exam_name.substring(0, 1) }}</text>
            </view>
            <view class="item-info">
              <view class="name-row">
                <text class="item-name">{{ analysis.exam_name }}</text>
                <view class="subject-tag" v-if="analysis.subject">{{ analysis.subject }}</view>
              </view>
              <text class="item-date">{{ formatDate(analysis.created_at) }}</text>
            </view>
          </view>
          
          <view class="item-right">
            <view class="status-container" @click.stop="viewAnalysis(analysis.id, analysis.status)">
              <view v-if="analysis.status === 'pending'" class="status-badge pending">
                <uni-icons type="spinner-cycle" size="14" color="#FFB74D" class="spin-icon" />
                <text>分析中</text>
              </view>
              <view v-else-if="analysis.status === 'extracting_mistakes'" class="status-badge pending">
                <uni-icons type="spinner-cycle" size="14" color="#FFB74D" class="spin-icon" />
                <text>整理错题中</text>
              </view>
              <view v-else-if="analysis.status === 'generating_exercises'" class="status-badge pending">
                <uni-icons type="spinner-cycle" size="14" color="#FFB74D" class="spin-icon" />
                <text>生成题目中</text>
              </view>
              <view v-else-if="analysis.status === 'failed'" class="status-badge failed">
                <text>失败</text>
              </view>
              <view v-else class="status-badge success">
                <text>已完成</text>
              </view>
              <uni-icons type="right" size="16" color="#ccc" style="margin-left: 4px;" />
            </view>
            <view class="delete-btn" @click.stop="deleteRecord(analysis.id, index)">
              <uni-icons type="trash" size="18" color="#FF5252" />
            </view>
          </view>
        </view>
      </view>
    </scroll-view>
  </view>
</template>

<script>
import { examAPI } from '@/api/index.js';

export default {
  data() {
    return {
      statusBarHeight: uni.getSystemInfoSync().statusBarHeight,
      examAnalyses: [],
      currentSubject: 'all',
      showSubjectPicker: false,
      isLoading: true,
      userInfo: {
        username: uni.getStorageSync('user') ? JSON.parse(uni.getStorageSync('user')).username : ''
      }
    };
  },
  computed: {
    // 动态计算拥有的科目种类，自动过滤掉无效/空科目
    uniqueSubjects() {
      const subjects = this.examAnalyses
        .map(item => item.subject)
        .filter(sub => sub && sub.trim() !== '' && sub !== '未知科目');
      return [...new Set(subjects)]; // 去重
    },
    // 根据选中的标签过滤列表
    filteredAnalyses() {
      if (this.currentSubject === 'all') {
        return this.examAnalyses;
      }
      return this.examAnalyses.filter(item => item.subject === this.currentSubject);
    }
  },
  onLoad() {
    this.loadExamAnalyses();
  },
  onShow() {
    // 每次进入页面都刷新，保证状态是最新的
    this.loadExamAnalyses();
  },
  methods: {
    goBack() {
      // 检查页面栈，如果能返回上一页（exam-analysis）就返回，否则跳回首页
      const pages = getCurrentPages();
      if (pages.length > 1) {
        uni.navigateBack({
          delta: 1
        });
      } else {
        uni.switchTab({
          url: '/pages/home/home'
        });
      }
    },
    switchSubject(subject) {
      this.currentSubject = subject;
      this.showSubjectPicker = false;
    },
    toggleSubjectPicker() {
      this.showSubjectPicker = !this.showSubjectPicker;
    },
    async loadExamAnalyses() {
      if (!this.userInfo.username) return;
      this.isLoading = true;
      try {
        const res = await examAPI.getHistory(this.userInfo.username);
        if (res.success) {
          this.examAnalyses = res.data;
        }
      } catch (error) {
        console.error('获取历史记录失败:', error);
        uni.showToast({ title: '加载记录失败', icon: 'none' });
      } finally {
        this.isLoading = false;
      }
    },
    viewAnalysis(id, status) {
      if (status === 'pending') {
        uni.showToast({
          title: '小伴还在努力批改中，请稍后再来看哦~',
          icon: 'none'
        });
        this.loadExamAnalyses();
        return;
      }
      if (status === 'failed') {
        uni.showToast({ title: '抱歉，该次批改失败', icon: 'none' });
        return;
      }
      
      // 设置标志位，让 exam-analysis 知道是从历史页面进来的
      uni.setStorageSync('view_analysis_id', id);
      uni.setStorageSync('from_history', true);
      
      // 跳转到拍照批改页面展示详情
      uni.navigateTo({
        url: '/pages/exam-analysis/exam-analysis'
      });
    },
    formatDate(dateString) {
      if (!dateString) return '';
      const date = new Date(dateString);
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const day = String(date.getDate()).padStart(2, '0');
      const hours = String(date.getHours()).padStart(2, '0');
      const minutes = String(date.getMinutes()).padStart(2, '0');
      return `${month}-${day} ${hours}:${minutes}`;
    },
    async deleteRecord(analysisId, index) {
      uni.showModal({
        title: '删除记录',
        content: '确定要删除这条批改记录吗？删除后无法恢复。',
        confirmColor: '#FF5252',
        success: async (res) => {
          if (res.confirm) {
            try {
              uni.showLoading({ title: '删除中...' });
              const result = await examAPI.deleteAnalysis(analysisId);
              if (result.success) {
                uni.showToast({ title: '删除成功', icon: 'success' });
                // 重新加载列表以更新数据和标签栏
                this.loadExamAnalyses();
              } else {
                throw new Error(result.message);
              }
            } catch (error) {
              uni.showToast({ title: '删除失败，请重试', icon: 'none' });
            } finally {
              uni.hideLoading();
            }
          }
        }
      });
    }
  }
};
</script>

<style lang="scss" scoped>
view, text, scroll-view {
  box-sizing: border-box;
}

.history-container {
  height: 100vh;
  width: 100vw;
  background-color: #F5F7FA;
  display: flex;
  flex-direction: column;
}

.custom-navbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  height: 44px;
  box-sizing: content-box;
  background: #fff;
  box-shadow: 0 2px 8px rgba(0,0,0,0.02);
  z-index: 10;
  
  .navbar-left { width: 40px; height: 100%; display: flex; align-items: center; }
  .navbar-title-container {
    flex: 1; text-align: center;
    .navbar-title { font-size: 17px; font-weight: bold; color: #333; }
  }
  .navbar-right { width: 40px; }
}

/* 筛选栏 */
.subject-filter-bar {
  position: relative;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  padding: 12px 20px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.03);
}

.current-subject {
  font-size: 15px;
  font-weight: bold;
  color: #333;
}

/* 遮罩层 */
.subject-picker-mask {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.4);
  z-index: 90;
}

/* 下拉内容 */
.subject-picker-content {
  position: absolute;
  top: calc(44px + 44px); /* 导航栏高度 + 筛选栏高度 */
  left: 16px;
  right: 16px;
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  z-index: 95;
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  transform: translateY(-20px);
  opacity: 0;
  pointer-events: none;
  transition: all 0.3s cubic-bezier(0.18, 0.89, 0.32, 1.28);
  
  &.show {
    transform: translateY(0);
    opacity: 1;
    pointer-events: auto;
  }
  
  .picker-item {
    padding: 8px 20px;
    background: #F0F2F5;
    color: #666;
    border-radius: 20px;
    font-size: 14px;
    transition: all 0.2s;
    
    &.active {
      background: #5C6BC0;
      color: #fff;
      font-weight: bold;
      box-shadow: 0 4px 10px rgba(92, 107, 192, 0.3);
    }
    
    &:active {
      transform: scale(0.95);
    }
  }
}

.history-list-view {
  flex: 1;
  padding: 16px;
}

.loading-state, .empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 200px;
  
  text {
    margin-top: 12px;
    font-size: 14px;
    color: #999;
  }
}

.spin-icon {
  animation: spin 1s linear infinite;
}
@keyframes spin {
  100% { transform: rotate(360deg); }
}

/* 列表项样式 */
.history-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.history-item {
  background: #fff;
  border-radius: 16px;
  padding: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 4px 12px rgba(0,0,0,0.03);
  transition: transform 0.2s ease;
  
  &:active {
    transform: scale(0.98);
    background: #FAFAFA;
  }
  
  .item-left {
    display: flex;
    align-items: center;
    flex: 1;
    overflow: hidden;
    
    .item-icon {
      width: 44px;
      height: 44px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      margin-right: 12px;
      flex-shrink: 0;
      
      text { font-size: 18px; font-weight: bold; color: #fff; }
      
      &.bg-color-0 { background: linear-gradient(135deg, #7986CB, #5C6BC0); }
      &.bg-color-1 { background: linear-gradient(135deg, #FFB74D, #F57C00); }
      &.bg-color-2 { background: linear-gradient(135deg, #81C784, #4CAF50); }
      &.bg-color-3 { background: linear-gradient(135deg, #BA68C8, #9C27B0); }
    }
    
    .item-info {
      flex: 1;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      
      .name-row {
        display: flex;
        align-items: center;
        margin-bottom: 4px;
        
        .item-name {
          font-size: 15px;
          font-weight: bold;
          color: #333;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
          max-width: 150px;
        }
        
        .subject-tag {
          margin-left: 8px;
          font-size: 10px;
          color: #5C6BC0;
          background: rgba(92, 107, 192, 0.1);
          padding: 2px 6px;
          border-radius: 4px;
          flex-shrink: 0;
        }
      }
      
      .item-date {
        font-size: 12px;
        color: #888;
      }
    }
  }
  
  .item-right {
    display: flex;
    align-items: center;
    gap: 12px;
    
    .status-container {
      display: flex;
      align-items: center;
    }
    
    .delete-btn {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 32px;
      height: 32px;
      border-radius: 16px;
      background: #FFF0F0;
      transition: all 0.2s;
      
      &:active {
        background: #FFE5E5;
        transform: scale(0.9);
      }
    }
    
    .status-badge {
      display: flex;
      align-items: center;
      padding: 4px 8px;
      border-radius: 12px;
      font-size: 11px;
      font-weight: 500;
      
      &.success { background: #E8F5E9; color: #4CAF50; }
      &.pending { background: #FFF3E0; color: #FF9800; }
      &.failed { background: #FFEBEE; color: #F44336; }
      
      .spin-icon { margin-right: 4px; }
    }
  }
}
</style>