<template>
  <div class="rounded-lg border border-outline-gray-2 bg-surface-white p-4 shadow-sm">
    <div class="flex items-center justify-between pb-3 border-b border-outline-gray-1">
      <div class="flex items-center gap-2">
        <LucideStar class="size-5 text-ink-gray-8 fill-ink-gray-8" />
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
      <LoadingIndicator class="size-6 text-ink-gray-6" />
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
      <div class="grid grid-cols-2 gap-4 bg-surface-gray-1 p-3 rounded-md">
        <div>
          <span class="text-xs text-ink-gray-6">{{ __("Overall Satisfaction") }}</span>
          <div class="flex items-baseline gap-1 mt-0.5">
            <span class="text-2xl font-bold text-ink-gray-9">
              {{ csatResource.data.average_rating?.toFixed(1) || "0.0" }}
            </span>
            <span class="text-xs text-ink-gray-5">/ 5.0</span>
          </div>
        </div>
        <div>
          <span class="text-xs text-ink-gray-6">{{ __("Total Feedback Responses") }}</span>
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
        <div class="space-y-2 max-h-48 overflow-y-auto pr-1">
          <div
            v-for="(agent, idx) in csatResource.data.leaderboard"
            :key="agent.agent"
            class="flex items-center justify-between p-2 rounded hover:bg-surface-gray-1 transition-colors text-sm"
          >
            <div class="flex items-center gap-2.5 truncate">
              <span
                class="flex size-5 items-center justify-center rounded-full text-xs font-bold"
                :class="
                  idx === 0
                    ? 'bg-surface-gray-3 text-ink-gray-9'
                    : 'bg-surface-gray-2 text-ink-gray-6'
                "
              >
                {{ idx + 1 }}
              </span>
              <span class="font-medium text-ink-gray-9 truncate">
                {{ agent.agent_name || agent.agent }}
              </span>
            </div>
            <div class="flex items-center gap-3 shrink-0">
              <span class="text-xs text-ink-gray-5">
                {{ agent.response_count }} {{ __("reviews") }}
              </span>
              <div class="flex items-center gap-1 font-semibold text-ink-gray-9 text-xs">
                <span>{{ agent.average_rating?.toFixed(1) }}</span>
                <LucideStar class="size-3 fill-ink-gray-8 text-ink-gray-8" />
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
