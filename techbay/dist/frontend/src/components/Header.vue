<script setup lang="ts">
import { userStore } from '@/stores/user-store';
import { useRouter } from 'vue-router';

const $Router = useRouter();

async function logout() {
  userStore.user = undefined;
  userStore.isLoggedIn = false;
  userStore.token = undefined;
  localStorage.removeItem('auth');
  await $Router.push('/login');
}

async function navigateToMyProfile() {
  await $Router.push('/my-profile');
}
</script>

<template>
  <header>
    <RouterLink to="/" class="logo"></RouterLink>
    <nav>
      <span class="nav-left-side">
        <RouterLink to="/offers">Offers</RouterLink>
        <RouterLink to="/my-requests" v-if="userStore.isLoggedIn">My Requests</RouterLink>
        <RouterLink to="/requests" v-if="userStore.isLoggedIn">Requests for my Offers</RouterLink>
      </span>
      <it-dropdown v-if="userStore.isLoggedIn">
        <it-button>Hi, {{ userStore.user?.displayname }}!</it-button>
        <template #menu>
          <it-dropdown-menu>
            <it-dropdown-item @click="navigateToMyProfile">Profile</it-dropdown-item>
            <it-dropdown-item @click="logout">Logout</it-dropdown-item>
          </it-dropdown-menu>
        </template>
      </it-dropdown>
      <RouterLink to="/login" v-if="!userStore.isLoggedIn">Login</RouterLink>
    </nav>
  </header>
</template>

<style scoped>
@import '@/assets/base.css';

header {
  display: flex;
  flex-direction: row;
  align-items: center;
  padding: 2em;
}

.logo {
  display: inline-block;
  width: calc(100px + 2em);
  height: calc(50px + 1em);
  background-image: url('../assets/techbay-logo.svg');
  background-size: calc(100px + 2em) calc(50px + 1em);
  margin: -0.5em 2em 0 -1em;
  padding-right: 0.5em;
}

nav a {
  color: var(--color-text);
  padding: 1em;
  text-decoration: unset;
}

nav {
  display: flex;
  flex-direction: row;
  justify-content: space-between;
  width: calc(100% - 100px - 2em - 2em);
  border-bottom: solid thin var(--color-border);
}

.nav-left-side {
  display: flex;
}
</style>
