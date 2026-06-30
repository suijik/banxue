<template>
  <view class="mistake-container">
    <view class="top-section">
      <!-- 顶部导航栏 -->
      <view class="custom-navbar" :style="{ paddingTop: statusBarHeight + 'px' }">
        <view class="navbar-left" @tap="goBack">
          <uni-icons type="back" size="24" color="#fff" />
        </view>
        <view class="navbar-title-container">
          <text class="navbar-title">智能错题本</text>
        </view>
        <view class="navbar-right"></view>
      </view>

      <view class="filter-panel">
        <view class="filter-row">
          <text class="filter-label">科目</text>
          <view class="subject-trigger" @click="toggleSubjectPicker">
            <text class="subject-trigger-text">{{ currentSubjectLabel }}</text>
            <uni-icons :type="showSubjectPicker ? 'top' : 'bottom'" size="16" color="#3F51B5"></uni-icons>
          </view>
        </view>

        <view class="filter-row compact">
          <text class="filter-label">状态</text>
          <view class="mastery-filter">
            <view
              v-for="item in masteryOptions"
              :key="item.value"
              class="filter-chip mastery-chip"
              :class="{ active: currentMastery === item.value }"
              @click="switchMastery(item.value)"
            >
              {{ item.label }}
            </view>
          </view>
        </view>
      </view>
    </view>

    <!-- 背景装饰 -->
    <view class="bg-shape shape-1"></view>
    <view class="bg-shape shape-2"></view>

    <view v-if="showSubjectPicker" class="subject-picker-mask" @click="toggleSubjectPicker"></view>
    <view v-if="showSubjectPicker" class="subject-picker-pop" :style="subjectPickerStyle" @click.stop>
      <scroll-view scroll-y class="subject-picker-scroll" show-scrollbar="false">
        <view class="subject-picker-grid">
          <view
            class="subject-option"
            :class="{ active: currentSubject === 'all' }"
            @click="switchSubject('all')"
          >
            全部科目
          </view>
          <view
            v-for="(subject, index) in uniqueSubjects"
            :key="index"
            class="subject-option"
            :class="{ active: currentSubject === subject }"
            @click="switchSubject(subject)"
          >
            {{ subject }}
          </view>
        </view>
      </scroll-view>
    </view>

    <!-- 记录列表 -->
    <scroll-view class="mistake-list-view" scroll-y>
      <view v-if="isLoading" class="loading-state">
        <uni-icons type="spinner-cycle" size="24" color="#5C6BC0" class="spin-icon" />
        <text>加载错题中...</text>
      </view>

      <view v-else-if="filteredGroups.length === 0" class="empty-state">
        <view class="empty-icon bg-blue">
          <uni-icons type="list" size="48" color="#fff" />
        </view>
        <text class="empty-text">{{ emptyStateText }}</text>
      </view>

      <view v-else class="mistake-list">
        <view class="exam-group-card" v-for="(group, groupIndex) in filteredGroups" :key="group.group_id">
          <view class="exam-group-header" @click="toggleGroup(group.group_id)">
            <view class="group-main-info">
              <view class="group-cover" :class="['bg-color-' + (groupIndex % 4)]">
                <view class="cover-binding"></view>
                <view class="cover-content">
                  <text class="cover-subject">{{ group.subject || '试卷' }}</text>
                  <view class="cover-line cover-line-lg"></view>
                  <view class="cover-line"></view>
                  <view class="cover-line cover-line-short"></view>
                </view>
              </view>
              <view class="group-texts">
                <view class="group-title-row">
                  <text class="group-title">{{ group.exam_name || '未命名试卷' }}</text>
                  <text class="group-subject">{{ group.subject || '未知科目' }}</text>
                </view>
                <view class="group-meta-row">
                  <text class="group-date">{{ formatDate(group.latest_created_at) }}</text>
                  <text class="group-count">共 {{ group.mistake_count || 0 }} 道错题</text>
                </view>
              </view>
            </view>
            <view class="group-actions">
              <view class="group-delete-btn" @click.stop="deleteGroup(group)">
                <uni-icons type="trash" size="16" color="#FF5252" />
              </view>
              <view class="preview-btn" v-if="group.exam_image_path" @click.stop="previewExamImage(group.exam_image_path)">
                <uni-icons type="image" size="16" color="#5C6BC0" />
              </view>
              <uni-icons :type="expandedGroups[group.group_id] ? 'top' : 'bottom'" size="18" color="#999" />
            </view>
          </view>

          <view v-if="expandedGroups[group.group_id]" class="group-mistakes">
            <view class="mistake-card" v-for="mistake in group.mistakes" :key="mistake.id">
              <view class="card-header">
                <view class="question-meta">
                  <view class="meta-badges">
                    <text class="question-no">{{ mistake.question_no || '未标注题号' }}</text>
                    <text class="mastery-badge" :class="{ mastered: mistake.is_mastered }">
                      {{ mistake.is_mastered ? '已掌握' : '未掌握' }}
                    </text>
                  </view>
                  <text class="stem-summary" v-if="mistake.stem_summary">{{ mistake.stem_summary }}</text>
                </view>
                <view class="right-actions">
                  <view class="mastery-toggle" :class="{ mastered: mistake.is_mastered }" @click.stop="toggleMastery(mistake)">
                    <uni-icons :type="mistake.is_mastered ? 'checkbox-filled' : 'circle'" size="14" :color="mistake.is_mastered ? '#22C55E' : '#94A3B8'" />
                    <text>{{ mistake.is_mastered ? '已掌握' : '标记掌握' }}</text>
                  </view>
                  <view class="error-type-selector" @click.stop="openErrorTypePicker(mistake)">
                    <text class="type-text" :class="{'has-type': mistake.error_type && mistake.error_type !== '未归类'}">{{ mistake.error_type || '未归类' }}</text>
                    <uni-icons type="bottom" size="12" color="#999" />
                  </view>
                  <view class="delete-btn" @click.stop="deleteMistake(mistake.id)">
                    <uni-icons type="trash" size="18" color="#FF5252" />
                  </view>
                </view>
              </view>
              
              <view class="question-content">
                <text class="q-label">题目：</text>
                <text class="q-text">{{ mistake.question || '暂无题目内容' }}</text>
              </view>
              
              <view class="answer-section">
                <view class="answer-box wrong-answer">
                  <text class="ans-label">你的答案：</text>
                  <text class="ans-text wrong">{{ mistake.user_answer || '未识别到' }}</text>
                </view>
                <view class="answer-box correct-answer">
                  <text class="ans-label">正确答案：</text>
                  <text class="ans-text right">{{ mistake.correct_answer || '暂无' }}</text>
                </view>
              </view>

              <view class="explanation-section" v-if="mistake.explanation">
                <view class="exp-header" @click="toggleExplanation(mistake.id)">
                  <view class="exp-header-left">
                    <uni-icons type="info-filled" size="16" color="#5C6BC0" />
                    <text>小伴解析</text>
                  </view>
                  <uni-icons :type="expandedExplanations[mistake.id] ? 'top' : 'bottom'" size="16" color="#5C6BC0" />
                </view>
                <text class="exp-text" v-if="expandedExplanations[mistake.id]">{{ mistake.explanation }}</text>
              </view>
            </view>
          </view>
        </view>
      </view>
    </scroll-view>
  </view>
