<script setup lang="ts">
import { TradingService } from '@/services';
import { inject, ref } from 'vue';
import type { NewOffer, Offer } from '@/api/generated';
import OfferList from '@/components/OfferList.vue';
import type { MessageService } from '@/services/message-service';
import NewOfferView from '@/views/NewOfferView.vue';
import { userStore } from '@/stores/user-store';

const $Message = inject<MessageService>('$Message');

const showNewOfferModal = ref(false);
const offers = ref<Offer[]>([]);

async function loadOffers(options: {
  page: number;
  nameOrder?: 'asc' | 'desc';
  creationOrder?: 'asc' | 'desc';
  limit: number;
  onlyMine: boolean;
}) {
  try {
    const offersFunction = options.onlyMine ? TradingService.getMyOffers : TradingService.getOffers;
    offers.value = await offersFunction(
      options.page,
      options.nameOrder,
      options.creationOrder,
      options.limit,
    );
  } catch {
    $Message?.danger({
      text: 'There was a problem when fetching the list of offers!',
      duration: 4000,
    });
  }
}
loadOffers({
  page: 0,
  limit: 10,
  onlyMine: false,
});

async function addNewOffer(newOffer: NewOffer) {
  if (newOffer == undefined) {
    showNewOfferModal.value = false;
    return;
  }

  try {
    await TradingService.addOffer(newOffer.name, newOffer.description, newOffer.picture ?? '');
    $Message?.success({ text: 'Added new offer!', duration: 4000 });
    showNewOfferModal.value = false;
  } catch {
    $Message?.danger({ text: 'Error while adding new offer!', duration: 4000 });
  }
}
</script>

<template>
  <div v-if="userStore.isLoggedIn" class="add-button-wrapper">
    <it-button
      icon="add"
      @click="showNewOfferModal = true"
      class="add-button"
      type="primary"
      title="Add new offer"
    ></it-button>
  </div>

  <div>
    <OfferList :offers="offers" @loadOffers="loadOffers" />
  </div>
  <it-modal v-model="showNewOfferModal" :close-on-esc="false" :closable-mask="false">
    <template #body>
      <NewOfferView @close="addNewOffer" style="margin-bottom: 1em" />
    </template>
  </it-modal>
</template>

<style>
.add-button-wrapper {
  position: fixed;
  display: inline-block;
  right: 6em;
  bottom: 6em;
}

.add-button .it-icon {
  font-size: 2em !important;
}

.add-button {
  padding: 1em !important;
  border-radius: 5em !important;
  height: calc(30px + 2em);
}
</style>
