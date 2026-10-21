<template>
  <div class="rounded-lg border border-outline-gray-2 bg-surface-white p-4 shadow-sm">
    <div class="flex items-center justify-between pb-3 border-b border-outline-gray-1">
      <div class="flex items-center gap-2">
        <LucideBuilding2 class="size-5 text-ink-gray-8" />
        <h3 class="text-base-semibold text-ink-gray-9">
          {{ __("CGD Entity Distribution & SLA Health") }}
        </h3>
      </div>
      <Button
        variant="ghost"
        size="sm"
        @click="cgdResource.reload()"
      >
        <LucideRefreshCw class="size-3.5 text-ink-gray-5 hover:text-ink-gray-8" />
      </Button>
    </div>

    <!-- Loading -->
    <div v-if="cgdResource.loading" class="flex justify-center py-8">
      <LoadingIndicator class="size-6 text-ink-gray-6" />
    </div>

    <!-- Empty State -->
    <div
      v-else-if="!cgdResource.data?.entities?.length"
      class="text-center py-8 text-sm text-ink-gray-5"
    >
      {{ __("No CGD customer entities or tickets found.") }}
    </div>

    <!-- Content -->
    <div v-else class="space-y-4 pt-3">
      <!-- High-level KPI summary -->
      <div class="grid grid-cols-3 gap-3 bg-surface-gray-1 p-3 rounded-md">
        <div>
          <span class="text-xs text-ink-gray-6">{{ __("Active CGD Tickets") }}</span>
          <div class="text-2xl font-bold text-ink-gray-9 mt-0.5">
            {{ cgdResource.data.total_active_cgd_tickets || 0 }}
          </div>
        </div>
        <div>
          <span class="text-xs text-ink-gray-6">{{ __("Urgent / Escalated") }}</span>
          <div class="flex items-center gap-1.5 mt-0.5">
            <span class="text-2xl font-bold text-ink-gray-9">
              {{ cgdResource.data.total_urgent_tickets || 0 }}
            </span>
            <LucideFlame
              v-if="cgdResource.data.total_urgent_tickets > 0"
              class="size-4 text-ink-gray-7"
            />
          </div>
        </div>
        <div>
          <span class="text-xs text-ink-gray-6">{{ __("SLA Risk (<24h)") }}</span>
          <div class="flex items-center gap-1.5 mt-0.5">
            <span class="text-2xl font-bold text-ink-gray-9">
              {{ cgdResource.data.total_sla_risk || 0 }}
            </span>
            <LucideAlertTriangle
              v-if="cgdResource.data.total_sla_risk > 0"
              class="size-4 text-ink-gray-7"
            />
          </div>
        </div>
      </div>

      <!-- Entity Table / List -->
      <div class="space-y-2">
        <div class="flex items-center justify-between text-xs font-semibold text-ink-gray-6 uppercase tracking-wider">
          <span>{{ __("Entity Breakdown") }}</span>
          <span>{{ __("Open / Risk / Compliance") }}</span>
        </div>
        <div class="space-y-2 max-h-56 overflow-y-auto pr-1">
          <div
            v-for="item in cgdResource.data.entities"
            :key="item.customer"
            class="flex items-center justify-between p-2 rounded hover:bg-surface-gray-1 transition-colors text-sm"
          >
            <div class="flex items-center gap-2 truncate">
              <LucideCrown
                v-if="item.is_vip"
                class="size-3.5 text-ink-gray-9 shrink-0"
                title="VIP CGD Entity"
              />
              <span class="font-medium text-ink-gray-9 truncate">
                {{ item.customer_name }}
              </span>
              <span
                v-if="item.is_vip"
                class="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-surface-gray-3 text-ink-gray-9 shrink-0"
              >
                VIP
              </span>
            </div>
            <div class="flex items-center gap-2 shrink-0 text-xs">
              <!-- Active tickets count -->
              <span class="font-semibold text-ink-gray-8">
                {{ item.open_tickets }} {{ __("open") }}
              </span>
              <!-- Risk count -->
              <span
                v-if="item.sla_risk_count > 0"
                class="px-1.5 py-0.5 rounded bg-surface-gray-2 text-ink-gray-8 font-medium"
                title="Tickets at risk of SLA breach within 24h"
              >
                {{ item.sla_risk_count }} {{ __("at risk") }}
              </span>
              <!-- SLA compliance pill -->
              <span
                class="px-2 py-0.5 rounded font-bold"
                :class="
                  item.sla_compliance_rate >= 90
                    ? 'bg-surface-gray-2 text-ink-gray-9'
                    : 'bg-surface-gray-3 text-ink-gray-8'
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
import LucideCrown from "~icons/lucide/crown";
import LucideFlame from "~icons/lucide/flame";
import LucideRefreshCw from "~icons/lucide/refresh-cw";

const cgdResource = createResource({
  url: "helpdesk.api.custom_reports.get_cgd_entity_breakdown",
  auto: true,
});
</script>
