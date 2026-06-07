<template>
  <view class="exam-analysis-container" :class="{ 'has-result': !!currentAnalysis }">
    <!-- 顶部导航栏 (保持与首页一致的设计语言) -->
    <view class="custom-navbar" :style="{ paddingTop: statusBarHeight + 'px' }">
      <view class="navbar-left" @tap="goBack">
        <uni-icons type="back" size="24" color="#fff" />
      </view>
      <view class="navbar-title-container">
        <text class="navbar-title">拍照批改</text>
      </view>
      <view class="navbar-right"></view>
    </view>

    <!-- 背景装饰 -->
    <view class="bg-shape shape-1"></view>
    <view class="bg-shape shape-2"></view>

    <!-- 内容区域 -->
    <scroll-view class="content-wrapper" scroll-y :style="{ height: `calc(100vh - ${statusBarHeight + 44}px)` }">
      
      <!-- 状态 1: 上传试卷区域 -->
      <view class="upload-section" v-if="!currentAnalysis && !isAnalyzing">
        <view class="top-hero upload-hero">
          <view class="welcome-text">
            <text class="main-title">哪里不会拍哪里</text>
            <text class="sub-title">小伴智能批改，帮你找出知识薄弱点</text>
          </view>
        </view>

        <view class="content-panel upload-panel">
          <view class="upload-card">
            <view class="input-group">
              <text class="input-label">试卷/作业名称</text>
              <input class="custom-input" v-model="examForm.examName" placeholder="例如：期中数学测试卷" placeholder-class="placeholder-style" />
            </view>
            
            <view class="upload-area">
              <text class="input-label">上传照片</text>
              <view class="exam-preview" v-if="examForm.imagePreview" @click="captureImage">
                <image :src="examForm.imagePreview" class="exam-image" mode="aspectFill" />
                <view class="re-upload-mask">
                  <uni-icons type="camera-filled" size="24" color="#fff" />
                  <text>点击重新上传</text>
                </view>
              </view>
              <view class="upload-placeholder" v-else @click="captureImage">
                <view class="icon-circle">
                  <uni-icons type="camera-filled" size="36" color="#3F51B5" />
                </view>
                <text class="upload-text">点击拍照或相册选择</text>
                <text class="upload-desc">请确保画面清晰、光线明亮</text>
                <text class="upload-tip">仅支持试卷、作业、练习题等可批改学习图片</text>
              </view>
            </view>
            
            <button class="primary-btn" @click="analyzeExam" :class="{'disabled': !examForm.imagePreview || !examForm.examName || isSubmitting}">
              <uni-icons type="paperplane-filled" size="18" color="#fff" style="margin-right: 6px;"></uni-icons>
              <text>{{ isSubmitting ? '上传中...' : '开始智能批改' }}</text>
            </button>
          </view>

          <!-- 历史记录入口卡片 -->
          <view class="history-entry-card" v-if="examAnalyses.length > 0">
            <view class="history-header">
              <view class="title-with-icon">
                <uni-icons type="list" size="20" color="#333" />
                <text class="history-title">批改记录与状态</text>
              </view>
              <view class="refresh-btn" @click="loadExamAnalyses">
                <uni-icons type="loop" size="16" color="#888" />
              </view>
            </view>
            <view class="history-list">
              <view class="history-item" v-for="(analysis, index) in examAnalyses.slice(0, 2)" :key="analysis.id" @click="viewAnalysis(analysis.id, analysis.status)">
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
                  <!-- 状态标识 -->
                  <view class="status-container">
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
            <!-- 查看全部按钮 -->
            <view class="view-all-btn" v-if="examAnalyses.length > 2" @click="goToHistory">
              <text>查看全部分类记录</text>
              <uni-icons type="arrow-right" size="14" color="#5C6BC0" />
            </view>
          </view>
        </view>
      </view>

      <!-- 状态 2: 分析结果展示 -->
      <view class="result-section" v-if="currentAnalysis">
        <view class="top-hero result-hero">
          <view class="result-header-card">
            <view class="result-title-area">
              <view class="title-row">
                <text class="result-exam-name">{{ currentAnalysis.exam_name }}</text>
                <view class="subject-badge" v-if="currentAnalysis.subject">
                  <text>{{ currentAnalysis.subject }}</text>
                </view>
              </view>
              <text class="result-date">批改时间: {{ formatDate(currentAnalysis.created_at) }}</text>
            </view>
            
            <!-- 试卷原图缩略图 -->
            <view class="exam-thumbnail" v-if="currentAnalysis.exam_image_path" @click="previewImage(currentAnalysis.exam_image_path)">
              <image :src="getImageUrl(currentAnalysis.exam_image_path)" mode="aspectFill" class="thumbnail-img"></image>
              <view class="zoom-icon-mask">
                <uni-icons type="search" size="14" color="#fff" />
              </view>
            </view>
          </view>
        </view>

        <view class="content-panel result-panel">
          <view class="overview-card">
            <view class="overview-header">
              <text class="overview-title">本次诊断概览</text>
              <text class="overview-subtitle">点开下方卡片查看详细内容</text>
            </view>
            <view class="overview-grid">
              <view class="overview-item">
                <text class="overview-value">{{ (currentAnalysis.marks && currentAnalysis.marks.length) || 0 }}</text>
                <text class="overview-label">错题</text>
              </view>
              <view class="overview-item">
                <text class="overview-value orange">{{ (currentAnalysis.weak_points && currentAnalysis.weak_points.length) || 0 }}</text>
                <text class="overview-label">薄弱点</text>
              </view>
              <view class="overview-item">
                <text class="overview-value green">{{ (currentAnalysis.suggestions && currentAnalysis.suggestions.length) || 0 }}</text>
                <text class="overview-label">建议</text>
              </view>
            </view>
          </view>

          <!-- 错题详情展示区域 -->
          <view class="analysis-card image-mark-card" v-if="currentAnalysis.exam_image_path">
            <view class="card-header-styled collapsible-header" @click="toggleSection('mistakes')">
              <view class="header-left">
                <view class="header-icon bg-blue">
                  <uni-icons type="info" size="18" color="#fff" />
                </view>
                <text class="card-title">错题详情</text>
              </view>
              <uni-icons :type="expandedSections.mistakes ? 'top' : 'bottom'" size="18" color="#94A3B8" />
            </view>

            <view v-if="expandedSections.mistakes" class="analysis-card-body">
              <!-- 全对状态提示 -->
              <view v-if="!currentAnalysis.marks || currentAnalysis.marks.length === 0" class="perfect-score-banner">
                <uni-icons type="medal-filled" size="24" color="#4CAF50" />
                <text>太棒了！小伴老师没有在这张卷子上发现任何错误！</text>
              </view>

              <!-- 错题列表 -->
              <view v-else class="error-descriptions">
                <view v-for="(mark, index) in currentAnalysis.marks" :key="'desc-'+index" class="error-desc-item">
                  <view class="error-number-small">{{ index + 1 }}</view>
                  <view class="error-content-box">
                    <view class="error-head-row">
                      <text class="error-qno">{{ mark.question_no || '未知题号' }}</text>
                      <text class="error-summary" v-if="mark.stem_summary">{{ mark.stem_summary }}</text>
                    </view>
                    <text class="error-answer" v-if="mark.correct_answer">正确答案：{{ mark.correct_answer }}</text>
                    <text class="error-thinking" v-if="mark.thinking_hint">思路：{{ mark.thinking_hint }}</text>
                    <text class="error-text" v-if="!mark.correct_answer && !mark.thinking_hint">{{ mark.error_text || '此处存在错误' }}</text>
                  </view>
                </view>
              </view>
            </view>
          </view>

          <!-- 知识薄弱点 -->
          <view class="analysis-card weak-card">
            <view class="card-header-styled collapsible-header" @click="toggleSection('weakPoints')">
              <view class="header-left">
                <view class="header-icon bg-orange">
                  <uni-icons type="flag-filled" size="18" color="#fff" />
                </view>
                <text class="card-title">知识薄弱点诊断</text>
              </view>
              <uni-icons :type="expandedSections.weakPoints ? 'top' : 'bottom'" size="18" color="#94A3B8" />
            </view>

            <view v-if="expandedSections.weakPoints" class="analysis-card-body">
              <view v-if="!currentAnalysis.weak_points || currentAnalysis.weak_points.length === 0" class="empty-state">
                <text>太棒了！未检测到明显的知识薄弱点 🎉</text>
              </view>
              <view v-else class="points-list">
                <view v-for="(point, index) in currentAnalysis.weak_points" :key="index" class="point-item">
                  <view class="point-index">{{ index + 1 }}</view>
                  <text class="point-text">{{ point }}</text>
                </view>
              </view>
            </view>
          </view>

          <!-- 学习建议 -->
          <view class="analysis-card suggest-card">
            <view class="card-header-styled collapsible-header" @click="toggleSection('suggestions')">
              <view class="header-left">
                <view class="header-icon bg-green">
                  <uni-icons type="hand-up-filled" size="18" color="#fff" />
                </view>
                <text class="card-title">小伴老师的建议</text>
              </view>
              <uni-icons :type="expandedSections.suggestions ? 'top' : 'bottom'" size="18" color="#94A3B8" />
            </view>

            <view v-if="expandedSections.suggestions" class="analysis-card-body">
              <view v-if="!currentAnalysis.suggestions || currentAnalysis.suggestions.length === 0" class="empty-state">
                <text>继续保持当前的学习状态！</text>
              </view>
              <view v-else class="points-list">
                <view v-for="(suggestion, index) in currentAnalysis.suggestions" :key="index" class="point-item">
                  <view class="point-index green-index">{{ index + 1 }}</view>
                  <text class="point-text">{{ suggestion }}</text>
                </view>
              </view>
            </view>
          </view>

          <view class="result-footer">
            <view class="footer-hint-card">
              <text class="footer-hint-title">复习提醒</text>
              <text class="footer-tip">错题已自动收录至「智能错题本」，建议先看错题详情，再按薄弱点逐项复习。</text>
            </view>
            <button class="secondary-btn" @click="currentAnalysis = null">
              <text>批改下一份</text>
            </button>
          </view>
        </view>
      </view>

    </scroll-view>
  </view>
