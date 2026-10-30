<template>
  <Dropdown :options="options">
    <template #default="{ open }">
      <button
        class="flex h-12 items-center rounded-5 py-2 duration-300 ease-in-out"
        :class="
          collapsed
            ? 'w-auto px-0'
            : open
            ? 'w-full px-2 bg-surface-base shadow-sm'
            : 'w-full px-2 hover:bg-surface-gray-3'
        "
      >
        <BrandLogo />
        <div
          class="flex flex-1 flex-col text-start duration-300 ease-in-out overflow-hidden rtl:items-start pe-2"
          :class="
            collapsed
              ? 'ms-0 w-0 overflow-hidden opacity-0'
              : 'ms-2 w-auto opacity-100'
          "
        >
          <div class="text-base-medium leading-none text-ink-gray-9 truncate">
            {{ displayName }}
          </div>
          <div class="mt-1 text-sm text-ink-gray-7 flex items-center gap-1.5">
            <span class="truncate">{{ authStore.userName }}</span>
            <span
              v-if="!isCustomerPortal"
              class="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider"
              :class="authStore.isAdmin ? 'bg-orange-100 text-[#d9531e] border border-orange-300' : 'bg-emerald-100 text-emerald-800 border border-emerald-300'"
            >
              {{ authStore.isAdmin ? __('Admin') : __('User') }}
            </span>
          </div>
        </div>
        <div
          class="duration-300 ease-in-out"
          :class="
            collapsed
              ? 'ms-0 w-0 overflow-hidden opacity-0'
              : 'ms-2 relative start-[-2.5px] w-auto opacity-100'
          "
        >
          <LucideChevronDown
            class="h-4 w-4 text-ink-gray-5"
            aria-hidden="true"
          />
        </div>
      </button>
    </template>
  </Dropdown>
</template>

<script setup lang="ts">
import LucideChevronDown from "~icons/lucide/chevron-down";
import BrandLogo from "@/components/BrandLogo.vue";
import { useAuthStore } from "@/stores/auth";
import { useConfigStore } from "@/stores/config";
import { usePortalStore } from "@/stores/portal";
import { useSidebarStore } from "@/stores/sidebar";
import { isCustomerPortal } from "@/utils";
import { __ } from "@/translation";
import { Dropdown } from "frappe-ui";
import { computed } from "vue";

const config = useConfigStore();
const portalStore = usePortalStore();

const props = defineProps({
  options: {
    type: Array,
    required: true,
  },
  isCollapsed: {
    type: Boolean,
    default: null,
  },
});

const authStore = useAuthStore();
const sidebarStore = useSidebarStore();

const collapsed = computed(() => props.isCollapsed ?? !sidebarStore.isExpanded);

const displayName = computed(() => {
  if (isCustomerPortal.value && portalStore.brandName) {
    return portalStore.brandName;
  }
  return config.brandName || "PNG Support Desk";
});
</script>
