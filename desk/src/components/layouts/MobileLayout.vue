<template>
  <div class="flex flex-col h-screen w-screen bg-[#f1f5f9] text-ink-gray-9 overflow-hidden font-sans antialiased">
    <!-- Main Branding Header -->
    <MainBrandingHeader />

    <!-- Mobile Body -->
    <div class="flex flex-1 min-h-0 overflow-hidden relative">
      <MobileSidebar />
      <div class="flex h-full flex-col flex-1 overflow-auto p-2 sm:p-3 relative bg-[#f8fafc]">
        <MobileAppHeader />
        <slot />
      </div>
    </div>
  </div>
</template>

<script setup>
import MainBrandingHeader from "./MainBrandingHeader.vue";
import MobileAppHeader from "./MobileAppHeader.vue";
import MobileSidebar from "./MobileSidebar.vue";
</script>
