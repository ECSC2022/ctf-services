<script setup lang="ts">
import { computed, inject, ref } from 'vue';
import { userStore } from '@/stores/user-store';
import { useRouter } from 'vue-router';
import { AuthenticationService } from '@/services';
import type { MessageService } from '@/services/message-service';

const $Message = inject<MessageService>('$Message');
const $Router = useRouter();

const username = ref();
const password = ref();
const isLoggingIn = ref(false);

const errors = ref(new Set());

const usernameErrorMessage = computed(() => {
  const messages = [];
  if (errors.value.has('usernameEmpty')) {
    messages.push("Username can't be empty");
  }
  if (errors.value.has('usernameLength')) {
    messages.push('Username has to be at least 5 characters long');
  }

  return messages.join('\n');
});

const passwordErrorMessage = computed(() => {
  const messages = [];
  if (errors.value.has('passwordEmpty')) {
    messages.push("Password can't be empty");
  }
  if (errors.value.has('passwordLength')) {
    messages.push('Password has to be at least 5 characters long');
  }

  return messages.join('\n');
});

async function login() {
  if (isLoggingIn.value) {
    return;
  }

  isLoggingIn.value = true;

  errors.value.clear();
  if (!username.value) {
    errors.value.add('usernameEmpty');
  } else if (username.value.length < 5) {
    errors.value.add('usernameLength');
  }

  if (!password.value) {
    errors.value.add('passwordEmpty');
  } else if (password.value.length < 5) {
    errors.value.add('passwordLength');
  }

  if (errors.value.size != 0) {
    isLoggingIn.value = false;
    return;
  }

  try {
    const user = await AuthenticationService.login(username.value, password.value);
    userStore.isLoggedIn = true;
    userStore.token = user.token;
    userStore.user = { ...user };
    $Message?.success({ text: 'Logged in!', duration: 4000 });
    localStorage.setItem('auth', user.token);
    const currentUser = await AuthenticationService.getCurrentUser();
    await $Router.push('/');
  } catch {
    $Message?.danger({ text: "Couldn't login with the given credentials", duration: 4000 });
  } finally {
    isLoggingIn.value = false;
  }
}
</script>

<template>
  <div class="main">
    <form @submit.prevent="login">
      <it-input
        type="text"
        label-top="Username"
        placeholder="username"
        v-model="username"
        :status="usernameErrorMessage.length > 0 ? 'danger' : ''"
        :message="usernameErrorMessage"
      />
      <it-input
        type="password"
        label-top="Password"
        placeholder="******"
        v-model="password"
        :status="passwordErrorMessage.length > 0 ? 'danger' : ''"
        :message="passwordErrorMessage"
      />
      <it-button :block="true" type="primary" @click="login">Login</it-button>
    </form>
    <span>
      <RouterLink to="/register">No account yet? Register here</RouterLink>
    </span>
  </div>
</template>

<style scoped>
.main {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  padding-top: 2em;
}

form {
  display: flex;
  flex-direction: column;
  width: 100%;
  justify-content: space-between;
}

form * {
  margin: 1em 0;
}
</style>
