<template>
  <div class="flex items-center justify-between pb-2 mb-1 pe-2">
    <div id="app-header" class="flex-1 w-full"></div>
    <div class="flex items-start justify-center">
      <CallUI :userEmail="user" />
    </div>
  </div>
</template>

<script setup>
import CallUI from "@/components/telephony/CallUI.vue";
import { useAuthStore } from "@/stores/auth";
import { useTelephonyStore } from "@/stores/telephony";
import { onMounted } from "vue";

const { user } = useAuthStore();

const telephonyStore = useTelephonyStore();

onMounted(() => {
  telephonyStore.fetchCallIntegrationStatus();
});
</script>
