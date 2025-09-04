<template>
  <div class="dashboard-box">
    <h2 class="dashboard-title">欢迎来到 Retell AI 控制台</h2>
    <p class="dashboard-desc">这里将展示您的语音助手数据和管理功能。</p>
    <el-alert title="功能区占位，可根据需求扩展" type="info" show-icon />
  </div>
</template>

<script setup>
// 可扩展更多控制台功能
</script>

<style scoped>
.dashboard-box {
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 2px 12px rgba(79,140,255,0.08);
  width: 480px;
  margin: 100px auto;
  padding: 48px 40px;
  text-align: center;
}
.dashboard-title {
  font-size: 28px;
  font-weight: bold;
  color: #4f8cff;
  margin-bottom: 24px;
}
.dashboard-desc {
  font-size: 18px;
  color: #333;
  margin-bottom: 32px;
}
</style> 