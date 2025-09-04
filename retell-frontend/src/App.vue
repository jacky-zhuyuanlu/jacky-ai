<script setup>
</script>

<template>
  <div>
    <nav class="navbar">
      <div class="navbar-inner">
        <div class="navbar-logo" @click="$router.push('/')">Retell <span>AI</span></div>
        <ul class="navbar-menu">
          <li :class="{active: $route.path === '/'}" @click="$router.push('/')">首页</li>
          <li :class="{active: $route.path.startsWith('/product')}" @click="$router.push('/product')">产品</li>
          <li :class="{active: $route.path.startsWith('/pricing')}" @click="$router.push('/pricing')">价格</li>
          <li :class="{active: $route.path.startsWith('/about')}" @click="$router.push('/about')">关于我们</li>
        </ul>
        <div class="navbar-actions">
          <el-button type="primary" size="small" @click="$router.push('/login')">登录</el-button>
        </div>
      </div>
    </nav>
    <main class="main-content">
      <router-view />
    </main>
  </div>
</template>

<style>
.navbar {
  position: sticky;
  top: 0;
  z-index: 100;
  background: #fff;
  box-shadow: 0 2px 12px rgba(79,140,255,0.08);
  border-bottom: 1px solid #e6eaf2;
  width: 100%;
  min-height: 64px;
}
.navbar-inner {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 64px;
  padding: 0 32px;
}
.navbar-logo {
  font-size: 28px;
  font-weight: bold;
  color: #357ae8;
  letter-spacing: 1px;
  cursor: pointer;
  user-select: none;
  transition: color 0.2s;
}
.navbar-logo span {
  color: #4f8cff;
}
.navbar-menu {
  display: flex;
  list-style: none;
  margin: 0 32px 0 0;
  padding: 0;
  gap: 32px;
}
.navbar-menu li {
  font-size: 17px;
  color: #333;
  cursor: pointer;
  position: relative;
  padding: 4px 0;
  transition: color 0.2s;
}
.navbar-menu li.active,
.navbar-menu li:hover {
  color: #357ae8;
}
.navbar-menu li.active::after,
.navbar-menu li:hover::after {
  content: '';
  display: block;
  position: absolute;
  left: 0; right: 0; bottom: -6px;
  height: 3px;
  border-radius: 2px;
  background: linear-gradient(90deg, #4f8cff 0%, #6fd6ff 100%);
  transition: all 0.2s;
}
.navbar-actions {
  display: flex;
  align-items: center;
}
.main-content {
  min-height: calc(100vh - 64px);
  padding-top: 24px;
}
@media (max-width: 900px) {
  .navbar-inner { flex-direction: column; height: auto; padding: 0 8px; }
  .navbar-menu { gap: 16px; margin: 0; }
  .main-content { padding-top: 16px; }
}
@media (max-width: 600px) {
  .navbar-inner { flex-direction: column; align-items: flex-start; padding: 0 4px; }
  .navbar-logo { font-size: 22px; }
  .navbar-menu { flex-direction: column; gap: 8px; }
}
</style>
