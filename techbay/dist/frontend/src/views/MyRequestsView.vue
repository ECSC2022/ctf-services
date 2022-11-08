<script setup lang="ts">
import { RequestService } from '@/services';
import { onMounted, ref } from 'vue';
import type { Request } from '@/api/generated';
import RequestsList from '@/components/RequestsList.vue';

const requests = ref<Request[]>([]);
onMounted(async () => {
  requests.value = await RequestService.getRequestsByMe();
});
</script>

<template>
  <RequestsList :requests="requests" :show-controls-for-my-requests="true" />
</template>
