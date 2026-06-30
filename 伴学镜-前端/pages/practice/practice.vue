<template>
  <view class="practice-container">
    <!-- 顶部导航栏 -->
    <view class="custom-navbar" :style="{ paddingTop: statusBarHeight + 'px' }">
      <view class="navbar-left" @tap="goBack">
        <uni-icons type="back" size="24" color="#fff" />
      </view>
      <view class="navbar-title-container">
        <text class="navbar-title">举一反三练习</text>
      </view>
      <view class="navbar-right"></view>
    </view>

    <!-- 背景装饰 -->
    <view class="bg-shape shape-1"></view>
    <view class="bg-shape shape-2"></view>

    <!-- 科目与难度、状态分类筛选栏 -->
    <view class="filter-bar-container">
      <view class="filter-tab" @click="toggleSubjectPicker">
        <text class="current-filter">{{ currentSubject === 'all' ? '全部科目' : currentSubject }}</text>
        <uni-icons :type="showSubjectPicker ? 'top' : 'bottom'" size="14" color="#FFFFFF"></uni-icons>
      </view>
      <view class="filter-divider"></view>
      <view class="filter-tab" @click="toggleDifficultyPicker">
        <text class="current-filter">{{ getDifficultyFilterText(currentDifficulty) }}</text>
        <uni-icons :type="showDifficultyPicker ? 'top' : 'bottom'" size="14" color="#FFFFFF"></uni-icons>
      </view>
      <view class="filter-divider"></view>
      <view class="filter-tab" @click="toggleMasteryPicker">
        <text class="current-filter">{{ getMasteryFilterText(currentMastery) }}</text>
        <uni-icons :type="showMasteryPicker ? 'top' : 'bottom'" size="14" color="#FFFFFF"></uni-icons>
      </view>
    </view>

    <!-- 下拉选择遮罩与内容 (科目) -->
    <view class="subject-picker-mask" v-if="showSubjectPicker || showDifficultyPicker || showMasteryPicker" @click="closeAllPickers"></view>
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

    <!-- 下拉选择遮罩与内容 (难度) -->
    <view class="subject-picker-content" :class="{ 'show': showDifficultyPicker }" :style="{ top: statusBarHeight + 44 + 40 + 'px' }">
      <view 
        class="picker-item difficulty-all" 
        :class="{ active: currentDifficulty === 'all' }" 
        @click="switchDifficulty('all')"
      >
        全部难度
      </view>
      <view 
        v-for="(diff, index) in difficultyLevels" 
        :key="index"
        class="picker-item" 
        :class="['difficulty-' + diff.value, { active: currentDifficulty === diff.value }]"
        @click="switchDifficulty(diff.value)"
      >
        {{ diff.label }}
      </view>
    </view>

    <!-- 下拉选择遮罩与内容 (状态) -->
    <view class="subject-picker-content" :class="{ 'show': showMasteryPicker }" :style="{ top: statusBarHeight + 44 + 40 + 'px' }">
      <view 
        class="picker-item" 
        :class="{ active: currentMastery === 'all' }" 
        @click="switchMastery('all')"
      >
        全部状态
      </view>
      <view 
        v-for="(status, index) in masteryLevels" 
        :key="index"
        class="picker-item" 
        :class="{ active: currentMastery === status.value }"
        @click="switchMastery(status.value)"
      >
        {{ status.label }}
      </view>
    </view>

    <!-- 记录列表 -->
    <scroll-view class="practice-list-view" scroll-y :style="{ height: `calc(100vh - ${statusBarHeight + 94}px)` }">
      <view v-if="isLoading" class="loading-state">
        <uni-icons type="spinner-cycle" size="24" color="#5C6BC0" class="spin-icon" />
        <text>加载练习题中...</text>
      </view>

      <view v-else-if="filteredQuestions.length === 0" class="empty-state">
        <view class="empty-icon bg-orange">
          <uni-icons type="star-filled" size="48" color="#fff" />
        </view>
        <text class="empty-text">当前暂无举一反三练习题</text>
        <text class="empty-subtext">完成试卷批改并提取错题后，系统会自动生成同类型练习题</text>
      </view>

      <view v-else class="practice-list">
        <view class="practice-card" v-for="(question, index) in filteredQuestions" :key="question.id">
          <view class="card-header">
            <view class="subject-badge" :class="['bg-color-' + (index % 4)]">
              {{ question.subject || '综合' }}
            </view>
            <view class="difficulty-badge" :class="question.difficulty">
              {{ getDifficultyText(question.difficulty) }}
            </view>
            <view class="flex-spacer"></view>
            <view class="mastery-btn" :class="{ 'is-mastered': question.is_mastered }" @click="toggleMastery(question)">
              <uni-icons :type="question.is_mastered ? 'checkbox-filled' : 'circle'" size="20" :color="question.is_mastered ? '#4CAF50' : '#ccc'" />
              <text>{{ question.is_mastered ? '已掌握' : '标为掌握' }}</text>
            </view>
            <view class="delete-btn" @click.stop="deleteQuestion(question.id)">
              <uni-icons type="trash" size="18" color="#FF5252" />
            </view>
          </view>
          
          <view class="question-content">
            <text class="q-label">题目：</text>
            <text class="q-text">{{ question.question || '暂无题目内容' }}</text>
          </view>
          
          <!-- 选项区域 (如果有) -->
          <view class="options-list" v-if="question.options && question.options.length > 0">
            <view class="option-item" v-for="(opt, oIndex) in question.options" :key="oIndex" @click="selectOption(question, opt.label)" :class="{'selected': question.userSelected === opt.label, 'correct': question.showAnswer && opt.label === question.answer, 'wrong': question.showAnswer && question.userSelected === opt.label && opt.label !== question.answer}">
              <view class="opt-label">{{ opt.label }}</view>
              <text class="opt-text">{{ opt.text }}</text>
              <uni-icons v-if="question.showAnswer && opt.label === question.answer" type="checkmarkempty" size="18" color="#4CAF50" style="margin-left: auto;" />
              <uni-icons v-if="question.showAnswer && question.userSelected === opt.label && opt.label !== question.answer" type="closeempty" size="18" color="#F44336" style="margin-left: auto;" />
            </view>
          </view>
          
          <!-- 操作按钮 -->
          <view class="action-row" v-if="!question.showAnswer">
            <button class="check-btn" @click="checkAnswer(question)" :disabled="question.options && question.options.length > 0 && !question.userSelected">查看解析</button>
          </view>

          <!-- 解析区域 -->
          <view class="explanation-section" v-if="question.showAnswer">
            <view class="exp-header">
              <uni-icons type="info-filled" size="16" color="#5C6BC0" />
              <text>小伴解析</text>
            </view>
            <view class="correct-answer-row">
              <text class="ans-label">正确答案：</text>
              <text class="ans-text">{{ question.answer }}</text>
            </view>
            <text class="exp-text">{{ question.explanation }}</text>
            <view class="collapse-row">
              <button class="collapse-btn" @click="collapseAnswer(question)">收起解析</button>
            </view>
          </view>
        </view>
      </view>
    </scroll-view>
  </view>
