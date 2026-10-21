<template>
  <div class="h-full flex-1 overflow-y-auto bg-surface-gray-1 p-6 space-y-6">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
      <div>
        <div class="flex items-center gap-2">
          <h1 class="text-2xl font-bold text-ink-gray-9 tracking-tight">
            {{ __("CGD Ticket Management Dashboard") }}
          </h1>
          <span
            v-if="analyticsResource.data?.cgd_name"
            class="px-2.5 py-0.5 rounded text-xs font-semibold bg-surface-gray-3 text-ink-gray-9 border border-outline-gray-2"
          >
            {{ analyticsResource.data.cgd_name }}
          </span>
        </div>
        <p class="text-xs text-ink-gray-6 mt-1">
          {{ analyticsResource.data?.period_label || __("Live performance metrics and status tracking") }}
        </p>
      </div>

      <!-- Action Buttons -->
      <div class="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          :label="__('Refresh')"
          :loading="analyticsResource.loading"
          @click="analyticsResource.reload()"
        >
          <template #prefix>
            <LucideRefreshCw class="size-3.5 text-ink-gray-6" />
          </template>
        </Button>

        <Button
          variant="outline"
          size="sm"
          :label="__('Export Excel (.xlsx)')"
          :loading="isExporting"
          @click="downloadExcelReport"
        >
          <template #prefix>
            <LucideDownload class="size-3.5 text-ink-gray-6" />
          </template>
        </Button>

        <Button
          variant="solid"
          size="sm"
          :label="__('Raise New Ticket')"
          @click="router.push({ name: 'TicketNew' })"
        >
          <template #prefix>
            <LucidePlus class="size-3.5" />
          </template>
        </Button>
      </div>
    </div>

    <!-- Filter Bar -->
    <div class="bg-surface-white border border-outline-gray-2 rounded-lg p-4 shadow-sm flex flex-wrap items-center justify-between gap-3">
      <!-- Time Period Switcher -->
      <div class="flex items-center gap-1 bg-surface-gray-2 p-1 rounded-md border border-outline-gray-1">
        <button
          v-for="mode in viewModes"
          :key="mode.value"
          type="button"
          class="px-3 py-1 text-xs font-medium rounded transition-colors"
          :class="
            selectedViewMode === mode.value
              ? 'bg-surface-white text-ink-gray-9 shadow-sm font-semibold'
              : 'text-ink-gray-6 hover:text-ink-gray-9'
          "
          @click="changeViewMode(mode.value)"
        >
          {{ mode.label }}
        </button>
      </div>

      <!-- Custom Date Picker Row -->
      <div v-if="selectedViewMode === 'custom'" class="flex items-center gap-2">
        <input
          v-model="customDateFrom"
          type="date"
          class="text-xs border border-outline-gray-2 rounded px-2.5 py-1 bg-surface-white text-ink-gray-9 focus:outline-none focus:border-outline-gray-4"
        />
        <span class="text-xs text-ink-gray-5">{{ __("to") }}</span>
        <input
          v-model="customDateTo"
          type="date"
          class="text-xs border border-outline-gray-2 rounded px-2.5 py-1 bg-surface-white text-ink-gray-9 focus:outline-none focus:border-outline-gray-4"
        />
        <Button
          variant="subtle"
          size="sm"
          :label="__('Apply')"
          @click="fetchAnalytics"
        />
      </div>

      <div class="text-xs text-ink-gray-5">
        <span class="font-medium text-ink-gray-7">{{ __("Timezone:") }}</span> {{ __("Configured Local Time") }}
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="analyticsResource.loading && !analyticsResource.data" class="flex justify-center items-center py-20">
      <LoadingIndicator class="size-8 text-ink-gray-6" />
    </div>

    <!-- Analytics Content -->
    <template v-else-if="analyticsResource.data">
      <!-- KPI Summary Cards -->
      <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <!-- Total -->
        <div class="modern-card border-t-2 border-t-primary p-4 flex flex-col justify-between">
          <div class="flex items-center justify-between text-ink-gray-6">
            <span class="text-xs font-semibold uppercase tracking-wider">{{ __("Total Tickets") }}</span>
            <div class="p-1 rounded-md bg-surface-gray-2 text-primary">
              <LucideTicket class="size-4" />
            </div>
          </div>
          <div class="text-2xl font-bold text-ink-gray-9 mt-2">
            {{ analyticsResource.data.summary.total_tickets }}
          </div>
          <div class="text-[11px] text-ink-gray-5 mt-1">{{ __("Raised in period") }}</div>
        </div>

        <!-- Open -->
        <div class="modern-card border-t-2 border-t-sky-500 p-4 flex flex-col justify-between">
          <div class="flex items-center justify-between text-ink-gray-6">
            <span class="text-xs font-semibold uppercase tracking-wider">{{ __("Open / Pending") }}</span>
            <div class="p-1 rounded-md bg-sky-50 text-sky-600">
              <LucideClock class="size-4" />
            </div>
          </div>
          <div class="text-2xl font-bold text-ink-gray-9 mt-2">
            {{ analyticsResource.data.summary.open_tickets }}
          </div>
          <div class="text-[11px] text-ink-gray-5 mt-1">{{ __("Awaiting action") }}</div>
        </div>

        <!-- In Progress -->
        <div class="modern-card border-t-2 border-t-amber-500 p-4 flex flex-col justify-between">
          <div class="flex items-center justify-between text-ink-gray-6">
            <span class="text-xs font-semibold uppercase tracking-wider">{{ __("In Progress") }}</span>
            <div class="p-1 rounded-md bg-amber-50 text-amber-600">
              <LucideActivity class="size-4" />
            </div>
          </div>
          <div class="text-2xl font-bold text-ink-gray-9 mt-2">
            {{ analyticsResource.data.summary.in_progress }}
          </div>
          <div class="text-[11px] text-ink-gray-5 mt-1">{{ __("Under active review") }}</div>
        </div>

        <!-- Resolved -->
        <div class="modern-card border-t-2 border-t-emerald-500 p-4 flex flex-col justify-between">
          <div class="flex items-center justify-between text-ink-gray-6">
            <span class="text-xs font-semibold uppercase tracking-wider">{{ __("Resolved / Closed") }}</span>
            <div class="p-1 rounded-md bg-emerald-50 text-emerald-600">
              <LucideCheckCircle2 class="size-4" />
            </div>
          </div>
          <div class="text-2xl font-bold text-ink-gray-9 mt-2">
            {{ analyticsResource.data.summary.resolved_tickets }}
          </div>
          <div class="text-[11px] text-emerald-600 font-medium mt-1">{{ __("With resolution note") }}</div>
        </div>

        <!-- Escalated -->
        <div class="modern-card border-t-2 border-t-purple-500 p-4 flex flex-col justify-between">
          <div class="flex items-center justify-between text-ink-gray-6">
            <span class="text-xs font-semibold uppercase tracking-wider">{{ __("Escalated (L2)") }}</span>
            <div class="p-1 rounded-md bg-purple-50 text-purple-600">
              <LucideAlertTriangle class="size-4" />
            </div>
          </div>
          <div class="text-2xl font-bold text-ink-gray-9 mt-2">
            {{ analyticsResource.data.summary.escalated_tickets }}
          </div>
          <div class="text-[11px] text-purple-600 font-medium mt-1">{{ __("Tier 2 investigation") }}</div>
        </div>

        <!-- SLA Adherence -->
        <div class="modern-card border-t-2 border-t-emerald-600 p-4 flex flex-col justify-between">
          <div class="flex items-center justify-between text-ink-gray-6">
            <span class="text-xs font-semibold uppercase tracking-wider">{{ __("SLA Compliance") }}</span>
            <div class="p-1 rounded-md bg-emerald-50 text-emerald-700">
              <LucideShieldCheck class="size-4" />
            </div>
          </div>
          <div class="text-2xl font-bold text-ink-gray-9 mt-2">
            {{ analyticsResource.data.summary.sla_adherence_percent }}%
          </div>
          <!-- Micro SLA target bar -->
          <div class="w-full bg-surface-gray-2 h-1.5 rounded-full overflow-hidden mt-1.5">
            <div
              class="h-full rounded-full bg-emerald-500 transition-all duration-300"
              :style="{ width: `${analyticsResource.data.summary.sla_adherence_percent}%` }"
            ></div>
          </div>
          <div class="text-[10px] text-ink-gray-5 mt-1">
            {{ __("Avg: {0}h", [analyticsResource.data.summary.avg_resolution_hours]) }}
          </div>
        </div>
      </div>

      <!-- Priority and Team Allocation Grid -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <!-- Priority Breakdown -->
        <div class="modern-card p-5 space-y-4">
          <div class="flex items-center justify-between">
            <h2 class="text-xs font-bold text-ink-gray-9 uppercase tracking-wider">
              {{ __("Tickets by Priority") }}
            </h2>
            <span class="text-xs text-ink-gray-5">{{ __("Urgency distribution") }}</span>
          </div>

          <div class="space-y-3">
            <div
              v-for="(count, priority) in analyticsResource.data.priority_breakdown"
              :key="priority"
              class="space-y-1"
            >
              <div class="flex justify-between text-xs font-medium text-ink-gray-8">
                <span>{{ priority }}</span>
                <span>{{ count }} ({{ calculatePercent(count, analyticsResource.data.summary.total_tickets) }}%)</span>
              </div>
              <div class="w-full bg-surface-gray-2 h-2 rounded-full overflow-hidden">
                <div
                  class="h-full rounded-full transition-all duration-300"
                  :class="
                    priority === 'Urgent'
                      ? 'bg-rose-500'
                      : priority === 'High'
                      ? 'bg-amber-500'
                      : priority === 'Medium'
                      ? 'bg-sky-500'
                      : 'bg-emerald-500'
                  "
                  :style="{ width: calculatePercent(count, analyticsResource.data.summary.total_tickets) + '%' }"
                />
              </div>
            </div>
          </div>
        </div>

        <!-- Support Team Breakdown -->
        <div class="modern-card p-5 space-y-4">
          <div class="flex items-center justify-between">
            <h2 class="text-xs font-bold text-ink-gray-9 uppercase tracking-wider">
              {{ __("Support Team Assignment") }}
            </h2>
            <span class="text-xs text-ink-gray-5">{{ __("L1 / L2 team allocation") }}</span>
          </div>

          <div v-if="!Object.keys(analyticsResource.data.team_breakdown || {}).length" class="text-xs text-ink-gray-5 py-4 text-center">
            {{ __("No team assignment data available for this range.") }}
          </div>

          <div v-else class="space-y-3">
            <div
              v-for="(count, team) in analyticsResource.data.team_breakdown"
              :key="team"
              class="flex items-center justify-between p-2.5 rounded-lg border border-outline-gray-2 bg-surface-gray-1"
            >
              <div class="flex items-center gap-2">
                <span
                  class="px-2 py-0.5 rounded-full text-[10px] font-bold"
                  :class="team.includes('L2') ? 'bg-purple-100 text-purple-700 border border-purple-200' : 'bg-surface-gray-3 text-ink-gray-8 border border-outline-gray-2'"
                >
                  {{ team.includes('L2') ? 'L2' : 'L1' }}
                </span>
                <span class="text-xs font-semibold text-ink-gray-9">{{ team }}</span>
              </div>
              <span class="text-xs font-bold text-ink-gray-8">{{ count }} {{ __("tickets") }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Recent Tickets Table -->
      <div class="modern-card overflow-hidden space-y-3 p-5">
        <div class="flex items-center justify-between">
          <div>
            <h2 class="text-xs font-bold text-ink-gray-9 uppercase tracking-wider">
              {{ __("Recent Tickets & Resolution Tracking") }}
            </h2>
            <p class="text-xs text-ink-gray-5 mt-0.5">
              {{ __("Click any ticket to view live progress, agent discussion, resolution details, or diagnostic attachments.") }}
            </p>
          </div>
          <Button
            variant="ghost"
            size="sm"
            :label="__('View All Tickets')"
            @click="router.push({ name: 'TicketsCustomer' })"
          >
            <template #suffix>
              <LucideArrowRight class="size-3.5" />
            </template>
          </Button>
        </div>

        <div v-if="!analyticsResource.data.recent_tickets?.length" class="text-xs text-ink-gray-5 py-8 text-center border rounded-lg border-outline-gray-1">
          {{ __("No tickets found in the selected date range.") }}
        </div>

        <div v-else class="border border-outline-gray-2 rounded-lg overflow-x-auto shadow-2xs">
          <table class="w-full text-left border-collapse text-xs">
            <thead>
              <tr class="bg-surface-gray-2 border-b border-outline-gray-2 text-ink-gray-7 font-semibold">
                <th class="py-2.5 px-3">{{ __("Ticket ID") }}</th>
                <th class="py-2.5 px-3">{{ __("Subject") }}</th>
                <th class="py-2.5 px-3">{{ __("Priority") }}</th>
                <th class="py-2.5 px-3">{{ __("Status") }}</th>
                <th class="py-2.5 px-3">{{ __("Assigned Tier") }}</th>
                <th class="py-2.5 px-3">{{ __("Resolution Status") }}</th>
                <th class="py-2.5 px-3">{{ __("Created") }}</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-outline-gray-1">
              <tr
                v-for="t in analyticsResource.data.recent_tickets"
                :key="t.name"
                class="hover:bg-surface-gray-1 cursor-pointer transition-colors"
                @click="openTicket(t.name)"
              >
                <td class="py-2.5 px-3 font-semibold text-ink-gray-9 whitespace-nowrap">
                  {{ t.name }}
                </td>
                <td class="py-2.5 px-3 font-medium text-ink-gray-9 max-w-[280px] truncate">
                  {{ t.subject }}
                </td>
                <td class="py-2.5 px-3 whitespace-nowrap">
                  <span
                    class="px-2 py-0.5 rounded text-[11px] font-semibold"
                    :class="
                      t.priority === 'Urgent'
                        ? 'bg-rose-50 text-rose-700 border border-rose-200'
                        : t.priority === 'High'
                        ? 'bg-amber-50 text-amber-700 border border-amber-200'
                        : 'bg-surface-gray-2 text-ink-gray-8 border border-outline-gray-2'
                    "
                  >
                    {{ t.priority || "Medium" }}
                  </span>
                </td>
                <td class="py-2.5 px-3 whitespace-nowrap">
                  <span
                    class="status-pill"
                    :class="{
                      'status-pill-resolved': t.status === 'Resolved',
                      'status-pill-closed': t.status === 'Closed',
                      'status-pill-open': t.status === 'Open',
                      'status-pill-pending': t.status === 'Pending' || t.status === 'Replied',
                    }"
                  >
                    <span
                      class="size-1.5 rounded-full"
                      :class="{
                        'bg-emerald-500': t.status === 'Resolved',
                        'bg-surface-gray-6': t.status === 'Closed',
                        'bg-sky-500 animate-pulse': t.status === 'Open',
                        'bg-amber-500': t.status === 'Pending' || t.status === 'Replied',
                      }"
                    ></span>
                    {{ t.status }}
                  </span>
                </td>
                <td class="py-2.5 px-3 whitespace-nowrap">
                  <div class="flex items-center gap-1.5">
                    <span
                      class="px-2 py-0.5 rounded-full text-[10px] font-bold"
                      :class="
                        t.is_escalated || t.escalation_level === 'L2'
                          ? 'bg-purple-100 text-purple-700 border border-purple-200'
                          : 'bg-surface-gray-2 text-ink-gray-7 border border-outline-gray-2'
                      "
                    >
                      {{ t.escalation_level || "L1" }}
                    </span>
                    <span class="text-ink-gray-7 font-medium">{{ t.team }}</span>
                  </div>
                </td>
                <td class="py-2.5 px-3 whitespace-nowrap">
                  <div v-if="t.has_resolution" class="flex items-center gap-1 text-emerald-700 font-semibold">
                    <LucideCheckCircle2 class="size-3.5 text-emerald-600" />
                    <span>{{ __("Resolution Available") }}</span>
                  </div>
                  <span v-else class="text-ink-gray-5">{{ __("Pending Resolution") }}</span>
                </td>
                <td class="py-2.5 px-3 text-ink-gray-6 whitespace-nowrap">
                  {{ t.creation }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { __ } from "@/translation";
import { Button, LoadingIndicator, createResource, toast } from "frappe-ui";
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import LucideActivity from "~icons/lucide/activity";
import LucideAlertTriangle from "~icons/lucide/alert-triangle";
import LucideArrowRight from "~icons/lucide/arrow-right";
import LucideCheckCircle2 from "~icons/lucide/check-circle-2";
import LucideClock from "~icons/lucide/clock";
import LucideDownload from "~icons/lucide/download";
import LucidePlus from "~icons/lucide/plus";
import LucideRefreshCw from "~icons/lucide/refresh-cw";
import LucideShieldCheck from "~icons/lucide/shield-check";
import LucideTicket from "~icons/lucide/ticket";

const router = useRouter();

const viewModes = [
  { label: __("Daily"), value: "daily" },
  { label: __("Weekly"), value: "weekly" },
  { label: __("Monthly"), value: "monthly" },
  { label: __("Custom Range"), value: "custom" },
];

const selectedViewMode = ref("daily");
const customDateFrom = ref("");
const customDateTo = ref("");
const isExporting = ref(false);

const analyticsResource = createResource({
  url: "helpdesk.api.cgd_portal.get_cgd_dashboard_analytics",
  params: {
    view_mode: selectedViewMode.value,
  },
  auto: true,
});

function changeViewMode(mode: string) {
  selectedViewMode.value = mode;
  if (mode !== "custom") {
    fetchAnalytics();
  }
}

function fetchAnalytics() {
  analyticsResource.fetch({
    view_mode: selectedViewMode.value,
    date_from: selectedViewMode.value === "custom" ? customDateFrom.value : null,
    date_to: selectedViewMode.value === "custom" ? customDateTo.value : null,
  });
}

function calculatePercent(val: number, total: number) {
  if (!total || total === 0) return 0;
  return Math.round((val / total) * 100);
}

function openTicket(ticketId: string) {
  router.push({
    name: "TicketCustomer",
    params: { ticketId },
  });
}

const exportResource = createResource({
  url: "helpdesk.api.cgd_portal.export_cgd_report_xlsx",
  auto: false,
});

async function downloadExcelReport() {
  isExporting.value = true;
  try {
    const res = await exportResource.submit({
      date_from: selectedViewMode.value === "custom" ? customDateFrom.value : null,
      date_to: selectedViewMode.value === "custom" ? customDateTo.value : null,
    });

    if (res?.base64_content) {
      const binaryString = window.atob(res.base64_content);
      const bytes = new Uint8Array(binaryString.length);
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }
      const blob = new Blob([bytes], {
        type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      });
      const link = document.createElement("a");
      const url = URL.createObjectURL(blob);
      link.setAttribute("href", url);
      link.setAttribute("download", res.filename || "CGD_Ticket_Report.xlsx");
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

      toast.success(
        __("Excel report with {0} tickets and audit history downloaded.", [
          res.total_tickets,
        ])
      );
    }
  } catch (error: any) {
    toast.error(error.message || __("Failed to export Excel report."));
  } finally {
    isExporting.value = false;
  }
}

onMounted(() => {
  const today = new Date().toISOString().split("T")[0];
  customDateFrom.value = today;
  customDateTo.value = today;
});
</script>
