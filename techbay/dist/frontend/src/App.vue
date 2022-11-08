<script lang="ts">
import { RouterView } from 'vue-router';
import Header from '@/components/Header.vue';
import { provide } from 'vue';
import { AuthenticationService } from '@/services';
import { userStore } from '@/stores/user-store';
import Spinner from '@/components/Spinner.vue';

export default {
  // eslint-disable-next-line vue/no-reserved-component-names
  components: { Spinner, RouterView, Header },
  async mounted() {
    // eslint-disable-next-line @typescript-eslint/ban-ts-comment
    //@ts-ignore
    provide('$Message', this.$Message);
    try {
      const token = localStorage.getItem('auth');
      if (token == null) {
        return;
      }

      userStore.token = token;
      const currentUser = await AuthenticationService.getCurrentUser();

      userStore.isLoggedIn = true;
      userStore.user = { ...currentUser };
    } catch {
      userStore.token = undefined;
      localStorage.removeItem('auth');
    }
  },
};
</script>

<template>
  <Header />

  <Spinner />

  <main>
    <RouterView />
  </main>
</template>

<style>
@import '@/assets/base.css';
main {
  padding: 2em;
  width: calc(70% - 4em);
  margin: 0 auto;
}

@media (max-width: 1024px) {
  main {
    width: calc(100% - 4em);
  }
}
</style>
