<script setup lang="ts">
import { computed, ref } from 'vue';

const emit = defineEmits(['close']);

const name = ref<string>();
const description = ref<string>();
const pictureFile = ref<File | undefined>();

const errors = ref<Set<string>>(new Set());

const nameErrors = computed(() => {
  if (errors.value.has('nameEmpty')) {
    return 'Name has to be set!';
  } else if (errors.value.has('nameLength')) {
    return 'Name has to be at least 5 characters long!';
  }
  return '';
});

const descriptionErrors = computed(() => {
  if (errors.value.has('descriptionEmpty')) {
    return 'Description has to be set!';
  } else if (errors.value.has('descriptionLength')) {
    return 'Description has to be at least 10 characters long!';
  }
  return '';
});

const pictureErrors = computed(() => {
  if (errors.value.has('pictureSize')) {
    return 'Picture has to be smaller than 50K';
  }
  return '';
});

async function submit() {
  errors.value.clear();

  if (!name.value) {
    errors.value.add('nameEmpty');
  } else if (name.value.length < 5) {
    errors.value.add('nameLength');
  }

  if (!description.value) {
    errors.value.add('descriptionEmpty');
  } else if (description.value.length < 10) {
    errors.value.add('descriptionLength');
  }

  if (pictureFile.value && pictureFile.value.size > 50 * 1024) {
    errors.value.add('pictureSize');
  }

  if (errors.value.size > 0) {
    return;
  }

  if (!pictureFile.value) {
    // eslint-disable-next-line @typescript-eslint/no-non-null-assertion
    emit('close', {
      name: name.value,
      description: description.value,
      picture: '',
    });
    clear();
  } else {
    const data = await pictureFile.value.arrayBuffer();
    const b64data = btoa(String.fromCharCode(...new Uint8Array(data)));
    // eslint-disable-next-line @typescript-eslint/no-non-null-assertion

    emit('close', {
      name: name.value,
      description: description.value,
      picture: b64data,
    });
    clear();
  }
}

function setPicture(event: Event) {
  // eslint-disable-next-line @typescript-eslint/ban-ts-comment
  //@ts-ignore
  const files: FileList = event.target!.files;
  pictureFile.value = files[0];
}

function close() {
  emit('close', undefined);
  clear();
}

function clear() {
  name.value = '';
  description.value = '';
  pictureFile.value = undefined;
}
</script>

<template>
  <h2>New offer <it-icon name="close" class="modal-close-icon" @click="close" /></h2>
  <div class="form">
    <it-input
      type="text"
      label-top="Name"
      v-model="name"
      :message="nameErrors"
      :status="nameErrors.length > 0 ? 'danger' : ''"
    />
    <div>
      <it-textarea
        label-top="Description"
        v-model="description"
        :class="descriptionErrors.length > 0 ? 'danger' : ''"
      />
      <span class="it-input-message it-input-message--danger">{{ descriptionErrors }}</span>
    </div>
    <it-input
      type="file"
      label-top="Picture"
      @change="setPicture"
      accept=".png, .jpg, .jpeg, .gif"
      :message="pictureErrors"
      :status="pictureErrors.length > 0 ? 'danger' : ''"
    />
    <it-button type="primary" @click="submit()">Submit</it-button>
  </div>
</template>

<style scoped>
.form {
  display: flex;
  flex-direction: column;
  gap: 2em;
}

h2 {
  margin-bottom: 1em;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.modal-close-icon {
  cursor: pointer;
  font-size: 2rem !important;
  padding: 0.5rem;
  margin-left: auto;
}
</style>

<style>
div.danger textarea.it-textarea {
  border: solid 1px #f93155;
}
</style>
