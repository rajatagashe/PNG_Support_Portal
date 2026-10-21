<template>
  <div class="space-y-3">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-2">
        <LucideHistory class="size-4 text-ink-gray-6" />
        <span class="text-xs font-semibold text-ink-gray-7 uppercase tracking-wider">
          {{ __("Assignment & Reassignment Audit Trail") }}
        </span>
      </div>
      <div class="flex items-center gap-1.5">
        <Button
          variant="outline"
          size="sm"
          class="!h-6 !text-xs !px-2"
          :label="__('Reassign / Escalate')"
          @click="showReassignModal = true"
        >
          <template #prefix>
            <LucideArrowUpRight class="size-3 text-ink-gray-6" />
          </template>
        </Button>
        <Button
          variant="ghost"
          size="sm"
          class="!h-6 !w-6 !p-0"
          @click="historyResource.reload()"
        >
          <LucideRefreshCw class="size-3 text-ink-gray-5 hover:text-ink-gray-8" />
        </Button>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="historyResource.loading" class="flex justify-center py-4">
      <LoadingIndicator class="size-4 text-ink-gray-6" />
    </div>

    <!-- Empty -->
    <div
      v-else-if="!historyResource.data?.length"
      class="text-xs text-ink-gray-5 py-3 text-center bg-surface-gray-1 rounded border border-outline-gray-1"
    >
      {{ __("No assignment history recorded yet for this ticket.") }}
    </div>

    <!-- Timeline entries -->
    <div v-else class="space-y-2.5">
      <div
        v-for="log in historyResource.data"
        :key="log.name"
        class="border border-outline-gray-2 rounded-lg p-3 text-xs space-y-2 transition-all shadow-2xs"
        :class="log.action_type === 'Escalation' ? 'bg-purple-50/30 border-l-3 border-l-purple-500' : 'bg-surface-white'"
      >
        <!-- Top row: Actor, Action Type Badge, and Timestamp -->
        <div class="flex items-center justify-between text-ink-gray-6">
          <div class="flex items-center gap-1.5 min-w-0">
            <span class="font-semibold text-ink-gray-9 truncate">
              {{ log.assigned_by_name || log.assigned_by }}
            </span>
            <span
              v-if="log.action_type"
              class="px-2 py-0.5 rounded-full text-[10px] uppercase tracking-wider font-bold"
              :class="
                log.action_type === 'Escalation'
                  ? 'bg-purple-100 text-purple-700 border border-purple-200'
                  : 'bg-surface-gray-2 text-ink-gray-8 border border-outline-gray-2'
              "
            >
              {{ __(log.action_type) }}
            </span>
          </div>
          <span class="shrink-0 text-[11px] text-ink-gray-5">{{ log.formatted_datetime }}</span>
        </div>

        <!-- Team change -->
        <div v-if="log.from_team !== log.to_team" class="flex items-center gap-1.5 text-ink-gray-8">
          <span class="text-ink-gray-6">{{ __('Team:') }}</span>
          <span class="line-through text-ink-gray-5">{{ log.from_team || __('None') }}</span>
          <LucideArrowRight class="size-3 text-ink-gray-6" />
          <span class="font-semibold text-ink-gray-9">{{ log.to_team || __('None') }}</span>
        </div>

        <!-- Agent change -->
        <div v-if="log.from_agent !== log.to_agent" class="flex items-center gap-1.5 text-ink-gray-8">
          <span class="text-ink-gray-6">{{ __('Assignee:') }}</span>
          <span class="line-through text-ink-gray-5">{{ log.from_agent_name || __('None') }}</span>
          <LucideArrowRight class="size-3 text-ink-gray-6" />
          <span class="font-semibold text-ink-gray-9">{{ log.to_agent_name || __('Unassigned') }}</span>
        </div>

        <!-- Status transition -->
        <div v-if="log.from_status && log.to_status && log.from_status !== log.to_status" class="flex items-center gap-1.5 text-ink-gray-7">
          <span class="text-ink-gray-6">{{ __('Status:') }}</span>
          <span>{{ log.from_status }}</span>
          <LucideArrowRight class="size-3 text-ink-gray-6" />
          <span class="font-medium text-ink-gray-9">{{ log.to_status }}</span>
        </div>

        <!-- Notes / reason -->
        <div
          v-if="log.reassignment_notes"
          class="bg-surface-white border border-outline-gray-1 rounded px-2 py-1 text-ink-gray-7 text-[11px] italic"
        >
          "{{ log.reassignment_notes }}"
        </div>
      </div>
    </div>

    <!-- Quick Assign / Reassign / Escalate Modal -->
    <QuickReassignModal
      v-if="showReassignModal"
      v-model="showReassignModal"
      :ticket-id="ticketId"
      :subject="ticket?.doc?.subject || ''"
      :current-team="ticket?.doc?.agent_group || ''"
      :current-agent="ticket?.doc?._assign ? (JSON.parse(ticket.doc._assign || '[]')[0] || '') : ''"
      :current-status="ticket?.doc?.status || ''"
      @assigned="handleAssigned"
    />
  </div>
</template>

<script setup lang="ts">
import { __ } from "@/translation";
import { TicketSymbol } from "@/types";
import { Button, LoadingIndicator, createResource } from "frappe-ui";
import { computed, inject, ref } from "vue";
import LucideArrowRight from "~icons/lucide/arrow-right";
import LucideArrowUpRight from "~icons/lucide/arrow-up-right";
import LucideHistory from "~icons/lucide/history";
import LucideRefreshCw from "~icons/lucide/refresh-cw";
import QuickReassignModal from "./QuickReassignModal.vue";

const props = defineProps<{
  ticketId: string;
}>();

const ticket = inject(TicketSymbol, null) as any;
const showReassignModal = ref(false);

const historyResource = createResource({
  url: "helpdesk.api.email_management.get_ticket_assignment_history",
  params: { ticket_id: props.ticketId },
  auto: true,
});

function handleAssigned() {
  historyResource.reload();
  if (ticket?.value?.reload) {
    ticket.value.reload();
  }
}
</script>
