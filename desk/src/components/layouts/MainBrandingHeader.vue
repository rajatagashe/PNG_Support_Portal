<template>
  <header
    aria-label="Portal Header and Branding"
    class="bg-white/95 backdrop-blur-md border-b border-slate-200/90 px-4 sm:px-6 h-14 flex items-center justify-between shadow-xs z-20 shrink-0"
  >
    <!-- Left: PNG Support Desk & Amantya Technologies Branding -->
    <div class="flex items-center gap-3">
      <!-- Portal Brand Logo Emblem using exact uploaded logo -->
      <div class="h-10 w-10 flex items-center justify-center shrink-0">
        <img
          :src="logoSrc"
          alt="PNG Support Desk"
          class="h-9 w-auto max-w-[120px] object-contain drop-shadow-xs"
        />
      </div>

      <div class="flex flex-col text-start">
        <div class="flex items-center gap-2">
          <span class="text-sm sm:text-base font-extrabold text-slate-900 tracking-tight leading-none">
            {{ __("PNG Support Desk") }}
          </span>
          <span class="hidden sm:inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold bg-orange-50 text-[#d9531e] border border-orange-200/80">
            {{ __("Support Portal") }}
          </span>
        </div>
        <span class="text-[11px] text-slate-500 font-medium leading-none mt-1">
          Amantya Technologies Private Limited
        </span>
      </div>
    </div>

    <!-- Right: User Profile Capsule & Actions -->
    <div class="flex items-center gap-2.5">
      <!-- User Profile Capsule -->
      <div class="flex items-center gap-2 bg-slate-50 hover:bg-slate-100/90 border border-slate-200/90 rounded-full py-1 ps-2 pe-3 transition-colors shadow-2xs">
        <span class="size-2 rounded-full bg-emerald-500 shrink-0" title="Online" />
        <!-- Burnt Orange Avatar Circle with Initials -->
        <div class="size-7 rounded-full bg-[#d9531e] text-white font-bold flex items-center justify-center text-xs shrink-0 shadow-2xs">
          {{ userInitials }}
        </div>
        <div class="flex flex-col text-start hidden sm:flex">
          <span class="text-xs font-bold text-slate-900 leading-tight truncate max-w-[130px]">
            {{ displayName }}
          </span>
          <span class="text-[10px] text-slate-500 font-medium leading-none mt-0.5">
            {{ roleLabel }}
          </span>
        </div>
        <!-- Sign Out Action Button -->
        <button
          type="button"
          class="ms-1 text-slate-400 hover:text-rose-600 transition-colors p-1 rounded-full hover:bg-slate-200/60"
          :title="__('Sign Out')"
          :aria-label="__('Sign Out')"
          @click="authStore.logout()"
        >
          <LucideLogOut class="size-3.5" />
        </button>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import pngLogo from "@/assets/png_logo.png";
import { useAuthStore } from "@/stores/auth";
import { useConfigStore } from "@/stores/config";
import { usePortalStore } from "@/stores/portal";
import { __ } from "@/translation";
import { computed } from "vue";
import LucideLogOut from "~icons/lucide/log-out";

const authStore = useAuthStore();
const configStore = useConfigStore();
const portalStore = usePortalStore();

const logoSrc = computed(() => {
  return configStore.brandLogo || portalStore.brandLogo || pngLogo;
});

const displayName = computed(() => {
  return authStore.userName || authStore.userId || "Administrator";
});

const userInitials = computed(() => {
  const name = displayName.value.trim();
  const parts = name.split(/\s+/);
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }
  return name.slice(0, 2).toUpperCase();
});

const roleLabel = computed(() => {
  if (authStore.isAdmin) return __("Administrator");
  if (authStore.isEmailUserOnly) return __("Support Email User");
  if (authStore.isAgent) return __("Support Executive");
  return __("User");
});
</script>
