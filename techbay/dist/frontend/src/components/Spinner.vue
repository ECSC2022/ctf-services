<script setup lang="ts"></script>

<template>
  <div class="spinner-background" style="display: none">
    <it-loading class="spinner" />
  </div>
</template>

<style scoped>
.spinner-background {
  position: fixed;
  z-index: 10000;
  left: 0;
  top: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(0, 0, 0, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
