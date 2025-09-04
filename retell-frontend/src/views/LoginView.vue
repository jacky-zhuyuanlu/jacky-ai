<template>
  <div class="login-box">
    <h2 class="login-title">登录体验</h2>
    <el-form :model="form" @submit.prevent="onLogin" class="login-form">
      <el-form-item>
        <el-input v-model="form.username" placeholder="请输入用户名" />
      </el-form-item>
      <el-form-item>
        <el-input v-model="form.password" type="password" placeholder="请输入密码" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" native-type="submit" :loading="loading" style="width:100%">登录</el-button>
      </el-form-item>
      <el-alert v-if="error" :title="error" type="error" show-icon style="margin-bottom:0" />
    </el-form>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { login } from '../api';
import { useRouter } from 'vue-router';

const router = useRouter();
const form = ref({ username: '', password: '' });
const loading = ref(false);
const error = ref('');

const onLogin = async () => {
  error.value = '';
  loading.value = true;
  try {
    const res = await login(form.value.username, form.value.password);
    // 登录成功，跳转到 legacy 页面
    router.push('/legacy');
  } catch (e) {
    error.value = e.response?.data?.detail || '登录失败';
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
.login-box {
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 2px 12px rgba(79,140,255,0.08);
  width: 360px;
  margin: 100px auto;
  padding: 40px 32px;
  text-align: center;
}
.login-title {
  font-size: 28px;
  font-weight: bold;
  color: #4f8cff;
  margin-bottom: 24px;
}
.login-form {
  margin-top: 24px;
}
</style> 