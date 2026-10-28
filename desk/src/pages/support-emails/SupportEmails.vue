<template>
  <div class="flex flex-col h-full w-full overflow-y-auto">
    <LayoutHeader>
      <template #left-header>
        <div class="flex items-center gap-2">
          <LucideMail class="size-5 text-ink-gray-7" />
          <div class="text-lg-medium text-ink-gray-9">
            {{ __("Support Email Management & Analytics") }}
          </div>
        </div>
      </template>
    </LayoutHeader>
    <div class="px-4 py-4 w-full space-y-4">
      <SupportMailboxStatus @activated="tabKey++" />
      <SupportEmailAnalyticsTab :key="tabKey" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { LayoutHeader } from "@/components";
import SupportEmailAnalyticsTab from "@/pages/dashboard/SupportEmailAnalyticsTab.vue";
import SupportMailboxStatus from "@/pages/support-emails/SupportMailboxStatus.vue";
import { __ } from "@/translation";
import { usePageMeta } from "frappe-ui";
import { ref } from "vue";
import LucideMail from "~icons/lucide/mail";

// remounting the tab reloads its lists once a newly connected mailbox has synced
const tabKey = ref(0);

usePageMeta(() => ({
  title: __("Support Email Management"),
}));
</script>