</template>

<script>
import { examAPI, serverURL } from '@/api/index.js';

export default {
  data() {
    return {
      statusBarHeight: uni.getSystemInfoSync().statusBarHeight,
      currentAnalysis: null,
      examForm: {
        examName: '',
        imagePreview: ''
      },
      isSubmitting: false, // 替换了原来的 isAnalyzing，仅表示上传过程
      examAnalyses: [],
      userInfo: {
        username: uni.getStorageSync('user') ? JSON.parse(uni.getStorageSync('user')).username : ''
      },
      pollTimer: null, // 用于存储轮询定时器
      fromHistory: false, // 标记是否是从历史页面跳转过来的
      expandedSections: {
        mistakes: false,
        weakPoints: false,
        suggestions: false
      }
    };
  },
  onLoad() {
    this.loadExamAnalyses();
  },
  onShow() {
    // 检查是否有从历史页面传回来的需要展示的分析ID
    const viewId = uni.getStorageSync('view_analysis_id');
    if (viewId) {
      uni.removeStorageSync('view_analysis_id'); // 清除标志
      
      // 检查是否是从历史页面来的标志
      if (uni.getStorageSync('from_history')) {
        this.fromHistory = true;
        uni.removeStorageSync('from_history');
      }
      
      this.viewAnalysis(viewId, 'completed'); // 从历史点进来的肯定是已完成的
    } else {
      // 重新检查是否需要恢复轮询
      this.checkAndStartPolling();
    }
  },
  onHide() {
    this.stopPolling(); // 页面隐藏时停止轮询，节省资源
  },
  onUnload() {
    this.stopPolling(); // 页面销毁时停止轮询
  },
  methods: {
    checkAndStartPolling() {
      // 检查列表中是否有正在处理中的记录
      const hasPending = this.examAnalyses.some(item => ['pending', 'extracting_mistakes', 'generating_exercises'].includes(item.status));
      if (hasPending) {
        this.startPolling();
      } else {
        this.stopPolling();
      }
    },
    startPolling() {
      if (this.pollTimer) return; // 如果已经在轮询，则不重复开启
      
      console.log('开始轮询分析状态...');
      // 每隔 3 秒静默刷新一次列表
      this.pollTimer = setInterval(async () => {
        if (!this.userInfo.username) return;
        try {
          const res = await examAPI.getHistory(this.userInfo.username);
          if (res.success) {
            // 比较是否有状态从 pending 变成了 其他状态
            const prevPending = this.examAnalyses.filter(i => i.status === 'pending').map(i => i.id);
            this.examAnalyses = res.data;
            
            const currentPending = this.examAnalyses.filter(i => i.status === 'pending').map(i => i.id);
            
            // 如果有记录完成了初步分析
            if (prevPending.length > currentPending.length) {
              uni.showToast({
                title: '有试卷批改完成啦！可以点击查看',
                icon: 'none'
              });
            }
            
            // 再次检查是否还需要继续轮询
            const hasAnyProcessing = this.examAnalyses.some(item => ['pending', 'extracting_mistakes', 'generating_exercises'].includes(item.status));
            if (!hasAnyProcessing) {
              this.stopPolling();
            }
          }
        } catch (error) {
          console.error('轮询历史记录失败:', error);
        }
      }, 3000);
    },
    stopPolling() {
      if (this.pollTimer) {
        clearInterval(this.pollTimer);
        this.pollTimer = null;
        console.log('已停止轮询');
      }
    },
    goToHistory() {
      uni.navigateTo({ url: '/pages/exam-history/exam-history' });
    },
    resetExpandedSections() {
      this.expandedSections = {
        mistakes: false,
        weakPoints: false,
        suggestions: false
      };
    },
    toggleSection(section) {
      this.$set(this.expandedSections, section, !this.expandedSections[section]);
    },
    captureImage() {
      uni.chooseImage({
        count: 1,
        sourceType: ['camera', 'album'],
        success: (res) => {
          this.examForm.imagePreview = res.tempFilePaths[0];
        },
        fail: (err) => {
          console.error('拍照/选择图片失败:', err);
        }
      });
    },
    goBack() {
      // 如果当前正在查看分析详情卡片
      if (this.currentAnalysis) {
        // 如果是从历史记录页面跳转过来的，那么关闭详情后应该直接返回历史记录页面
        if (this.fromHistory) {
          this.currentAnalysis = null;
          this.fromHistory = false;
          this.resetExpandedSections();
          uni.navigateBack({
            delta: 1
          });
        } else {
          // 如果是从本页面上传列表点进来的，只关闭详情卡片，留在本页面
          this.currentAnalysis = null;
          this.resetExpandedSections();
        }
      } else {
        // 如果已经在最顶层的上传界面，则返回上一页（如首页）
        uni.navigateBack({
          delta: 1,
          fail: () => {
            uni.switchTab({ url: '/pages/home/home' });
          }
        });
      }
    },
    async analyzeExam() {
      if (!this.examForm.examName || !this.examForm.imagePreview || this.isSubmitting) return;

      this.isSubmitting = true;
      
      try {
        let fileData;
        
        // 跨平台统一的 Base64 转换方法
        // 尝试判断运行环境
        // #ifdef H5
        // H5 端使用 fetch
        const response = await fetch(this.examForm.imagePreview);
        const blob = await response.blob();
        fileData = await new Promise((resolve, reject) => {
          const reader = new FileReader();
          reader.onload = () => resolve(reader.result);
          reader.onerror = reject;
          reader.readAsDataURL(blob);
        });
        // #endif

        // #ifdef MP-WEIXIN || MP-ALIPAY || MP-BAIDU || MP-TOUTIAO || MP-QQ
        // 小程序端使用 FileSystemManager
        const fileManager = uni.getFileSystemManager();
        const file = await new Promise((resolve, reject) => {
          fileManager.readFile({
            filePath: this.examForm.imagePreview,
            encoding: 'base64',
            success: resolve,
            fail: reject
          });
        });
        fileData = `data:image/jpeg;base64,${file.data}`;
        // #endif

        // #ifdef APP-PLUS
        // App 端原生使用 plus.io (需要判断 plus 是否准备好)
        fileData = await new Promise((resolve, reject) => {
          plus.io.resolveLocalFileSystemURL(this.examForm.imagePreview, (entry) => {
            entry.file((file) => {
              const fileReader = new plus.io.FileReader();
              fileReader.onloadend = (evt) => {
                resolve(evt.target.result);
              };
              fileReader.readAsDataURL(file);
            }, (err) => reject(err));
          }, (err) => reject(err));
        });
        // #endif

        // 万一所有条件编译都没命中（如其他未定义平台），或者由于某些原因没赋值成功
        // 提供一个通用的退路：使用 uni.request 转换为 arraybuffer 后手动转 base64
        if (!fileData) {
          const resArrayBuffer = await new Promise((resolve, reject) => {
            uni.request({
              url: this.examForm.imagePreview,
              method: 'GET',
              responseType: 'arraybuffer',
              success: (res) => {
                if (res.statusCode === 200) {
                  resolve(res.data);
                } else {
                  reject(new Error('读取文件失败'));
                }
              },
              fail: reject
            });
          });
          const base64Str = uni.arrayBufferToBase64(resArrayBuffer);
          fileData = `data:image/jpeg;base64,${base64Str}`;
        }

        const formData = {
          examName: this.examForm.examName,
          imageData: fileData,
          username: this.userInfo.username
        };

        // 仅上传，不等待分析完成
        const res = await examAPI.uploadExamPaper(formData);
        
        if (res.success) {
          uni.showToast({
            title: '上传成功！小伴正在后台为您批改',
            icon: 'none',
            duration: 3000
          });
          
          // 清空表单，刷新历史列表
          this.examForm = { examName: '', imagePreview: '' };
          this.loadExamAnalyses();
        } else {
          if (res.code === 'UNSUPPORTED_EXAM_IMAGE') {
            const reason = res.data && res.data.reason ? `\n\n识别结果：${res.data.reason}` : '';
            uni.showModal({
              title: '暂不支持该图片',
              content: `${res.message || '请上传试卷、作业或练习题图片'}${reason}`,
              showCancel: false,
              confirmText: '我知道了'
            });
            return;
          }
          throw new Error(res.message || '批改请求失败');
        }
      } catch (error) {
        uni.showToast({
          title: error.message || '上传失败，请重试',
          icon: 'none'
        });
      } finally {
        this.isSubmitting = false;
      }
    },
    async loadExamAnalyses() {
      if (!this.userInfo.username) return;
      try {
        const res = await examAPI.getHistory(this.userInfo.username);
        if (res.success) {
          this.examAnalyses = res.data;
          this.checkAndStartPolling(); // 检查是否有正在分析中的记录并按需开启轮询
        }
      } catch (error) {
        console.error('获取历史记录失败:', error);
      }
    },
    async viewAnalysis(analysisId, status) {
      if (status === 'pending') {
        uni.showToast({
          title: '小伴还在努力批改中，请稍后再来看哦~',
          icon: 'none'
        });
        // 点击时顺便刷新一下列表状态
        this.loadExamAnalyses();
        return;
      }
      if (status === 'failed') {
        uni.showToast({ title: '抱歉，该次批改失败，请重新上传', icon: 'none' });
        return;
      }
      
      try {
        uni.showLoading({ title: '加载结果...' });
        const res = await examAPI.getAnalysisResult(String(analysisId));
        if (res.success) {
          this.currentAnalysis = res.data;
          this.resetExpandedSections();
          
          // 如果当前还在后台处理中，给出提示
          if (status === 'extracting_mistakes' || status === 'generating_exercises') {
            setTimeout(() => {
              uni.showToast({
                title: '批改结果已出！小伴正在后台为您整理错题和生成练习~',
                icon: 'none',
                duration: 3000
              });
            }, 500);
          }
        }
      } catch (error) {
        uni.showToast({ title: '获取详情失败', icon: 'none' });
      } finally {
        uni.hideLoading();
      }
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
                // 如果删除的是当前正在查看的记录，则重置查看状态
                if (this.currentAnalysis && this.currentAnalysis.id === analysisId) {
                  this.currentAnalysis = null;
                }
                // 重新加载列表以更新数据
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
    getImageUrl(path) {
      if (!path) return '';
      if (path.startsWith('http')) return path;
      return path.startsWith('/') ? serverURL + path : serverURL + '/' + path;
    },
    previewImage(path) {
      const url = this.getImageUrl(path);
      if (!url) return;
      uni.previewImage({
        urls: [url],
        current: url
      });
    }
  }
};
</script>

<style lang="scss" scoped>
view, text, scroll-view, image, input {
  box-sizing: border-box;
}

.exam-analysis-container {
  height: 100vh;
  width: 100vw;
  background-color: #F5F7FA;
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;

  &.has-result {
    .shape-1 {
      height: 205px;
      border-radius: 0 0 28px 28px;
    }
  }
}

/* 顶部背景与导航 */
.custom-navbar {
  position: relative;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  height: 44px;
  background: transparent;
  
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

/* 顶部紫色渐变背景与装饰 */
.bg-shape {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 138px;
  background: linear-gradient(135deg, #3F51B5 0%, #5C6BC0 100%);
  border-radius: 0 0 24px 24px;
  z-index: 0;
}
.shape-1 {
  background: linear-gradient(135deg, #3F51B5 0%, #5C6BC0 100%);
}
.shape-2 {
  width: 200px;
  height: 200px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.1);
  filter: blur(30px);
  top: -50px;
  right: -50px;
  z-index: 1;
}

.content-wrapper {
  flex: 1;
  position: relative;
  z-index: 5;
}

.top-hero {
  position: relative;
  z-index: 2;
}

.content-panel {
  position: relative;
  z-index: 2;
}

/* --- 状态1: 上传区样式 --- */
.upload-section {
  padding: 12px 16px 40px;
  
  .upload-hero {
    padding: 10px 6px 0;
  }

  .welcome-text {
    display: flex;
    flex-direction: column;
    color: #fff;
    
    .main-title {
      font-size: 24px;
      font-weight: 800;
      margin-bottom: 6px;
    }
    .sub-title {
      font-size: 13px;
      opacity: 0.85;
    }
  }

  .upload-panel {
    margin-top: 28px;
  }
}

.upload-card {
  background: #fff;
  border-radius: 20px;
  padding: 24px 20px;
  box-shadow: 0 8px 24px rgba(63, 81, 181, 0.08);
  margin-bottom: 24px;
  
  .input-group, .upload-area {
    margin-bottom: 20px;
    
    .input-label {
      display: block;
      font-size: 14px;
      font-weight: bold;
      color: #333;
      margin-bottom: 10px;
    }
  }
  
  .custom-input {
    background: #F8F9FA;
    height: 48px;
    border-radius: 12px;
    padding: 0 16px;
    font-size: 15px;
    color: #333;
  }
  .placeholder-style {
    color: #BDBDBD;
  }
  
  .upload-placeholder {
    height: 160px;
    background: #F8F9FA;
    border: 2px dashed #E0E0E0;
    border-radius: 16px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    transition: all 0.2s;
    
    &:active {
      background: #F0F2F5;
      border-color: #3F51B5;
    }
    
    .icon-circle {
      width: 56px;
      height: 56px;
      border-radius: 28px;
      background: rgba(63, 81, 181, 0.1);
      display: flex;
      align-items: center;
      justify-content: center;
      margin-bottom: 12px;
    }
    
    .upload-text {
      font-size: 15px;
      font-weight: bold;
      color: #333;
      margin-bottom: 4px;
    }
    .upload-desc {
      font-size: 12px;
      color: #999;
    }

    .upload-tip {
      margin-top: 8px;
      font-size: 12px;
      color: #5C6BC0;
      background: rgba(92, 107, 192, 0.08);
      padding: 6px 10px;
      border-radius: 999px;
    }
  }
  
  .exam-preview {
    position: relative;
    height: 200px;
    border-radius: 16px;
    overflow: hidden;
    background: #000;
    
    .exam-image {
      width: 100%;
      height: 100%;
      opacity: 0.8;
    }
    
    .re-upload-mask {
      position: absolute;
      top: 0; left: 0; right: 0; bottom: 0;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      background: rgba(0, 0, 0, 0.4);
      opacity: 0;
      transition: opacity 0.3s;
      
      text {
        color: #fff;
        font-size: 14px;
        margin-top: 8px;
        font-weight: bold;
      }
    }
    
    &:active .re-upload-mask {
      opacity: 1;
    }
  }
  
  .primary-btn {
    width: 100%;
    height: 50px;
    border-radius: 25px;
    background: linear-gradient(135deg, #5C6BC0 0%, #3F51B5 100%);
    color: #fff;
    font-size: 16px;
    font-weight: bold;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 6px 16px rgba(63, 81, 181, 0.3);
    transition: all 0.3s;
    
    &.disabled {
      background: #E0E0E0;
      box-shadow: none;
      color: #999;
    }
    
    &:active:not(.disabled) {
      transform: scale(0.97);
      box-shadow: 0 2px 8px rgba(63, 81, 181, 0.2);
    }
  }
}

.history-entry-card {
  background: #fff;
  border-radius: 16px;
  padding: 16px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
  
  .history-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
    
    .title-with-icon {
      display: flex;
      align-items: center;
      gap: 6px;
      .history-title {
        font-size: 15px;
        font-weight: bold;
        color: #333;
      }
    }
    .refresh-btn {
      padding: 4px;
    }
  }
  
  .history-list {
    .history-item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 12px 0;
      border-bottom: 1px solid #F5F5F5;
      
      &:last-child {
        border-bottom: none;
        padding-bottom: 0;
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
          color: #fff;
          font-size: 18px;
          font-weight: bold;
          
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
              max-width: 140px;
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
  }

  .view-all-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    padding-top: 12px;
    margin-top: 12px;
    border-top: 1px solid #F0F2F5;
    
    text {
      font-size: 13px;
      color: #5C6BC0;
      font-weight: 500;
      margin-right: 4px;
    }
    
    &:active {
      opacity: 0.7;
    }
  }
}

/* --- 状态2: 分析中动画 --- */
.analyzing-section {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 60vh;
  padding: 0 20px;
  
  .analyzing-card {
    background: #fff;
    width: 100%;
    border-radius: 24px;
    padding: 40px 20px;
    display: flex;
    flex-direction: column;
    align-items: center;
    box-shadow: 0 8px 30px rgba(0, 0, 0, 0.05);
    
    .radar-animation {
      position: relative;
      width: 100px;
      height: 100px;
      display: flex;
      align-items: center;
      justify-content: center;
      margin-bottom: 24px;
      
      .scan-icon {
        position: relative;
        z-index: 2;
      }
      
      .radar-circle {
        position: absolute;
        width: 100%;
        height: 100%;
        border-radius: 50%;
        border: 2px solid #3F51B5;
        opacity: 0;
        animation: radar-wave 2s infinite cubic-bezier(0.36, 0.11, 0.89, 0.32);
        
        &.delay-1 { animation-delay: 0.6s; }
        &.delay-2 { animation-delay: 1.2s; }
      }
    }
    
    .analyzing-title {
      font-size: 18px;
      font-weight: bold;
      color: #333;
      margin-bottom: 8px;
    }
    .analyzing-desc {
      font-size: 13px;
      color: #888;
      margin-bottom: 24px;
    }
    
    .progress-bar-container {
      width: 80%;
      height: 6px;
      background: #F0F2F5;
      border-radius: 3px;
      overflow: hidden;
      margin-bottom: 8px;
      
      .progress-bar {
        height: 100%;
        background: linear-gradient(90deg, #5C6BC0 0%, #3F51B5 100%);
        border-radius: 3px;
        transition: width 0.3s ease;
      }
    }
    
    .progress-text {
      font-size: 12px;
      color: #3F51B5;
      font-weight: bold;
    }
  }
}

@keyframes radar-wave {
  0% { transform: scale(0.5); opacity: 0.8; }
  100% { transform: scale(2); opacity: 0; }
}

/* --- 状态3: 结果展示 --- */
.result-section {
  padding: 16px 16px 20px;

  .result-hero {
    padding-top: 6px;
  }
  
  .result-header-card {
    background: #fff;
    border-radius: 16px;
    padding: 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
    
    .result-title-area {
      display: flex;
      flex-direction: column;
      flex: 1;
      margin-right: 12px;
      
      .title-row {
        display: flex;
        align-items: center;
        margin-bottom: 8px;
        flex-wrap: wrap;
        gap: 8px;
        
        .result-exam-name {
          font-size: 18px;
          font-weight: bold;
          color: #333;
          max-width: 100%;
          word-break: break-all;
        }
        
        .subject-badge {
          background: rgba(63, 81, 181, 0.1);
          color: #3F51B5;
          padding: 2px 8px;
          border-radius: 12px;
          font-size: 11px;
          font-weight: bold;
        }
      }

      .result-date {
        font-size: 12px;
        color: #888;
      }
    }
    
    .exam-thumbnail {
      position: relative;
      width: 60px;
      height: 80px;
      border-radius: 8px;
      overflow: hidden;
      flex-shrink: 0;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
      border: 1px solid #F0F2F5;
      
      .thumbnail-img {
        width: 100%;
        height: 100%;
        display: block;
      }
      
      .zoom-icon-mask {
        position: absolute;
        bottom: 0;
        right: 0;
        width: 24px;
        height: 24px;
        background: rgba(0, 0, 0, 0.5);
        border-top-left-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
      }
      
      &:active {
        opacity: 0.8;
      }
    }
  }

  .result-panel {
    margin-top: 30px;
  }

  .overview-card {
    background: linear-gradient(135deg, #FFFFFF 0%, #F7F9FF 100%);
    border-radius: 18px;
    padding: 16px;
    margin-bottom: 14px;
    box-shadow: 0 6px 18px rgba(63, 81, 181, 0.06);
    border: 1px solid rgba(92, 107, 192, 0.08);

    .overview-header {
      display: flex;
      align-items: flex-end;
      justify-content: space-between;
      margin-bottom: 14px;
      gap: 12px;
    }

    .overview-title {
      font-size: 15px;
      font-weight: 700;
      color: #1F2937;
    }

    .overview-subtitle {
      font-size: 11px;
      color: #94A3B8;
      text-align: right;
    }

    .overview-grid {
      display: flex;
      gap: 10px;
    }

    .overview-item {
      flex: 1;
      background: #fff;
      border-radius: 14px;
      padding: 14px 10px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      box-shadow: inset 0 0 0 1px #EEF2FF;
    }

    .overview-value {
      font-size: 24px;
      line-height: 1;
      font-weight: 800;
      color: #3F51B5;
      margin-bottom: 8px;

      &.orange {
        color: #F59E0B;
      }

      &.green {
        color: #43A047;
      }
    }

    .overview-label {
      font-size: 12px;
      color: #64748B;
      font-weight: 600;
    }
  }
  
  .analysis-card {
    background: #fff;
    border-radius: 16px;
    padding: 16px;
    margin-bottom: 14px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
    
    .card-header-styled {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 0;
      position: relative;
      min-height: 36px;

      .header-left {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 10px;
        flex: 1;
        padding: 0 28px;
      }
      
      .header-icon {
        width: 32px;
        height: 32px;
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        
        &.bg-orange { background: linear-gradient(135deg, #FFCA28, #FF8F00); }
        &.bg-green { background: linear-gradient(135deg, #66BB6A, #43A047); }
        &.bg-blue { background: linear-gradient(135deg, #64B5F6, #1E88E5); }
      }
      
      .card-title {
        font-size: 16px;
        font-weight: bold;
        color: #333;
      }
    }

    .collapsible-header {
      padding: 2px 0;

      &:active {
        opacity: 0.75;
      }
    }

    .analysis-card-body {
      margin-top: 20px;
    }
    
    /* 原图打分样式 */
    &.image-mark-card {
      .perfect-score-banner {
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 24px;
        background: #E8F5E9;
        border-radius: 12px;
        
        text {
          color: #2E7D32;
          font-size: 15px;
          font-weight: bold;
          margin-left: 8px;
        }
      }
  
      .error-descriptions {
        display: flex;
        flex-direction: column;
        gap: 12px;
        
        .error-desc-item {
          display: flex;
          align-items: flex-start;
          background: linear-gradient(180deg, #FFF8F8 0%, #FFFFFF 100%);
          padding: 14px;
          border-radius: 14px;
          border: 1px solid #FFEBEE;
          
          .error-number-small {
            background: #E53935;
            color: #fff;
            font-size: 13px;
            font-weight: bold;
            width: 24px;
            height: 24px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
            margin-right: 12px;
          }
          
          .error-content-box {
            display: flex;
            flex-direction: column;
            flex: 1;

            .error-head-row {
              display: flex;
              align-items: center;
              flex-wrap: wrap;
              gap: 8px;
              margin-bottom: 8px;
            }
            
            .error-qno {
              font-size: 15px;
              font-weight: bold;
              color: #D32F2F;
            }

            .error-summary {
              font-size: 12px;
              color: #8C8C8C;
              background: #FFF1F1;
              padding: 4px 8px;
              border-radius: 999px;
            }

            .error-answer,
            .error-thinking {
              font-size: 14px;
              color: #444;
              line-height: 1.6;
            }

            .error-answer {
              color: #1B5E20;
              font-weight: 600;
              margin-bottom: 4px;
            }

            .error-thinking {
              color: #555;
            }
            
            .error-text {
              font-size: 14px;
              color: #444;
              line-height: 1.6;
            }
          }
        }
      }
    }

    .empty-state {
      padding: 16px 14px;
      text-align: center;
      background: #F8F9FA;
      border-radius: 12px;
      color: #666;
      font-size: 13px;
    }
    
    .points-list {
      display: flex;
      flex-direction: column;
      gap: 10px;
      margin-top: 2px;
      
      .point-item {
        display: flex;
        align-items: center;
        gap: 12px;
        background: #F8F9FA;
        padding: 12px 14px;
        border-radius: 12px;
        text-align: center;
        
        .point-index {
          width: 24px;
          height: 24px;
          border-radius: 12px;
          background: #FFE0B2;
          color: #F57C00;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 12px;
          font-weight: bold;
          flex-shrink: 0;
          
          &.green-index {
            background: #C8E6C9;
            color: #388E3C;
          }
        }
        
        .point-text {
          font-size: 14px;
          color: #444;
          line-height: 1.6;
          flex: 1;
          text-align: center;
        }
      }
    }
  }
  
  .result-footer {
    display: flex;
    flex-direction: column;
    align-items: center;
    margin-top: 8px;

    .footer-hint-card {
      width: 100%;
      background: linear-gradient(135deg, #F7F8FE 0%, #FFFFFF 100%);
      border-radius: 16px;
      padding: 16px;
      margin-bottom: 14px;
      border: 1px solid rgba(92, 107, 192, 0.08);
    }

    .footer-hint-title {
      display: block;
      font-size: 14px;
      font-weight: 700;
      color: #3F51B5;
      margin-bottom: 6px;
    }
    
    .footer-tip {
      font-size: 12px;
      color: #7C8597;
      line-height: 1.7;
      text-align: center;
    }
    
    .secondary-btn {
      width: 220px;
      height: 44px;
      border-radius: 22px;
      background: #fff;
      border: 1px solid #3F51B5;
      color: #3F51B5;
      font-size: 15px;
      font-weight: bold;
      display: flex;
      align-items: center;
      justify-content: center;
      
      &:active {
        background: #F5F7FA;
      }
    }
  }
}
</style>
