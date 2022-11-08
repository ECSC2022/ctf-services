<script setup lang="ts">
import { inject, onMounted, ref } from 'vue';
import { ProfileService } from '@/services';
import { useRouter } from 'vue-router';
import type { MessageService } from '@/services/message-service';

const $Message = inject<MessageService>('$Message');
const $Router = useRouter();
const props = defineProps(['userId']);

const user = ref();

onMounted(async () => {
  if (props.userId == undefined) {
    await $Router.push('/');
  }

  try {
    user.value = await ProfileService.getProfile(props.userId);
  } catch {
    $Message?.danger({
      text: `Couldn't fetch profile information for user with id ${props.userId}`,
      duration: 4000,
    });
    await $Router.push('/');
  }
});
</script>

<template>
  <div class="main" v-if="user">
    <h1>
      {{ user.displayname }}
      <br />
      <span class="username">(username: {{ user.username }})</span>
    </h1>
    <it-input
      v-if="user.telephoneNumber"
      label-top="Telephone Number"
      prefix-icon="phone"
      v-model="user.telephoneNumber"
    />
    <it-input v-if="user.address" label-top="Address" prefix-icon="home" v-model="user.address" />
    <div v-if="user.status">
      <span class="it-input-label">Status</span>
      <it-textarea v-model="user.status"><b>Status:</b> {{ user.status }}</it-textarea>
    </div>
  </div>
</template>

<style scoped>
.main {
  display: flex;
  flex-direction: column;
  gap: 2em;
}

.username {
  font-size: 1rem;
}
</style>
