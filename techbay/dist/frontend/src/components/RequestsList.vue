<script setup lang="ts">
import { computed, inject, onMounted, ref, watch } from 'vue';
import { dateToDifferenceString } from '@/services/time.service';
import type { Offer, Request } from '@/api/generated';
import { RequestService, SpinnerService, TradingService } from '@/services';
import type { MessageService } from '@/services/message-service';

const $Message = inject<MessageService>('$Message');

type RequestWithOffer = Request & { offer: Offer };

const props = defineProps(['requests', 'showControlsForMyRequests']);
const emit = defineEmits(['reloadRequests']);

const requestsWithOffers = ref<RequestWithOffer[]>([]);

watch([props], async () => {
  await populateRequestsWithOffers();
  selectShownRequests();
});

const shownRequests = ref<RequestWithOffer[]>([]);
const page = ref(0);
const nameOrder = ref();
const creationOrder = ref();
const limit = ref(10);

watch([page, nameOrder, creationOrder, limit], selectShownRequests);

function previousPage() {
  page.value--;
}

function nextPage() {
  page.value++;
}

const nameSymbol = computed(() => {
  if (nameOrder.value == undefined) {
    return '';
  } else if (nameOrder.value == 'asc') {
    return '▲';
  } else {
    return '▼';
  }
});

function changeNameOrder() {
  if (nameOrder.value == undefined) {
    nameOrder.value = 'asc';
  } else if (nameOrder.value == 'asc') {
    nameOrder.value = 'desc';
  } else if (nameOrder.value == 'desc') {
    nameOrder.value = undefined;
  }
}

const createdSymbol = computed(() => {
  if (creationOrder.value == undefined) {
    return '';
  } else if (creationOrder.value == 'asc') {
    return '▲';
  } else {
    return '▼';
  }
});

function changeCreatedOrder() {
  if (creationOrder.value == undefined) {
    creationOrder.value = 'asc';
  } else if (creationOrder.value == 'asc') {
    creationOrder.value = 'desc';
  } else if (creationOrder.value == 'desc') {
    creationOrder.value = undefined;
  }
}

const timeDiffString = dateToDifferenceString;

function selectShownRequests() {
  const sortedRequests = requestsWithOffers.value.sort((a, b) => {
    if (nameOrder.value != undefined) {
      let c = a.offer.name.localeCompare(b.offer.name);
      if (nameOrder.value == 'asc') {
        c = b.offer.name.localeCompare(a.offer.name);
      }
      if (c == 0 && creationOrder.value != undefined) {
        return a.timestamp - b.timestamp;
      }
      return c;
    } else if (creationOrder.value != undefined) {
      let c = a.timestamp - b.timestamp;
      if (creationOrder.value == 'asc') {
        c = b.timestamp - a.timestamp;
      }
      return c;
    }
    return 0;
  });

  const from = page.value * limit.value;

  shownRequests.value = sortedRequests.slice(from, from + limit.value);
}

async function populateRequestsWithOffers() {
  SpinnerService.show();
  try {
    const promises = props.requests.map(async (request: Request) => {
      try {
        const offer = await TradingService.getOffer(request.offerId);
        return { ...request, offer };
      } catch {
        return undefined;
      }
    });
    const requests = await Promise.all(promises);
    requestsWithOffers.value = requests.filter((request) => request != undefined);
    selectShownRequests();
  } finally {
    SpinnerService.hide();
  }
}

async function accept(requestId: number) {
  try {
    await RequestService.acceptRequest(requestId);
    $Message?.success({ text: `Accepted request!`, duration: 4000 });
    emit('reloadRequests');
  } catch {
    $Message?.danger({
      text: `Error while accepting request with id ${requestId}`,
      duration: 4000,
    });
  }
}

async function deny(requestId: number) {
  try {
    await RequestService.denyRequest(requestId);
    $Message?.success({ text: `Denied request!`, duration: 4000 });
    emit('reloadRequests');
  } catch {
    $Message?.danger({ text: `Error while denying request with id ${requestId}`, duration: 4000 });
  }
}

async function takeback(requestId: number) {
  try {
    await RequestService.takebackRequest(requestId);
    $Message?.success({ text: `Request taken back!`, duration: 4000 });
    emit('reloadRequests');
  } catch {
    $Message?.danger({
      text: `Error while taking back request with id ${requestId}`,
      duration: 4000,
    });
  }
}

