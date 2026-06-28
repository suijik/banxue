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
        
        <!-- 极简数据展示（使用统计接口，增加加载状态） -->
        <view class="stats-row">
          <view class="stat-item" v-if="!statsLoading">
            <text class="stat-num">{{ userInfo.fixedMistakes }}</text>
            <text class="stat-label">累计错题</text>
          </view>
          <view class="stat-item" v-else>
            <text class="stat-num">--</text>
            <text class="stat-label">加载中</text>
          </view>
          <view class="divider"></view>
          <view class="stat-item" v-if="!statsLoading">
            <text class="stat-num">{{ userInfo.masteredMistakes }}</text>
            <text class="stat-label">已掌握错题</text>
          </view>
          <view class="stat-item" v-else>
            <text class="stat-num">--</text>
            <text class="stat-label">加载中</text>
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