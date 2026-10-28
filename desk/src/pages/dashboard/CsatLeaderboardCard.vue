<template>
  <div class="rounded-xl border border-outline-gray-2 bg-surface-white p-4 shadow-xs">
    <div class="flex items-center justify-between pb-3 border-b border-outline-gray-1">
      <div class="flex items-center gap-2">
        <div class="flex size-7 items-center justify-center rounded-lg bg-amber-50 border border-amber-200 text-amber-500">
          <LucideStar class="size-4 fill-amber-400" />
        </div>
        <h3 class="text-base-semibold text-ink-gray-9">
          {{ __("CSAT & Agent Ratings Leaderboard") }}
        </h3>
      </div>
      <Button
        variant="ghost"
        size="sm"
        @click="csatResource.reload()"
      >
        <LucideRefreshCw class="size-3.5 text-ink-gray-5 hover:text-ink-gray-8" />
      </Button>
    </div>

    <!-- Loading -->
    <div v-if="csatResource.loading" class="flex justify-center py-8">
      <LoadingIndicator class="size-6 text-primary" />
    </div>

    <!-- Empty State -->
    <div
      v-else-if="!csatResource.data || csatResource.data.total_responses === 0"
      class="text-center py-8 text-sm text-ink-gray-5"
    >
      {{ __("No CSAT survey responses recorded in this timeframe.") }}
    </div>

    <!-- Content -->
    <div v-else class="space-y-4 pt-3">
      <!-- Summary Stats -->
      <div class="grid grid-cols-2 gap-3">
        <div class="p-3 rounded-xl bg-surface-white border border-outline-gray-2 border-t-3 border-t-amber-500 shadow-2xs">
          <span class="text-xs font-medium text-ink-gray-6">{{ __("Overall Satisfaction") }}</span>
          <div class="flex items-baseline gap-1 mt-0.5">
            <span class="text-2xl font-bold text-ink-gray-9">
              {{ csatResource.data.average_rating?.toFixed(1) || "0.0" }}
            </span>
            <span class="text-xs text-ink-gray-5">/ 5.0</span>
            <LucideStar class="size-3.5 fill-amber-400 text-amber-500 ml-1" />
          </div>
        </div>
        <div class="p-3 rounded-xl bg-surface-white border border-outline-gray-2 border-t-3 border-t-blue-500 shadow-2xs">
          <span class="text-xs font-medium text-ink-gray-6">{{ __("Total Feedback Responses") }}</span>
          <div class="text-2xl font-bold text-ink-gray-9 mt-0.5">
            {{ csatResource.data.total_responses || 0 }}
          </div>
        </div>
      </div>

      <!-- Agent Rankings -->
      <div class="space-y-2">
        <div class="text-xs font-semibold text-ink-gray-6 uppercase tracking-wider">
          {{ __("Agent Rankings") }}
        </div>
        <div class="space-y-1.5 max-h-48 overflow-y-auto pr-1">
          <div
            v-for="(agent, idx) in csatResource.data.leaderboard"
            :key="agent.agent"
            class="flex items-center justify-between p-2 rounded-lg border border-outline-gray-1 bg-surface-gray-1/40 hover:bg-surface-gray-1 transition-colors text-sm"
          >
            <div class="flex items-center gap-2.5 truncate">
              <span
                class="flex size-5 shrink-0 items-center justify-center rounded-full text-xs font-bold"
                :class="
                  idx === 0
                    ? 'bg-amber-100 text-amber-900 border border-amber-300'
                    : idx === 1
                    ? 'bg-slate-200 text-slate-800 border border-slate-300'
                    : idx === 2
                    ? 'bg-amber-50 text-amber-800 border border-amber-200'
                    : 'bg-surface-gray-2 text-ink-gray-6'
                "
              >
                {{ idx + 1 }}
              </span>
              <span class="font-semibold text-ink-gray-9 truncate">
                {{ agent.agent_name || agent.agent }}
              </span>
            </div>
            <div class="flex items-center gap-3 shrink-0">
              <span class="text-xs text-ink-gray-5">
                {{ agent.response_count }} {{ __("reviews") }}
              </span>
              <div class="flex items-center gap-1 font-bold text-ink-gray-9 text-xs">
                <span>{{ agent.average_rating?.toFixed(1) }}</span>
                <LucideStar class="size-3.5 fill-amber-400 text-amber-500" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { __ } from "@/translation";
import { Button, LoadingIndicator, createResource } from "frappe-ui";
import LucideRefreshCw from "~icons/lucide/refresh-cw";
import LucideStar from "~icons/lucide/star";

const csatResource = createResource({
  url: "helpdesk.api.csat.get_csat_leaderboard",
  auto: true,
});
</script>
