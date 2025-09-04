import { createRouter, createWebHistory } from 'vue-router';
import HomeView from '../views/HomeView.vue';
import LoginView from '../views/LoginView.vue';
import DashboardView from '../views/DashboardView.vue';
import ProductView from '../views/ProductView.vue';
import PricingView from '../views/PricingView.vue';
import AboutView from '../views/AboutView.vue';
import LegacyHomeView from '../views/LegacyHomeView.vue';

const routes = [
  { path: '/', name: 'Home', component: HomeView },
  { path: '/login', name: 'Login', component: LoginView },
  { path: '/dashboard', name: 'Dashboard', component: DashboardView },
  { path: '/product', name: 'Product', component: ProductView },
  { path: '/pricing', name: 'Pricing', component: PricingView },
  { path: '/about', name: 'About', component: AboutView },
  { path: '/legacy', name: 'LegacyHome', component: LegacyHomeView },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router; 