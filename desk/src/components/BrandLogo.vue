<template>
  <img
    :src="logoSrc"
    alt="PNG Support Desk"
    class="h-8 w-auto max-w-[120px] shrink-0 object-contain rounded-md"
  />
</template>

<script setup lang="ts">
import pngLogo from "@/assets/png_logo.png";
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
  return config.brandLogo || portalStore.brandLogo || pngLogo;
});
</script>

<style scoped></style>