</template>

<script>
import { mistakeAPI, serverURL } from '@/api/index.js';

export default {
  data() {
    return {
      statusBarHeight: uni.getSystemInfoSync().statusBarHeight,
      groupedMistakes: [],
      expandedGroups: {},
      expandedExplanations: {},
      currentSubject: 'all',
      currentMastery: 'unmastered',
      showSubjectPicker: false,
      isLoading: true,
      userInfo: {
        username: ''
      },
      masteryOptions: [
        { label: '未掌握', value: 'unmastered' },
        { label: '已掌握', value: 'mastered' }
      ],
      errorTypes: ['粗心大意', '概念不清', '计算错误', '思路卡壳', '审题不清', '未归类']
    };
  },
  computed: {
    uniqueSubjects() {
      const subjects = this.groupedMistakes
        .map(item => item.subject)
        .filter(sub => sub && sub.trim() !== '' && sub !== '未知科目');
      return [...new Set(subjects)];
    },
    filteredGroups() {
      if (this.currentSubject === 'all') {
        return this.groupedMistakes;
      }
      return this.groupedMistakes.filter(item => item.subject === this.currentSubject);
    },
    currentSubjectLabel() {
      return this.currentSubject === 'all' ? '全部科目' : this.currentSubject;
    },
    subjectPickerStyle() {
      return {
        top: `${this.statusBarHeight + 118}px`
      };
    },
    emptyStateText() {
      const subjectText = this.currentSubject === 'all' ? '当前筛选条件' : `${this.currentSubject}`;
      return this.currentMastery === 'mastered'
        ? `暂无${subjectText}的已掌握错题`
        : `太棒了！暂无${subjectText}的未掌握错题`;
    }
  },
  onLoad() {
    this.loadMistakes();
  },
  onShow() {
    this.loadMistakes();
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
    switchSubject(subject) {
      this.currentSubject = subject;
      this.showSubjectPicker = false;
    },
    switchMastery(status) {
      if (this.currentMastery === status) return;
      this.currentMastery = status;
      this.loadMistakes();
    },
    toggleSubjectPicker() {
      this.showSubjectPicker = !this.showSubjectPicker;
    },
    toggleGroup(groupId) {
      this.$set(this.expandedGroups, groupId, !this.expandedGroups[groupId]);
    },
    toggleExplanation(mistakeId) {
      this.$set(this.expandedExplanations, mistakeId, !this.expandedExplanations[mistakeId]);
    },
    async loadMistakes() {
      this.isLoading = true;
      try {
        const res = await mistakeAPI.getMistakes({
          group_by_exam: true,
          is_mastered: this.currentMastery === 'mastered' ? 'true' : 'false'
        });
        if (res.success) {
          this.groupedMistakes = res.data || [];
          const nextExpanded = {};
          (this.groupedMistakes || []).forEach((group, index) => {
            nextExpanded[group.group_id] = this.expandedGroups[group.group_id] ?? index === 0;
          });
          this.expandedGroups = nextExpanded;
        }
      } catch (error) {
        console.error('获取错题失败:', error);
        this.groupedMistakes = [];
      } finally {
        this.isLoading = false;
      }
    },
    async deleteMistake(id) {
      uni.showModal({
        title: '删除错题',
        content: '确定要将这道题移出错题本吗？',
        confirmColor: '#FF5252',
        success: async (res) => {
          if (res.confirm) {
            try {
              uni.showLoading({ title: '删除中...' });
              const result = await mistakeAPI.deleteMistake(id);
              if (result.success) {
                uni.showToast({ title: '删除成功', icon: 'success' });
                this.loadMistakes();
              }
            } catch (error) {
              uni.showToast({ title: '删除失败', icon: 'none' });
            } finally {
              uni.hideLoading();
            }
          }
        }
      });
    },
    async deleteGroup(group) {
      uni.showModal({
        title: '删除整张试卷',
        content: `确定删除“${group.exam_name || '该试卷'}”下的全部错题吗？`,
        confirmColor: '#FF5252',
        success: async (res) => {
          if (!res.confirm) return;
          try {
            uni.showLoading({ title: '删除中...' });
            const result = await mistakeAPI.deleteMistakeGroup({
              group_id: group.group_id
            });
            if (result.success) {
              uni.showToast({ title: '已删除整张试卷', icon: 'success' });
              this.loadMistakes();
            } else {
              throw new Error(result.message || '删除失败');
            }
          } catch (error) {
            uni.showToast({ title: error.message || '删除失败', icon: 'none' });
          } finally {
            uni.hideLoading();
          }
        }
      });
    },
    formatDate(dateString) {
      if (!dateString) return '';
      const date = new Date(dateString);
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const day = String(date.getDate()).padStart(2, '0');
      return `${month}-${day}`;
    },
    getImageUrl(path) {
      if (!path) return '';
      if (path.startsWith('http')) return path;
      return path.startsWith('/') ? serverURL + path : serverURL + '/' + path;
    },
    previewExamImage(path) {
      const url = this.getImageUrl(path);
      if (!url) return;
      uni.previewImage({
        urls: [url],
        current: url
      });
    },
    openErrorTypePicker(mistake) {
      uni.showActionSheet({
        itemList: this.errorTypes,
        success: async (res) => {
          const selectedType = this.errorTypes[res.tapIndex];
          if (mistake.error_type === selectedType) return; // 没改变
          
          const oldType = mistake.error_type;
          mistake.error_type = selectedType; // 乐观更新
          
          try {
            uni.showLoading({ title: '保存中...', mask: true });
            const result = await mistakeAPI.updateMistake(mistake.id, {
              error_type: selectedType
            });
            if (result.success) {
              uni.showToast({ title: '已归类', icon: 'success' });
            } else {
              throw new Error(result.message || '更新失败');
            }
          } catch (err) {
            mistake.error_type = oldType; // 失败回滚
            uni.showToast({ title: err.message || '操作失败', icon: 'none' });
          } finally {
            uni.hideLoading();
          }
        }
      });
    },
    async toggleMastery(mistake) {
      const nextValue = !mistake.is_mastered;
      const oldValue = mistake.is_mastered;
      mistake.is_mastered = nextValue;

      try {
        uni.showLoading({ title: nextValue ? '标记中...' : '更新中...', mask: true });
        const result = await mistakeAPI.updateMistake(mistake.id, {
          is_mastered: nextValue
        });
        if (!result.success) {
          throw new Error(result.message || '更新失败');
        }

        uni.showToast({
          title: nextValue ? '已标记掌握' : '已改为未掌握',
          icon: 'success'
        });

        if (nextValue && this.currentMastery === 'unmastered') {
          this.loadMistakes();
        } else if (!nextValue && this.currentMastery === 'mastered') {
          this.loadMistakes();
        }
      } catch (error) {
        mistake.is_mastered = oldValue;
        uni.showToast({ title: error.message || '操作失败', icon: 'none' });
      } finally {
        uni.hideLoading();
      }
    }
  }
};
</script>

