<template>
  <img
    v-if="logoSrc"
    :src="logoSrc"
    alt="Brand Logo"
    class="h-8 w-8 shrink-0 object-contain rounded-md"
  />
  <HDLogo v-else class="h-8 w-8 shrink-0 rounded-4" />
</template>

<script setup lang="ts">
import HDLogo from "@/assets/logos/HDLogo.vue";
import { useConfigStore } from "@/stores/config";
import { usePortalStore } from "@/stores/portal";
import { isCustomerPortal } from "@/utils";
import { computed } from "vue";

const config = useConfigStore();
const portalStore = usePortalStore();

const logoSrc = computed(() => {
  if (isCustomerPortal.value && portalStore.brandLogo) {
    return portalStore.brandLogo;
  }
  return config.brandLogo || portalStore.brandLogo;
});
</script>

<style scoped></style>
