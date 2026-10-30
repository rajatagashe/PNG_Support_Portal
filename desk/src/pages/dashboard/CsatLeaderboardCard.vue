<template>
  <div class="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-xs">
    <div class="flex items-center justify-between pb-3 border-b border-slate-100">
      <div class="flex items-center gap-2">
        <div class="flex size-7 items-center justify-center rounded-lg bg-orange-50 border border-orange-200 text-[#d9531e]">
          <LucideStar class="size-4 fill-orange-400" />
        </div>
        <h3 class="text-sm font-bold text-slate-900">
          {{ __("CSAT & Agent Ratings Leaderboard") }}
        </h3>
      </div>
      <Button
        variant="ghost"
        size="sm"
        class="!size-7 p-0"
        @click="csatResource.reload()"
      >
        <LucideRefreshCw class="size-3.5 text-slate-400 hover:text-slate-700" />
      </Button>
    </div>

    <!-- Loading -->
    <div v-if="csatResource.loading" class="flex justify-center py-8">
      <LoadingIndicator class="size-6 text-[#d9531e]" />
    </div>

    <!-- Empty State -->
    <div
      v-else-if="!csatResource.data || csatResource.data.total_responses === 0"
      class="text-center py-8 text-sm text-slate-500"
    >
      {{ __("No CSAT survey responses recorded in this timeframe.") }}
    </div>

    <!-- Content -->
    <div v-else class="space-y-4 pt-3">
      <!-- Summary Stats (Inspired by Reference Palette) -->
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <!-- 1. Overall Satisfaction -->
        <div class="p-3.5 sm:p-4 rounded-2xl bg-[#fefdfa] border border-amber-200/90 hover:border-amber-400 shadow-xs transition-all duration-200 hover:shadow-md hover:-translate-y-0.5 flex flex-col justify-between select-none group min-h-[140px]">
          <div class="flex items-center justify-between gap-1.5">
            <div class="flex items-center gap-2 min-w-0">
              <span class="size-2 rounded-full bg-[#f59e0b] shrink-0" />
              <span class="text-xs sm:text-sm font-semibold text-slate-800 tracking-tight truncate">{{ __("Overall Satisfaction") }}</span>
            </div>
            <div class="size-6 rounded-md flex items-center justify-center shrink-0 text-slate-400 group-hover:scale-110 transition-transform">
              <LucideStar class="size-3.5 fill-amber-400 text-amber-500" />
            </div>
          </div>
          <div class="mt-1.5">
            <div class="flex items-baseline gap-1">
              <span class="text-2xl sm:text-3xl font-extrabold text-[#1b2a5b] tracking-tight leading-none">
                {{ csatResource.data.average_rating?.toFixed(1) || "0.0" }}
              </span>
              <span class="text-xs text-slate-500 font-bold">/ 5.0</span>
            </div>
            <div class="text-[11px] text-slate-500 font-medium truncate mt-1">
              {{ __("Average customer rating") }}
            </div>
          </div>
          <div class="mt-2">
            <div class="h-1.5 w-full bg-[#eef2f6] rounded-full overflow-hidden">
              <div
                class="h-full rounded-full bg-[#f59e0b] transition-all duration-500"
                :style="{ width: ((csatResource.data.average_rating || 0) / 5 * 100) + '%' }"
              />
            </div>
            <div class="flex items-center justify-between text-[11px] font-semibold text-amber-700 mt-1">
              <span>{{ ((csatResource.data.average_rating || 0) / 5 * 100).toFixed(0) }}% satisfaction</span>
              <span>CSAT</span>
            </div>
          </div>
          <div class="flex items-center justify-between pt-2 mt-1.5 border-t border-slate-200/60 text-[11px] font-medium text-slate-500">
            <span>{{ __("Verified surveys") }}</span>
            <router-link to="/tickets" class="text-[#ea580c] hover:text-[#c2410c] font-semibold inline-flex items-center gap-0.5 transition-colors">
              <span>{{ __("Details") }}</span>
              <LucideChevronDown class="size-3" />
            </router-link>
          </div>
        </div>

        <!-- 2. Total Feedback Responses -->
        <div class="p-3.5 sm:p-4 rounded-2xl bg-[#fafbfd] border border-slate-300 hover:border-indigo-400 shadow-xs transition-all duration-200 hover:shadow-md hover:-translate-y-0.5 flex flex-col justify-between select-none group min-h-[140px]">
          <div class="flex items-center justify-between gap-1.5">
            <div class="flex items-center gap-2 min-w-0">
              <span class="size-2 rounded-full bg-[#1b2a5b] shrink-0" />
              <span class="text-xs sm:text-sm font-semibold text-slate-800 tracking-tight truncate">{{ __("Total Feedback Responses") }}</span>
            </div>
            <div class="size-6 rounded-md flex items-center justify-center shrink-0 text-slate-400 group-hover:scale-110 transition-transform">
              <LucideMessageSquare class="size-3.5 text-blue-600" />
            </div>
          </div>
          <div class="mt-1.5">
            <div class="text-2xl sm:text-3xl font-extrabold text-[#1b2a5b] tracking-tight leading-none">
              {{ csatResource.data.total_responses || 0 }}
            </div>
            <div class="text-[11px] text-slate-500 font-medium truncate mt-1">
              {{ __("Completed survey scorecards") }}
            </div>
          </div>
          <div class="mt-2">
            <div class="h-1.5 w-full bg-[#eef2f6] rounded-full overflow-hidden">
              <div class="h-full rounded-full bg-[#1b2a5b] w-full transition-all duration-500" />
            </div>
            <div class="flex items-center justify-between text-[11px] font-semibold text-slate-700 mt-1">
              <span>100% response volume</span>
              <span>{{ __("Audited") }}</span>
            </div>
          </div>
          <div class="flex items-center justify-between pt-2 mt-1.5 border-t border-slate-200/60 text-[11px] font-medium text-slate-500">
            <span>{{ __("All responses") }}</span>
            <router-link to="/tickets" class="text-[#ea580c] hover:text-[#c2410c] font-semibold inline-flex items-center gap-0.5 transition-colors">
              <span>{{ __("Details") }}</span>
              <LucideChevronDown class="size-3" />
            </router-link>
          </div>
        </div>
      </div>

      <!-- Agent Rankings -->
      <div class="space-y-2">
        <div class="text-xs font-bold text-slate-600 uppercase tracking-wider">
          {{ __("Agent Rankings") }}
        </div>
        <div class="space-y-1.5 max-h-48 overflow-y-auto pr-1">
          <div
            v-for="(agent, idx) in csatResource.data.leaderboard"
            :key="agent.agent"
            class="flex items-center justify-between p-2 rounded-lg border border-slate-200 bg-slate-50/80 hover:bg-slate-100/90 transition-colors text-sm"
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
                    : 'bg-slate-100 text-slate-700'
                "
              >
                {{ idx + 1 }}
              </span>
              <span class="font-bold text-slate-900 truncate">
                {{ agent.agent_name || agent.agent }}
              </span>
            </div>
            <div class="flex items-center gap-3 shrink-0">
              <span class="text-xs text-slate-500 font-medium">
                {{ agent.response_count }} {{ __("reviews") }}
              </span>
              <div class="flex items-center gap-1 font-bold text-slate-900 text-xs">
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
import LucideChevronDown from "~icons/lucide/chevron-down";
import LucideMessageSquare from "~icons/lucide/message-square";
import LucideRefreshCw from "~icons/lucide/refresh-cw";
import LucideStar from "~icons/lucide/star";

const csatResource = createResource({
  url: "helpdesk.api.csat.get_csat_leaderboard",
  auto: true,
});
</script>