<style lang="scss" scoped>
view, text, scroll-view, image {
  box-sizing: border-box;
}

.mistake-container {
  height: 100vh;
  width: 100vw;
  background-color: #F5F7FA;
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
}

.top-section {
  position: relative;
  z-index: 30;
  flex-shrink: 0;
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

/* 顶部导航 */
.custom-navbar {
  position: relative;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  height: 56px;
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
      font-size: 18px;
      font-weight: 700;
      color: #fff;
      letter-spacing: 0.5px;
    }
  }
  .navbar-right {
    width: 40px;
  }
}

/* 筛选面板 */
.filter-panel {
  position: relative;
  z-index: 2;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  background: linear-gradient(135deg, #3F51B5 0%, #5C6BC0 100%);
  padding: 10px 16px 14px;
  border-radius: 0 0 20px 20px;
  box-shadow: 0 8px 18px rgba(63, 81, 181, 0.16);
  margin-top: -1px;
}

.filter-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.filter-row.compact {
  align-items: center;
  margin-top: 12px;
}

.filter-label {
  width: 32px;
  line-height: 32px;
  font-size: 13px;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.92);
  flex-shrink: 0;
}

.filter-chip {
  min-width: fit-content;
  padding: 7px 14px;
  border-radius: 999px;
  font-size: 12px;
  line-height: 18px;
  color: rgba(255, 255, 255, 0.88);
  background: rgba(255, 255, 255, 0.14);
  border: 1px solid rgba(255, 255, 255, 0.18);
  flex-shrink: 0;

  &.active {
    color: #3F51B5;
    background: #FFFFFF;
    border-color: #FFFFFF;
    font-weight: 700;
    box-shadow: 0 6px 14px rgba(15, 23, 42, 0.12);
  }
}

