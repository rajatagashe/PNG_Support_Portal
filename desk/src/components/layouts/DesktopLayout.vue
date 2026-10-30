<template>
  <div class="flex flex-col h-screen w-screen bg-[#f1f5f9] text-ink-gray-9 overflow-hidden font-sans antialiased">
    <!-- Minimalist Enterprise Branding Header -->
    <MainBrandingHeader />

    <!-- Workspace: Floating Sidebar + High-Contrast Content Area -->
    <div class="flex flex-1 min-h-0 overflow-hidden">
      <!-- Floating Sidebar Column -->
      <aside
        aria-label="Main Navigation Sidebar"
        class="p-3 pe-0 flex shrink-0 h-full select-none"
      >
        <Sidebar class="h-full rounded-2xl bg-white border border-slate-200/90 shadow-xs overflow-hidden" />
      </aside>

      <!-- Main Content Area with Light Slate Background for Contrast -->
      <main
        role="main"
        class="flex-1 flex flex-col h-full min-w-0 overflow-y-auto p-4 bg-[#f8fafc] rounded-2xl m-3 ms-2.5 border border-slate-200/90 shadow-2xs relative"
      >
        <AppHeader />
        <slot />
      </main>
    </div>

    <Notifications />
  </div>
</template>

<script setup>
import { Notifications } from "@/components";
import AppHeader from "./AppHeader.vue";
import MainBrandingHeader from "./MainBrandingHeader.vue";
import Sidebar from "./Sidebar.vue";
</script>
