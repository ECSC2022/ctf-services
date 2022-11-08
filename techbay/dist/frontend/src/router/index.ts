import { createRouter, createWebHashHistory, createWebHistory } from 'vue-router';
import HomeView from '../views/HomeView.vue';
import OffersView from '../views/OffersView.vue';
import MyRequestsView from '../views/MyRequestsView.vue';
import LoginView from '../views/LoginView.vue';
import RegisterView from '../views/RegisterView.vue';
import AdminView from '../views/AdminView.vue';
import OfferView from '../views/OfferView.vue';
import MyProfileView from '../views/MyProfileView.vue';
import ProfileView from '../views/ProfileView.vue';
import RequestsView from '../views/RequestsView.vue';
import { userStore } from '@/stores/user-store';

const router = createRouter({
  history: createWebHashHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/home',
      name: 'home',
      component: HomeView,
    },
    {
      path: '/offers',
      name: 'offers',
      component: OffersView,
    },
    {
      path: '/offer/:offerId',
      name: 'offer',
      component: OfferView,
    },
    {
      path: '/my-profile',
      name: 'my-profile',
      component: MyProfileView,
      beforeEnter: requireAuthenticated,
    },
    {
      path: '/profile/:userId',
      name: 'profile',
      component: ProfileView,
      props: true,
      beforeEnter: requireAuthenticated,
    },
    {
      path: '/my-requests',
      name: 'my-requests',
      component: MyRequestsView,
      beforeEnter: requireAuthenticated,
    },
    {
      path: '/requests',
      name: 'requests',
      component: RequestsView,
      beforeEnter: requireAuthenticated,
    },
    {
      path: '/login',
      name: 'login',
      component: LoginView,
      beforeEnter: requireUnauthenticated,
    },
    {
      path: '/register',
      name: 'register',
      component: RegisterView,
    },
    {
      path: '/admin',
      name: 'admin',
      component: AdminView,
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/home',
    },
  ],
});

function requireAuthenticated(): any {
  if (!userStore.isLoggedIn) {
    return '/';
  }
}

function requireUnauthenticated(): any {
  if (userStore.isLoggedIn) {
    return '/';
  }
}

export default router;