.subject-trigger {
  flex: 1;
  min-width: 0;
  height: 38px;
  padding: 0 14px;
  border-radius: 14px;
  background: #FFFFFF;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.12);
}

.subject-trigger-text {
  flex: 1;
  min-width: 0;
  font-size: 13px;
  color: #334155;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-right: 8px;
}

.subject-picker-mask {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.2);
  z-index: 40;
}

.subject-picker-pop {
  position: fixed;
  left: 72px;
  right: 16px;
  z-index: 45;
  background: #FFFFFF;
  border-radius: 18px;
  padding: 14px;
  box-shadow: 0 18px 32px rgba(15, 23, 42, 0.18);
  max-height: min(320px, 46vh);
}

.subject-picker-scroll {
  max-height: calc(min(320px, 46vh) - 28px);
}

.subject-picker-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.subject-option {
  padding: 8px 14px;
  border-radius: 999px;
  background: #F1F5F9;
  color: #475569;
  font-size: 12px;
  line-height: 18px;

  &.active {
    background: #E0E7FF;
    color: #3F51B5;
    font-weight: 700;
  }
}

.mastery-filter {
  display: flex;
  flex: 1;
  gap: 10px;
  flex-wrap: wrap;
}

/* 列表视图 */
.mistake-list-view {
  flex: 1;
  min-height: 0;
  width: 100%;
  padding: 16px 16px 0;
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
    background: linear-gradient(135deg, #5C6BC0 0%, #3F51B5 100%);
    box-shadow: 0 8px 16px rgba(63, 81, 181, 0.2);
  }
  
  .empty-text {
    font-size: 15px;
    color: #666;
  }
}

