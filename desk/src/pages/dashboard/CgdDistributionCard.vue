<template>
  <div class="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-xs">
    <div class="flex items-center justify-between pb-3 border-b border-slate-100">
      <div class="flex items-center gap-2">
        <LucideBuilding2 class="size-5 text-[#d9531e]" />
        <h3 class="text-sm font-bold text-slate-900">
          {{ __("CGD Entity Distribution & SLA Health") }}
        </h3>
      </div>
      <Button
        variant="ghost"
        size="sm"
        class="!size-7 p-0"
        @click="cgdResource.reload()"
      >
        <LucideRefreshCw class="size-3.5 text-slate-400 hover:text-slate-700" />
      </Button>
    </div>

    <!-- Loading -->
    <div v-if="cgdResource.loading" class="flex justify-center py-8">
      <LoadingIndicator class="size-6 text-[#d9531e]" />
    </div>

    <!-- Empty State -->
    <div
      v-else-if="!cgdResource.data?.entities?.length"
      class="text-center py-8 text-sm text-slate-500"
    >
      {{ __("No CGD customer entities or tickets found.") }}
    </div>

    <!-- Content -->
    <div v-else class="space-y-4 pt-3">
      <!-- High-level KPI summary (Inspired by Reference Palette) -->
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <!-- 1. Active CGD Tickets -->
        <div class="p-3.5 sm:p-4 rounded-2xl bg-[#fafbfd] border border-slate-300 hover:border-indigo-400 shadow-xs transition-all duration-200 hover:shadow-md hover:-translate-y-0.5 flex flex-col justify-between select-none group min-h-[140px]">
          <div class="flex items-center justify-between gap-1.5">
            <div class="flex items-center gap-2 min-w-0">
              <span class="size-2 rounded-full bg-[#1b2a5b] shrink-0" />
              <span class="text-xs sm:text-sm font-semibold text-slate-800 tracking-tight truncate">{{ __("Active CGD Tickets") }}</span>
            </div>
            <div class="size-6 rounded-md flex items-center justify-center shrink-0 text-slate-400 group-hover:scale-110 transition-transform">
              <LucideTicket class="size-3.5" />
            </div>
          </div>
          <div class="mt-1.5">
            <div class="text-2xl sm:text-3xl font-extrabold text-[#1b2a5b] tracking-tight leading-none">
              {{ cgdResource.data.total_active_cgd_tickets || 0 }}
            </div>
            <div class="text-[11px] text-slate-500 font-medium truncate mt-1">
              {{ __("Customer tenant tickets") }}
            </div>
          </div>
          <div class="mt-2">
            <div class="h-1.5 w-full bg-[#eef2f6] rounded-full overflow-hidden">
              <div class="h-full rounded-full bg-[#1b2a5b] w-full transition-all duration-500" />
            </div>
            <div class="flex items-center justify-between text-[11px] font-semibold text-slate-700 mt-1">
              <span>{{ __("All CGD tenants") }}</span>
              <span>100%</span>
            </div>
          </div>
          <div class="flex items-center justify-between pt-2 mt-1.5 border-t border-slate-200/60 text-[11px] font-medium text-slate-500">
            <span>{{ __("Active queue") }}</span>
            <router-link to="/tickets" class="text-[#ea580c] hover:text-[#c2410c] font-semibold inline-flex items-center gap-0.5 transition-colors">
              <span>{{ __("Details") }}</span>
              <LucideChevronDown class="size-3" />
            </router-link>
          </div>
        </div>

        <!-- 2. Urgent / Escalated -->
        <div class="p-3.5 sm:p-4 rounded-2xl bg-[#fefdfa] border border-amber-200/90 hover:border-amber-400 shadow-xs transition-all duration-200 hover:shadow-md hover:-translate-y-0.5 flex flex-col justify-between select-none group min-h-[140px]">
          <div class="flex items-center justify-between gap-1.5">
            <div class="flex items-center gap-2 min-w-0">
              <span class="size-2 rounded-full bg-[#f59e0b] shrink-0" />
              <span class="text-xs sm:text-sm font-semibold text-slate-800 tracking-tight truncate">{{ __("Urgent / Escalated") }}</span>
            </div>
            <div class="size-6 rounded-md flex items-center justify-center shrink-0 text-slate-400 group-hover:scale-110 transition-transform">
              <LucideFlame class="size-3.5 text-amber-500" />
            </div>
          </div>
          <div class="mt-1.5">
            <div class="text-2xl sm:text-3xl font-extrabold text-[#1b2a5b] tracking-tight leading-none">
              {{ cgdResource.data.total_urgent_tickets || 0 }}
            </div>
            <div class="text-[11px] text-slate-500 font-medium truncate mt-1">
              {{ __("Priority & escalation queue") }}
            </div>
          </div>
          <div class="mt-2">
            <div class="h-1.5 w-full bg-[#eef2f6] rounded-full overflow-hidden">
              <div
                class="h-full rounded-full bg-[#f59e0b] transition-all duration-500"
                :style="{ width: cgdResource.data.total_active_cgd_tickets ? ((cgdResource.data.total_urgent_tickets || 0) / cgdResource.data.total_active_cgd_tickets * 100).toFixed(1) + '%' : '0%' }"
              />
            </div>
            <div class="flex items-center justify-between text-[11px] font-semibold text-amber-700 mt-1">
              <span>{{ cgdResource.data.total_active_cgd_tickets ? ((cgdResource.data.total_urgent_tickets || 0) / cgdResource.data.total_active_cgd_tickets * 100).toFixed(1) : 0 }}% of total</span>
              <span>{{ __("Escalated") }}</span>
            </div>
          </div>
          <div class="flex items-center justify-between pt-2 mt-1.5 border-t border-slate-200/60 text-[11px] font-medium text-slate-500">
            <span>{{ __("Urgent status") }}</span>
            <router-link to="/tickets" class="text-[#ea580c] hover:text-[#c2410c] font-semibold inline-flex items-center gap-0.5 transition-colors">
              <span>{{ __("Details") }}</span>
              <LucideChevronDown class="size-3" />
            </router-link>
          </div>
        </div>

        <!-- 3. SLA Risk (<24h) -->
        <div class="p-3.5 sm:p-4 rounded-2xl bg-[#fefbfb] border border-rose-300 hover:border-rose-400 shadow-xs transition-all duration-200 hover:shadow-md hover:-translate-y-0.5 flex flex-col justify-between select-none group min-h-[140px]">
          <div class="flex items-center justify-between gap-1.5">
            <div class="flex items-center gap-2 min-w-0">
              <span class="size-2 rounded-full bg-[#ef4444] shrink-0" />
              <span class="text-xs sm:text-sm font-semibold text-slate-800 tracking-tight truncate">{{ __("SLA Risk (<24h)") }}</span>
            </div>
            <div class="size-6 rounded-md flex items-center justify-center shrink-0 text-slate-400 group-hover:scale-110 transition-transform">
              <LucideAlertTriangle class="size-3.5 text-rose-500" />
            </div>
          </div>
          <div class="mt-1.5">
            <div class="text-2xl sm:text-3xl font-extrabold text-[#1b2a5b] tracking-tight leading-none">
              {{ cgdResource.data.total_sla_risk || 0 }}
            </div>
            <div class="text-[11px] text-slate-500 font-medium truncate mt-1">
              {{ __("Nearing breach threshold") }}
            </div>
          </div>
          <div class="mt-2">
            <div class="h-1.5 w-full bg-[#eef2f6] rounded-full overflow-hidden">
              <div
                class="h-full rounded-full bg-[#ef4444] transition-all duration-500"
                :style="{ width: cgdResource.data.total_active_cgd_tickets ? ((cgdResource.data.total_sla_risk || 0) / cgdResource.data.total_active_cgd_tickets * 100).toFixed(1) + '%' : '0%' }"
              />
            </div>
            <div class="flex items-center justify-between text-[11px] font-semibold text-rose-700 mt-1">
              <span>{{ cgdResource.data.total_active_cgd_tickets ? ((cgdResource.data.total_sla_risk || 0) / cgdResource.data.total_active_cgd_tickets * 100).toFixed(1) : 0 }}% of total</span>
              <span>{{ __("At risk") }}</span>
            </div>
          </div>
          <div class="flex items-center justify-between pt-2 mt-1.5 border-t border-slate-200/60 text-[11px] font-medium text-slate-500">
            <span>{{ __("<24h remaining") }}</span>
            <router-link to="/tickets" class="text-[#ea580c] hover:text-[#c2410c] font-semibold inline-flex items-center gap-0.5 transition-colors">
              <span>{{ __("Details") }}</span>
              <LucideChevronDown class="size-3" />
            </router-link>
          </div>
        </div>
      </div>

      <!-- Entity Table / List -->
      <div class="space-y-2">
        <div class="flex items-center justify-between text-xs font-bold text-slate-600 uppercase tracking-wider">
          <span>{{ __("Entity Breakdown") }}</span>
          <span>{{ __("Open / Risk / Compliance") }}</span>
        </div>
        <div class="space-y-2 max-h-56 overflow-y-auto pr-1">
          <div
            v-for="item in cgdResource.data.entities"
            :key="item.customer"
            class="flex items-center justify-between p-2.5 rounded-lg border border-slate-200 bg-slate-50/80 hover:bg-slate-100/90 transition-colors text-sm"
          >
            <div class="flex items-center gap-2 truncate">
              <LucideCrown
                v-if="item.is_vip"
                class="size-4 text-amber-500 shrink-0"
                title="VIP CGD Entity"
              />
              <span class="font-bold text-slate-900 truncate">
                {{ item.customer_name }}
              </span>
              <span
                v-if="item.is_vip"
                class="text-[10px] uppercase font-extrabold tracking-wider px-2 py-0.5 rounded-full bg-amber-50 text-amber-800 border border-amber-300 shrink-0"
              >
                VIP
              </span>
            </div>
            <div class="flex items-center gap-2 shrink-0 text-xs">
              <!-- Active tickets count -->
              <span class="font-bold text-slate-800">
                {{ item.open_tickets }} {{ __("open") }}
              </span>
              <!-- Risk count -->
              <span
                v-if="item.sla_risk_count > 0"
                class="px-2 py-0.5 rounded-full bg-rose-50 text-rose-700 border border-rose-200 font-semibold"
                title="Tickets at risk of SLA breach within 24h"
              >
                {{ item.sla_risk_count }} {{ __("at risk") }}
              </span>
              <!-- SLA compliance pill -->
              <span
                class="px-2.5 py-0.5 rounded-full font-bold border"
                :class="
                  item.sla_compliance_rate >= 90
                    ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                    : 'bg-amber-50 text-amber-700 border-amber-200'
                "
              >
                {{ item.sla_compliance_rate?.toFixed(0) }}%
              </span>
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
import LucideAlertTriangle from "~icons/lucide/alert-triangle";
import LucideBuilding2 from "~icons/lucide/building-2";
import LucideChevronDown from "~icons/lucide/chevron-down";
import LucideCrown from "~icons/lucide/crown";
import LucideFlame from "~icons/lucide/flame";
import LucideRefreshCw from "~icons/lucide/refresh-cw";
import LucideTicket from "~icons/lucide/ticket";

const cgdResource = createResource({
  url: "helpdesk.api.custom_reports.get_cgd_entity_breakdown",
  auto: true,
});
</script>
