<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router';
import { computed, inject, onMounted, ref } from 'vue';
import type { Offer } from '@/api/generated';
import { RequestService, TradingService } from '@/services';
import { dateToDifferenceString } from '@/services/time.service';
import { userStore } from '@/stores/user-store';
import type { MessageService } from '@/services/message-service';

const $route = useRoute();
const $Router = useRouter();
const $Message = inject<MessageService>('$Message');

const offerId = parseInt($route.params.offerId + '', 10);
const offer = ref<Offer | undefined>(undefined);

const shouldShowRequestButton = computed(() => {
  return (
    userStore.isLoggedIn &&
    offer.value?.owner == undefined &&
    offer.value?.creator.userId != userStore.user?.userId
  );
});

onMounted(async () => {
  try {
    offer.value = await TradingService.getOffer(offerId);
  } catch {
    $Message?.danger({ text: `Error while fetching order with id ${offerId}`, duration: 4000 });
    await $Router.push('/offers');
  }
});

const dateDiffString = dateToDifferenceString;

async function request() {
  if (!offerId || !offer.value) {
    return;
  }
  try {
    await RequestService.requestOffer(offerId);
    offer.value.isRequestedByMe = true;
    $Message?.success({ text: 'Successfully sent request!', duration: 4000 });
  } catch {
    $Message?.danger({ text: 'Error while sending request!', duration: 4000 });
  }
}
</script>

<template>
  <div v-if="offer">
    <div class="offer-header">
      <span class="offer-title">
        {{ offer.name }}
        <span v-if="!offer.owner" class="offer-timestamp">
          {{ dateDiffString(new Date(offer.timestamp)) }} by
          <RouterLink :to="'/profile/' + offer.creator.userId">{{
            offer.creator.displayname
          }}</RouterLink>
        </span>
        <span v-else class="offer-timestamp">
          Owned by
          <RouterLink :to="'/profile/' + offer.owner.userId">{{
            offer.owner.displayname
          }}</RouterLink>
        </span>
      </span>
      <it-button
        v-if="shouldShowRequestButton"
        :disabled="offer.isRequestedByMe"
        type="primary"
        @click="request"
        >Request</it-button
      >
    </div>
    <img class="offer-image" :src="offer.picture" v-if="offer.picture" />
    <it-divider />
    <p>{{ offer.description }}</p>
  </div>
</template>

<style scoped>
.offer-image {
  width: 100%;
  height: auto;
  margin-top: 2em;
  border: solid thin var(--color-border);
  padding: 1em;
}

.offer-timestamp {
  font-size: 0.9rem;
}

.offer-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
}

.offer-title {
  font-size: 2em;
}
</style>