.mistake-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-bottom: 24px;
}

.exam-group-card {
  background: linear-gradient(180deg, #FFFFFF 0%, #FAFBFF 100%);
  border-radius: 20px;
  box-shadow: 0 10px 26px rgba(63, 81, 181, 0.08);
  overflow: hidden;
  border: 1px solid rgba(92, 107, 192, 0.08);
}

.exam-group-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px;
  border-bottom: 1px solid #EEF1F7;
}

.group-main-info {
  display: flex;
  align-items: flex-start;
  flex: 1;
  min-width: 0;
}

.group-cover {
  position: relative;
  width: 58px;
  height: 74px;
  border-radius: 14px 16px 16px 14px;
  margin-right: 14px;
  flex-shrink: 0;
  box-shadow: 0 10px 22px rgba(92, 107, 192, 0.2);
  overflow: hidden;
}

.cover-binding {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 8px;
  background: rgba(255, 255, 255, 0.28);
}

.cover-content {
  height: 100%;
  padding: 10px 8px 8px 14px;
  display: flex;
  flex-direction: column;
}

.cover-subject {
  font-size: 10px;
  line-height: 1.25;
  color: #fff;
  font-weight: 700;
  word-break: break-all;
  max-height: 26px;
  overflow: hidden;
}

.cover-line {
  height: 3px;
  border-radius: 999px;
  margin-top: 6px;
  background: rgba(255, 255, 255, 0.72);
}

.cover-line-lg {
  margin-top: 10px;
}

.cover-line-short {
  width: 65%;
}

.group-texts {
  flex: 1;
  min-width: 0;
}

.group-title-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.group-title {
  display: block;
  font-size: 16px;
  font-weight: bold;
  color: #1F2937;
  line-height: 1.5;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.group-subject {
  font-size: 11px;
  color: #4F46E5;
  background: #EEF2FF;
  border-radius: 999px;
  padding: 4px 8px;
  flex-shrink: 0;
}

.group-meta-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 8px;
}

.group-date,
.group-count {
  font-size: 12px;
  color: #94A3B8;
}

.group-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: 12px;
}

