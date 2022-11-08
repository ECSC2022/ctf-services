<script setup lang="ts">
import { inject, onMounted, ref } from 'vue';
import { ProfileService } from '@/services';
import { useRouter } from 'vue-router';
import type { MessageService } from '@/services/message-service';
import { userStore } from '@/stores/user-store';

const $Message = inject<MessageService>('$Message');
const $Router = useRouter();

const user = ref();

onMounted(async () => {
  try {
    user.value = await ProfileService.getProfileOfCurrentUser();
  } catch {
    $Message?.danger({
      text: `Couldn't fetch profile information for the current user`,
      duration: 4000,
    });
    await $Router.push('/');
  }
});

async function updateProfile() {
  try {
    await ProfileService.updateProfile(user.value);
    userStore.user!.displayname = user.value.displayname;

    $Message?.success({
      text: 'Successfully updated profile!',
      duration: 4000,
    });
  } catch {
    $Message?.danger({
      text: 'Error while updating profile',
      duration: 4000,
    });
  }
}
</script>

<template>
  <div class="main" v-if="user">
    <div>
      <it-input v-model="user.displayname" prefix-icon="person" />
      <span class="username">(username: {{ user.username }})</span>
    </div>
    <it-input
      label-top="Telephone Number"
      prefix-icon="phone"
      v-model="user.telephoneNumber"
    />
    <it-input
      label-top="Address"
      prefix-icon="home"
      v-model="user.address"
    />
    <div>
      <span class="it-input-label">Status</span>
      <it-textarea v-model="user.status"><b>Status:</b> {{ user.status }}</it-textarea>
    </div>
    <it-divider />

    <h3>Visibility settings</h3>
    <it-checkbox v-model="user.isTelephoneNumberPublic" label="Telephone number public?" />
    <it-checkbox v-model="user.isAddressPublic" label="Address public?" />
    <it-checkbox v-model="user.isStatusPublic" label="Status public?" />

    <it-button type="primary" @click="updateProfile">Update</it-button>
  </div>
</template>

<style scoped>
.main {
  display: flex;
  flex-direction: column;
  gap: 2em;
}
</style>
