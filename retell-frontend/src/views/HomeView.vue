<template>
  <div class="home-hero" data-aos="fade-up">
    <div class="hero-content">
      <div class="hero-text">
        <h1 class="home-title animate__animated animate__fadeInDown">AI 智能语音助手平台</h1>
        <p class="home-desc animate__animated animate__fadeIn animate__delay-1s">高效、自然的语音交互体验，赋能中国企业与个人。</p>
        <el-button class="hero-btn animate__animated animate__pulse animate__infinite" type="primary" size="large" @click="$router.push('/login')">立即体验</el-button>
      </div>
      <div class="hero-illustration">
        <div ref="lottieContainer" class="lottie-box"></div>
      </div>
    </div>
  </div>
  <div class="features">
    <div class="feature-card" v-for="f in features" :key="f.title" data-aos="fade-up">
      <h3>{{ f.title }}</h3>
      <p>{{ f.desc }}</p>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue';
import lottie from 'lottie-web';
const features = [
  { title: '实时语音识别', desc: '基于领先的 AI 技术，快速准确地将语音转为文字。' },
  { title: '多场景适用', desc: '支持客服、会议、教育等多种应用场景，灵活集成。' },
  { title: '数据安全保障', desc: '严格的数据加密与隐私保护，符合中国法律法规。' },
];
const lottieContainer = ref(null);
onMounted(() => {
  lottie.loadAnimation({
    container: lottieContainer.value,
    renderer: 'svg',
    loop: true,
    autoplay: true,
    // 可替换为本地或网络上的 Lottie 动画 JSON 文件
    path: 'https://assets10.lottiefiles.com/packages/lf20_4kx2q32n.json',
  });
});
</script>

<style scoped>
.home-hero {
  background: linear-gradient(120deg, #4f8cff 0%, #6fd6ff 100%);
  color: #fff;
  padding: 80px 0 60px 0;
  text-align: center;
  position: relative;
  overflow: hidden;
}
.hero-content {
  display: flex;
  align-items: center;
  justify-content: center;
  max-width: 1200px;
  margin: 0 auto;
  flex-wrap: wrap;
}
.hero-text {
  flex: 1 1 400px;
  min-width: 320px;
  text-align: left;
  z-index: 2;
}
.hero-illustration {
  flex: 1 1 400px;
  min-width: 320px;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2;
}
.lottie-box {
  width: 340px;
  height: 340px;
  margin: 0 auto;
  background: transparent;
}
.home-title {
  font-size: 48px;
  font-weight: bold;
  margin-bottom: 20px;
}
.home-desc {
  font-size: 22px;
  margin-bottom: 40px;
}
.hero-btn {
  font-size: 20px;
  font-weight: bold;
  padding: 16px 48px;
  border-radius: 30px;
  margin-top: 10px;
}
.features {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  margin: 60px 0;
}
.feature-card {
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 2px 12px rgba(79,140,255,0.08);
  margin: 16px;
  padding: 32px 24px;
  width: 320px;
  text-align: left;
  color: #333;
  transition: transform 0.3s, box-shadow 0.3s;
}
.feature-card:hover {
  transform: translateY(-8px) scale(1.03);
  box-shadow: 0 8px 32px rgba(79,140,255,0.18);
}
@media (max-width: 900px) {
  .hero-content { flex-direction: column; }
  .hero-illustration, .hero-text { text-align: center; }
}
@media (max-width: 700px) {
  .home-title { font-size: 32px; }
  .lottie-box { width: 220px; height: 220px; }
  .features { flex-direction: column; align-items: center; }
  .feature-card { width: 90% !important; }
}
</style> 