.group-delete-btn,
.preview-btn {
  width: 34px;
  height: 34px;
  border-radius: 17px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.preview-btn {
  background: #EEF2FF;
}

.group-delete-btn {
  background: #FFF1F2;
}

.group-mistakes {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 14px;
  background: #F8FAFF;
}

.mistake-card {
  background: #fff;
  border-radius: 16px;
  padding: 16px;
  box-shadow: 0 6px 16px rgba(15, 23, 42, 0.04);
  border: 1px solid #EEF2F7;

  .question-meta {
    display: flex;
    flex-direction: column;
    gap: 6px;
    flex: 1;
    min-width: 0;
  }

  .meta-badges {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px;
  }

  .question-no {
    font-size: 14px;
    font-weight: bold;
    color: #DC2626;
    background: #FEF2F2;
    padding: 4px 8px;
    border-radius: 999px;
    align-self: flex-start;
  }

  .mastery-badge {
    font-size: 11px;
    color: #B45309;
    background: #FEF3C7;
    padding: 4px 8px;
    border-radius: 999px;
    align-self: flex-start;

    &.mastered {
      color: #15803D;
      background: #DCFCE7;
    }
  }

  .stem-summary {
    font-size: 12px;
    color: #64748B;
    line-height: 1.5;
  }

  .right-actions {
    display: flex;
    align-items: center;
    margin-left: 12px;
    gap: 8px;
  }
  
  .card-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    margin-bottom: 16px;
    
    .subject-badge {
      padding: 4px 10px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: bold;
      color: #fff;
      margin-right: 12px;
    }
    
    .date-text {
      flex: 1;
      font-size: 12px;
      color: #999;
    }
    
    .delete-btn {
      padding: 4px;
      border-radius: 50%;
      background: #FFF0F0;
      display: flex;
      align-items: center;
      justify-content: center;
      margin-left: 12px;
      
      &:active {
        background: #FFE5E5;
        transform: scale(0.9);
      }
    }
    
    .error-type-selector {
      display: flex;
      align-items: center;
      background: #F8FAFC;
      padding: 6px 10px;
      border-radius: 999px;
      
      .type-text {
        font-size: 11px;
        color: #999;
        margin-right: 4px;
        
        &.has-type {
          color: #5C6BC0;
          font-weight: bold;
        }
      }
      
      &:active {
        background: #E8EAF6;
      }
    }

    .mastery-toggle {
      display: flex;
      align-items: center;
      gap: 4px;
      background: #F8FAFC;
      padding: 6px 10px;
      border-radius: 999px;

      text {
        font-size: 11px;
        color: #64748B;
      }

      &.mastered {
        background: #ECFDF5;

        text {
          color: #15803D;
          font-weight: bold;
        }
      }

      &:active {
        background: #E2E8F0;
      }
    }
  }
  
  .question-content {
    margin-bottom: 16px;
    background: #F8FAFC;
    padding: 14px;
    border-radius: 12px;
    
    .q-label {
      font-size: 14px;
      font-weight: bold;
      color: #2C3E50;
      margin-bottom: 4px;
      display: block;
    }
    
    .q-text {
      font-size: 15px;
      color: #334155;
      line-height: 1.7;
    }
  }
  
  .answer-section {
    display: flex;
    flex-direction: column;
    gap: 12px;
    margin-bottom: 16px;
    
    .answer-box {
      display: flex;
      align-items: flex-start;
      background: #FCFCFD;
      border-radius: 12px;
      padding: 10px 12px;
      border: 1px solid #EEF2F7;
      
      .ans-label {
        font-size: 14px;
        color: #666;
        width: 70px;
        flex-shrink: 0;
      }
      
      .ans-text {
        font-size: 14px;
        font-weight: bold;
        flex: 1;
        
        &.wrong {
          color: #E53935;
        }
        
        &.right {
          color: #4CAF50;
        }
      }
    }
  }
  
  .explanation-section {
    background: #EEF4FF;
    padding: 14px;
    border-radius: 12px;
    border-left: 4px solid #5C6BC0;
    
    .exp-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 0;

      .exp-header-left {
        display: flex;
        align-items: center;
        gap: 6px;
      }
      
      text {
        font-size: 13px;
        font-weight: bold;
        color: #5C6BC0;
      }
    }
    
    .exp-text {
      display: block;
      font-size: 13px;
      color: #555;
      line-height: 1.5;
      margin-top: 10px;
    }
  }
}

/* 科目背景色池 */
.bg-color-0 { background: #5C6BC0; }
.bg-color-1 { background: #4F46E5; }
.bg-color-2 { background: #0EA5E9; }
.bg-color-3 { background: #F59E0B; }
</style>
