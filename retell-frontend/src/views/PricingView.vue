<template>
  <div class="pricing-page">
    <h1>价格方案</h1>
    <div class="pricing-cards">
      <div class="pricing-card" v-for="plan in plans" :key="plan.name">
        <h2>{{ plan.name }}</h2>
        <p class="price">{{ plan.price }}</p>
        <ul>
          <li v-for="f in plan.features" :key="f">{{ f }}</li>
        </ul>
        <el-button type="primary" size="small">立即购买</el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
const plans = [
  { name: '基础版', price: '¥99/月', features: ['10000分钟语音识别', '基础对话功能', '邮件支持'] },
  { name: '专业版', price: '¥299/月', features: ['50000分钟语音识别', '高级对话引擎', '专属客服', 'API调用'] },
  { name: '企业版', price: '定制', features: ['不限时长', '定制化服务', '专属技术支持'] },
];
</script>

<style scoped>
.pricing-page {
  max-width: 1000px;
  margin: 40px auto;
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 2px 12px rgba(79,140,255,0.08);
  padding: 48px 40px;
}
.pricing-page h1 {
  color: #4f8cff;
  font-size: 32px;
  margin-bottom: 32px;
  text-align: center;
}
.pricing-cards {
  display: flex;
  justify-content: center;
  gap: 32px;
  flex-wrap: wrap;
}
.pricing-card {
  background: #f7f8fa;
  border-radius: 12px;
  box-shadow: 0 1px 6px rgba(79,140,255,0.06);
  padding: 32px 24px;
  width: 260px;
  text-align: center;
}
.pricing-card h2 {
  color: #357ae8;
  font-size: 22px;
  margin-bottom: 10px;
}
.price {
  color: #4f8cff;
  font-size: 28px;
  font-weight: bold;
  margin: 16px 0;
}
.pricing-card ul {
  list-style: none;
  padding: 0;
  margin: 16px 0;
}
.pricing-card li {
  color: #333;
  font-size: 15px;
  margin-bottom: 8px;
}
</style> 