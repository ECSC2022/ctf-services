<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { dateToDifferenceString } from '@/services/time.service';
import { userStore } from '@/stores/user-store';

const props = defineProps(['offers']);
const emit = defineEmits(['loadOffers']);

const page = ref(0);
const nameOrder = ref();
const creationOrder = ref();
const limit = ref(10);
const onlyMine = ref(false);

function loadOffers() {
  emit('loadOffers', {
    page: page.value,
    nameOrder: nameOrder.value,
    creationOrder: creationOrder.value,
    limit: limit.value,
    onlyMine: onlyMine.value,
  });
}

watch([page], loadOffers);
watch([limit, onlyMine, nameOrder, creationOrder], () => {
  if (page.value != 0) {
    page.value = 0;
  } else {
    loadOffers();
  }
});

onMounted(loadOffers);

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
</script>

<template>
  <div class="control">
    <div class="control-mine">
      <it-checkbox v-if="userStore.isLoggedIn" label="Only show my offers?" v-model="onlyMine" />
    </div>
    <it-button-group class="control-page">
      <it-button :disabled="page == 0" @click="previousPage()">&lt;-</it-button>
      <it-button :disabled="true">{{ page + 1 }}</it-button>
      <it-button :disabled="offers.length < limit" @click="nextPage()">-&gt;</it-button>
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
          >Created {{ createdSymbol }}</span
        >
      </div>
      <it-divider />
    </div>
    <RouterLink
      class="table-row-wrapper"
      v-for="offer in props.offers"
      :key="offer.id"
      :to="`/offer/${offer.id}`"
    >
      <div class="table-body table-row" :class="offer.owner ? 'owned' : ''">
        <span class="table-row-picture"><img :src="offer.picture" /></span>
        <span class="table-row-name">
          {{ offer.name }}
        </span>
        <span class="table-row-timestamp">{{ timeDiffString(new Date(offer.timestamp)) }}</span>
      </div>
      <it-divider />
    </RouterLink>
    <div v-if="offers.length == 0" class="no-offers-to-show">No offers to show!</div>
  </div>

  <div class="control">
    <span class="control-mine"></span>
    <it-button-group class="control-page">
      <it-button :disabled="page == 0" @click="previousPage()">&lt;-</it-button>
      <it-button :disabled="true">{{ page + 1 }}</it-button>
      <it-button :disabled="offers.length < limit" @click="nextPage()">-&gt;</it-button>
    </it-button-group>
    <span class="control-amount"></span>
  </div>
</template>

<style scoped>
.owned {
  background-color: #eee;
  color: #666;
  text-decoration: line-through;
}

.control {
  display: grid;
  grid-auto-columns: 1fr 1fr 1fr;
  align-items: center;
}

.control-mine {
  grid-column: 1;
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
  grid-auto-columns: 5em auto 15%;
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

.no-offers-to-show {
  text-align: center;
  font-style: italic;
  font-size: 1.5em;
  margin: 2em 0;
}
</style>
