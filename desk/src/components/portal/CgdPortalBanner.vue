<template>
  <div
    class="mx-4 mt-3 mb-2 rounded-lg border border-outline-gray-2 bg-surface-white p-4 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-3"
  >
    <div class="flex items-center gap-3">
      <div
        class="flex size-11 shrink-0 items-center justify-center rounded-lg bg-white border border-outline-gray-2 p-1 overflow-hidden shadow-2xs"
      >
        <img
          :src="portalStore.brandLogo || pngLogo"
          alt="PNG Support Desk"
          class="size-full object-contain"
        />
      </div>
      <div>
        <div class="flex items-center gap-2">
          <h2 class="text-base-semibold text-ink-gray-9 leading-snug">
            {{ portalStore.bannerTitle }}
          </h2>
          <span
            v-if="portalStore.isVip"
            class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-800 border border-amber-300 shadow-2xs"
          >
            <LucideCrown class="size-3.5 text-amber-600" />
            {{ __("VIP Priority CGD") }}
          </span>
          <span
            v-else-if="portalStore.customerName"
            class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-primary border border-blue-200"
          >
            {{ portalStore.customerName }}
          </span>
        </div>
        <p class="text-xs text-ink-gray-6 mt-0.5">
          {{ portalStore.bannerSubtitle }}
        </p>
      </div>
    </div>
    <div class="flex items-center gap-2 self-end md:self-center shrink-0">
      <RouterLink
        v-if="showNewTicket"
        :to="{ name: 'TicketNew' }"
        class="inline-flex"
      >
        <Button
          variant="solid"
          size="sm"
          :label="__('Raise New Ticket')"
        >
          <template #prefix>
            <LucidePlus class="size-3.5" />
          </template>
        </Button>
      </RouterLink>
      <RouterLink
        v-if="showKnowledgeBase"
        :to="{ name: 'CustomerKnowledgeBase' }"
        class="inline-flex"
      >
        <Button
          variant="outline"
          size="sm"
          :label="__('Knowledge Base')"
        >
          <template #prefix>
            <LucideBookOpen class="size-3.5" />
          </template>
        </Button>
      </RouterLink>
    </div>
  </div>
</template>

<script setup lang="ts">
import pngLogo from "@/assets/png_logo.png";
import { usePortalStore } from "@/stores/portal";
import { __ } from "@/translation";
import { Button } from "frappe-ui";
import LucideBookOpen from "~icons/lucide/book-open";
import LucideCrown from "~icons/lucide/crown";
import LucidePlus from "~icons/lucide/plus";

withDefaults(
  defineProps<{
    showNewTicket?: boolean;
    showKnowledgeBase?: boolean;
  }>(),
  {
    showNewTicket: false,
    showKnowledgeBase: false,
  }
);

const portalStore = usePortalStore();
</script>