</template>

<script>
import { knowledgeAPI } from '@/api/index.js';

export default {
  data() {
    return {
      statusBarHeight: uni.getSystemInfoSync().statusBarHeight,
      questions: [],
      currentSubject: 'all',
      currentDifficulty: 'all',
      currentMastery: 'all',
      showSubjectPicker: false,
      showDifficultyPicker: false,
      showMasteryPicker: false,
      difficultyLevels: [
        { label: '基础', value: 'easy' },
        { label: '进阶', value: 'medium' },
        { label: '挑战', value: 'hard' }
      ],
      masteryLevels: [
        { label: '未掌握', value: false },
        { label: '已掌握', value: true }
      ],
      isLoading: true,
      userInfo: {
        username: ''
      }
    };
  },
  computed: {
    uniqueSubjects() {
      const subjects = this.questions
        .map(item => item.subject)
        .filter(sub => sub && sub.trim() !== '' && sub !== '未知科目');
      return [...new Set(subjects)];
    },
    filteredQuestions() {
      let filtered = this.questions;
      
      if (this.currentSubject !== 'all') {
        filtered = filtered.filter(item => item.subject === this.currentSubject);
      }
      
      if (this.currentDifficulty !== 'all') {
        filtered = filtered.filter(item => item.difficulty === this.currentDifficulty);
      }
      
      if (this.currentMastery !== 'all') {
        filtered = filtered.filter(item => item.is_mastered === this.currentMastery);
      }
      
      return filtered;
    }
  },
  onLoad() {
    this.loadQuestions();
  },
  onShow() {
    this.loadQuestions();
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
    closeAllPickers() {
      this.showSubjectPicker = false;
      this.showDifficultyPicker = false;
      this.showMasteryPicker = false;
    },
    switchSubject(subject) {
      this.currentSubject = subject;
      this.closeAllPickers();
    },
    toggleSubjectPicker() {
      const current = this.showSubjectPicker;
      this.closeAllPickers();
      this.showSubjectPicker = !current;
    },
    switchDifficulty(diff) {
      this.currentDifficulty = diff;
      this.closeAllPickers();
    },
    toggleDifficultyPicker() {
      const current = this.showDifficultyPicker;
      this.closeAllPickers();
      this.showDifficultyPicker = !current;
    },
    switchMastery(status) {
      this.currentMastery = status;
      this.closeAllPickers();
    },
    toggleMasteryPicker() {
      const current = this.showMasteryPicker;
      this.closeAllPickers();
      this.showMasteryPicker = !current;
    },
    getDifficultyFilterText(level) {
      if (level === 'all') return '全部难度';
      const item = this.difficultyLevels.find(d => d.value === level);
      return item ? item.label : '全部难度';
    },
    getMasteryFilterText(status) {
      if (status === 'all') return '全部状态';
      const item = this.masteryLevels.find(m => m.value === status);
      return item ? item.label : '全部状态';
    },
    getDifficultyText(level) {
      const map = {
        'easy': '基础',
        'medium': '进阶',
        'hard': '挑战'
      };
      return map[level] || '普通';
    },
    async loadQuestions() {
      this.isLoading = true;
      try {
        const res = await knowledgeAPI.getPracticeQuestions({});
        if (res.success) {
          // 初始化前端状态字段
          this.questions = (res.data || []).map(q => ({
            ...q,
            showAnswer: false,
            userSelected: null
          }));
        }
      } catch (error) {
        console.error('获取练习题失败:', error);
      } finally {
        this.isLoading = false;
      }
    },
    selectOption(question, label) {
      if (question.showAnswer) return; // 已经看答案了就不能选了
      question.userSelected = label;
    },
    checkAnswer(question) {
      question.showAnswer = true;
    },
    collapseAnswer(question) {
      question.showAnswer = false;
    },
    async toggleMastery(question) {
      const newStatus = !question.is_mastered;
      // 乐观更新 UI
      question.is_mastered = newStatus;
      
      try {
        await knowledgeAPI.updatePracticeMastery(question.id, {
          is_mastered: newStatus
        });
        uni.showToast({ title: newStatus ? '已掌握' : '已取消掌握', icon: 'none' });
      } catch (error) {
        // 回滚
        question.is_mastered = !newStatus;
        uni.showToast({ title: '操作失败', icon: 'none' });
      }
    },
    async deleteQuestion(id) {
      uni.showModal({
        title: '删除练习题',
        content: '确定要删除这道练习题吗？',
        confirmColor: '#FF5252',
        success: async (res) => {
          if (res.confirm) {
            try {
              uni.showLoading({ title: '删除中...' });
              const result = await knowledgeAPI.deletePracticeQuestion(id);
              if (result.success) {
                uni.showToast({ title: '删除成功', icon: 'success' });
                this.loadQuestions(); // 重新加载列表
              }
            } catch (error) {
              uni.showToast({ title: '删除失败', icon: 'none' });
              // 前端模拟删除（提高体验）
              this.questions = this.questions.filter(q => q.id !== id);
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
view, text, scroll-view, image, button {
  box-sizing: border-box;
}

.practice-container {
  height: 100vh;
  width: 100vw;
  background-color: #F5F7FA;
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
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
  background: rgba(255, 167, 38, 0.1);
  bottom: 20%;
  left: -50px;
}

/* 顶部导航 */
.custom-navbar {
  position: relative;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  height: 44px;
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

/* 筛选栏 */
.filter-bar-container {
  position: relative;
  z-index: 100;
  display: flex;
  background: linear-gradient(135deg, #3F51B5 0%, #5C6BC0 100%);
  padding: 8px 20px 16px;
  border-radius: 0 0 16px 16px;
  box-shadow: 0 4px 12px rgba(63, 81, 181, 0.15);
  margin-top: -1px;
}

.filter-tab {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  position: relative;
}

/* 分割线 */
.filter-divider {
  width: 1px;
  height: 20px;
  background: rgba(255, 255, 255, 0.3);
  margin: 0 4px;
}

.current-filter {
  font-size: 14px;
  font-weight: bold;
  color: #fff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 80px;
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
  top: calc(44px + 40px); /* 导航栏高度 + 筛选栏高度 */
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
      background: #FFF3E0;
      color: #FFA726;
      font-weight: bold;
      box-shadow: 0 2px 8px rgba(255, 167, 38, 0.2);
    }
    
    &:active {
      transform: scale(0.95);
    }
  }
}

/* 列表视图 */
.practice-list-view {
  flex: 1;
  width: 100%;
  padding: 16px;
  position: relative;
  z-index: 1;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding-top: 100px;
  
  .spin-icon {
    animation: spin 1s linear infinite;
    margin-bottom: 12px;
  }
  
  text {
    font-size: 14px;
    color: #888;
  }
}

@keyframes spin {
  100% { transform: rotate(360deg); }
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding-top: 80px;
  
  .empty-icon {
    width: 80px;
    height: 80px;
    border-radius: 40px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 16px;
    background: linear-gradient(135deg, #FFA726 0%, #FB8C00 100%);
    box-shadow: 0 8px 16px rgba(255, 167, 38, 0.2);
  }
  
  .empty-text {
    font-size: 15px;
    color: #666;
  }

  .empty-subtext {
    font-size: 13px;
    color: #94A3B8;
    margin-top: 8px;
    padding: 0 32px;
    text-align: center;
    line-height: 1.6;
  }
}

.practice-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-bottom: 24px;
}

.practice-card {
  background: #fff;
  border-radius: 16px;
  padding: 20px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04);
  
  .card-header {
    display: flex;
    align-items: center;
    margin-bottom: 16px;
    
    .subject-badge {
      padding: 4px 10px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: bold;
      color: #fff;
      margin-right: 8px;
    }
    
    .difficulty-badge {
      padding: 4px 8px;
      border-radius: 6px;
      font-size: 11px;
      font-weight: bold;
      
      &.easy { background: #E8F5E9; color: #2E7D32; }
      &.medium { background: #FFF3E0; color: #E65100; }
      &.hard { background: #FFEBEE; color: #C62828; }
    }
    
    .flex-spacer {
      flex: 1;
    }
    
    .mastery-btn {
      display: flex;
      align-items: center;
      gap: 4px;
      padding: 4px 8px;
      border-radius: 12px;
      background: #F5F7FA;
      transition: all 0.2s;
      
      text {
        font-size: 12px;
        color: #888;
      }
      
      &.is-mastered {
        background: #E8F5E9;
        text { color: #4CAF50; font-weight: bold; }
      }
      
      &:active {
        transform: scale(0.95);
      }
    }
  }
  
  .question-content {
    margin-bottom: 16px;
    
    .q-label {
      font-size: 14px;
      font-weight: bold;
      color: #2C3E50;
      margin-bottom: 8px;
      display: block;
    }
    
    .q-text {
      font-size: 15px;
      color: #333;
      line-height: 1.6;
    }
  }
  
  .options-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
    margin-bottom: 16px;
    
    .option-item {
      display: flex;
      align-items: center;
      padding: 12px 16px;
      background: #F8F9FA;
      border-radius: 10px;
      border: 2px solid transparent;
      transition: all 0.2s;
      
      .opt-label {
        width: 24px;
        height: 24px;
        border-radius: 12px;
        background: #E0E0E0;
        color: #555;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 13px;
        font-weight: bold;
        margin-right: 12px;
        flex-shrink: 0;
      }
      
      .opt-text {
        font-size: 14px;
        color: #333;
      }
      
      &.selected {
        background: #E8EAF6;
        border-color: #5C6BC0;
        .opt-label { background: #5C6BC0; color: #fff; }
      }
      
      &.correct {
        background: #E8F5E9;
        border-color: #4CAF50;
        .opt-label { background: #4CAF50; color: #fff; }
      }
      
      &.wrong {
        background: #FFEBEE;
        border-color: #F44336;
        .opt-label { background: #F44336; color: #fff; }
      }
    }
  }
  
  .action-row {
    display: flex;
    justify-content: flex-end;
    margin-bottom: 12px;
    
    .check-btn {
      margin: 0;
      padding: 0 24px;
      height: 36px;
      line-height: 36px;
      background: linear-gradient(135deg, #5C6BC0 0%, #3F51B5 100%);
      color: #fff;
      font-size: 14px;
      border-radius: 18px;
      
      &[disabled] {
        background: #ccc;
        color: #fff;
      }
    }
  }
  
  .explanation-section {
    background: #F0F2F5;
    padding: 16px;
    border-radius: 12px;
    border-top: 3px solid #5C6BC0;
    
    .exp-header {
      display: flex;
      align-items: center;
      gap: 6px;
      margin-bottom: 12px;
      
      text {
        font-size: 14px;
        font-weight: bold;
        color: #5C6BC0;
      }
    }
    
    .correct-answer-row {
      margin-bottom: 8px;
      
      .ans-label {
        font-size: 14px;
        color: #666;
      }
      
      .ans-text {
        font-size: 16px;
        font-weight: bold;
        color: #4CAF50;
      }
    }
    
    .exp-text {
      font-size: 14px;
      color: #555;
      line-height: 1.6;
    }

    .collapse-row {
      display: flex;
      justify-content: flex-end;
      margin-top: 12px;
    }

    .collapse-btn {
      margin: 0;
      padding: 0 20px;
      height: 34px;
      line-height: 34px;
      background: #E8EAF6;
      color: #3F51B5;
      font-size: 13px;
      border-radius: 17px;
      border: none;
    }
  }
}

/* 科目背景色池 */
.bg-color-0 { background: #5C6BC0; }
.bg-color-1 { background: #42A5F5; }
.bg-color-2 { background: #66BB6A; }
.bg-color-3 { background: #FFA726; }
</style>