onMounted(async () => {
  await populateRequestsWithOffers();
  selectShownRequests();
});
</script>

<template>
  <div v-if="requestsWithOffers.length == 0">
    <h1>No open requests!</h1>
  </div>

  <div v-else>
    <div class="control">
      <it-button-group class="control-page">
        <it-button :disabled="page == 0" @click="previousPage()">&lt;-</it-button>
        <it-button :disabled="true">{{ page + 1 }}</it-button>
        <it-button :disabled="shownRequests.length < limit" @click="nextPage()">-&gt;</it-button>
      </it-button-group>
      <label class="control-amount">
        Offers per page
        <it-select :options="[10, 50, 100]" v-model="limit" />
      </label>
    </div>

    <div class="table">
      <div>
        <div class="table-header table-row">
          <span class="table-row-picture"></span>
          <span class="table-row-name" @click="changeNameOrder">Name {{ nameSymbol }}</span>
          <span class="table-row-timestamp" @click="changeCreatedOrder"
            >Requested at {{ createdSymbol }}</span
          >
          <span class="table-row-controls"></span>
        </div>
        <it-divider />
      </div>
      <RouterLink
        class="table-row-wrapper"
        v-for="request in shownRequests"
        :key="request.id"
        :to="`/offer/${request.offerId}`"
      >
        <div class="table-body table-row">
          <span class="table-row-picture"><img :src="request.offer.picture" /></span>
          <span class="table-row-name"
            >{{ request.offer.name }} by
            <RouterLink :to="`/profile/${request.userId}`">#{{ request.userId }}</RouterLink></span
          >
          <span class="table-row-timestamp">{{ timeDiffString(new Date(request.timestamp)) }}</span>
          <span v-if="props.showControlsForMyRequests" class="table-row-controls">
            <it-button
              icon="undo"
              type="danger"
              @click.prevent="takeback(request.id)"
              title="Takeback request"
            />
          </span>
          <span v-else class="table-row-controls">
            <it-button
              icon="check"
              type="success"
              @click.prevent="accept(request.id)"
              title="Accept request"
            />
            <it-button
              icon="close"
              type="danger"
              @click.prevent="deny(request.id)"
              title="Deny request"
            />
          </span>
        </div>
        <it-divider />
      </RouterLink>
    </div>

    <div class="control">
      <it-button-group class="control-page">
        <it-button :disabled="page == 0" @click="previousPage()">&lt;-</it-button>
        <it-button :disabled="true">{{ page + 1 }}</it-button>
        <it-button :disabled="shownRequests.length < limit" @click="nextPage()">-&gt;</it-button>
      </it-button-group>
      <label class="control-amount">
        Offers per page
        <it-select :options="[10, 50, 100]" v-model="limit" />
      </label>
    </div>
  </div>
</template>

<style scoped>
@import '@/assets/base.css';
.control {
  display: grid;
  grid-auto-columns: 1fr 1fr 1fr;
}

.control-page {
  grid-column: 2;
}

.control-amount {
  grid-column: 3;
}

.table {
  display: block;
  margin: 2em 0 2em 0;
}

.table .it-divider {
  padding: 0;
  margin: 0;
}

.table-row {
  display: grid;
  width: 100%;
  grid-auto-columns: 10% auto 15% 10%;
  grid-column-gap: 1em;
  padding: 1em;
  align-items: center;
}

.table-row-wrapper {
  color: var(--color-text);
  text-decoration: none;
}

.table-row-picture {
  grid-column: 1;
}

.table-row-picture img {
  width: 5em;
  height: 5em;
  border: solid thin var(--color-border);
}

.table-row-name {
  grid-column: 2;
}

.table-row-timestamp {
  grid-column: 3;
}

.table-row-controls {
  grid-column: 4;
  display: flex;
  flex-direction: row;
  gap: 0.5em;
}

.table-header {
  font-size: 1.25em;
  font-weight: bold;
  padding: 0.25em 1em;
}

.table-header .table-row-name,
.table-header .table-row-timestamp {
  cursor: pointer;
}

.table-body.table-row {
  cursor: pointer;
}

.table-body.table-row:hover {
  background: rgba(150, 150, 150, 0.1);
}
</style>
