<script setup lang="ts">
import { computed, inject, ref } from 'vue';
import { useRouter } from 'vue-router';
import { AuthenticationService } from '@/services';
import type { MessageService } from '@/services/message-service';

const $Message = inject<MessageService>('$Message');
const $Router = useRouter();

const username = ref();
const password = ref();

const passportFile = ref<File | undefined>();

const isRegistering = ref(false);

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

const passportErrorMessage = computed(() => {
  if (errors.value.has('passportEmpty')) {
    return "Passport can't be empty";
  }

  if (errors.value.has('passportSize')) {
    return 'Passport has to be smaller than 50K';
  }

  return '';
});

async function register() {
  if (isRegistering.value) {
    return;
  }

  isRegistering.value = true;

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

  if (!passportFile.value) {
    errors.value.add('passportEmpty');
  } else if (passportFile.value && passportFile.value.size > 50 * 1024) {
    errors.value.add('passportSize');
  }

  if (errors.value.size != 0) {
    isRegistering.value = false;
    return;
  }

  try {
    const data = await passportFile.value!.arrayBuffer();
    const b64data = btoa(String.fromCharCode(...new Uint8Array(data)));

    await AuthenticationService.register(username.value, password.value, b64data);
    $Message?.success({ text: 'Registered!', duration: 4000 });
    await $Router.push('/login');
  } catch {
    $Message?.danger({ text: "Couldn't register with the given credentials", duration: 4000 });
  } finally {
    isRegistering.value = false;
  }
}

function setPassport(event: Event) {
  // eslint-disable-next-line @typescript-eslint/ban-ts-comment
  //@ts-ignore
  const files: FileList = event.target!.files;
  passportFile.value = files[0];
}
</script>

<template>
  <div class="main">
    <form @submit.prevent="register">
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
      <it-input
        type="file"
        label-top="Passport"
        @change="setPassport"
        accept=".png"
        :message="passportErrorMessage"
        :status="passportErrorMessage.length > 0 ? 'danger' : ''"
      />
      <it-button :block="true" type="primary" @click="register">Register</it-button>
    </form>
    <span>
      <RouterLink to="/login">Already an account? Login here</RouterLink>
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

.passport-input {
  margin-bottom: 0;
  padding-bottom: 0;
}

.passport-error-message {
  color: #f93155;
  font-size: 12px;
  margin-top: 0;
  padding-top: 0;
}
</style>

<style>
div.passport-input-error textarea {
  border: 1px solid #f93155;
}
</style>
