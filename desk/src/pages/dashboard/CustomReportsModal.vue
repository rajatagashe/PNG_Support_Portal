<template>
  <Dialog
    v-model="isOpen"
    :options="{
      title: __('Custom Ad-Hoc Report Builder & Multi-Format Export'),
      size: 'xl',
    }"
  >
    <template #body-content>
      <div class="space-y-4 py-2">
        <!-- Controls Grid -->
        <div class="grid grid-cols-1 sm:grid-cols-4 gap-3 bg-surface-gray-1 p-3 rounded-lg border border-outline-gray-1">
          <FormControl
            v-model="filters.group_by"
            type="select"
            :label="__('Group Dimension')"
            :options="[
              { label: __('Customer / CGD Entity'), value: 'customer' },
              { label: __('Priority Level'), value: 'priority' },
              { label: __('Status Category'), value: 'status' },
              { label: __('Support Team'), value: 'agent_group' },
            ]"
          />
          <FormControl
            v-model="filters.status"
            type="select"
            :label="__('Status Filter')"
            :options="[
              { label: __('All Statuses'), value: '' },
              { label: __('Open'), value: 'Open' },
              { label: __('Resolved'), value: 'Resolved' },
              { label: __('Closed'), value: 'Closed' },
            ]"
          />
          <FormControl
            v-model="filters.priority"
            type="select"
            :label="__('Priority Filter')"
            :options="[
              { label: __('All Priorities'), value: '' },
              { label: __('Urgent'), value: 'Urgent' },
              { label: __('High'), value: 'High' },
              { label: __('Medium'), value: 'Medium' },
              { label: __('Low'), value: 'Low' },
            ]"
          />
          <div class="flex items-end">
            <Button
              variant="solid"
              class="w-full"
              :label="__('Run Report')"
              :loading="reportResource.loading"
              @click="runReport"
            >
              <template #prefix>
                <LucideBarChart2 class="size-4" />
              </template>
            </Button>
          </div>
        </div>

        <!-- Report Results Section -->
        <div v-if="reportResource.loading" class="flex justify-center py-10">
          <LoadingIndicator class="size-6 text-ink-gray-6" />
        </div>

        <div
          v-else-if="!reportData?.breakdown?.length && !reportData?.rows?.length"
          class="text-center py-10 text-sm text-ink-gray-5"
        >
          {{ __("Click 'Run Report' to compute SLA metrics and ticket breakdowns.") }}
        </div>

        <div v-else class="space-y-4">
          <!-- Summary Metric Cards -->
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div class="bg-surface-gray-1 border border-outline-gray-1 rounded-md p-3 text-center">
              <div class="text-xs text-ink-gray-6">{{ __('Total Tickets') }}</div>
              <div class="text-2xl font-bold text-ink-gray-9 mt-1">
                {{ summaryMetrics.total_tickets }}
              </div>
            </div>
            <div class="bg-surface-gray-1 border border-outline-gray-1 rounded-md p-3 text-center">
              <div class="text-xs text-ink-gray-6">{{ __('Active Backlog') }}</div>
              <div class="text-2xl font-bold text-ink-gray-9 mt-1">
                {{ summaryMetrics.open_tickets }}
              </div>
            </div>
            <div class="bg-surface-gray-1 border border-outline-gray-1 rounded-md p-3 text-center">
              <div class="text-xs text-ink-gray-6">{{ __('Resolved Tickets') }}</div>
              <div class="text-2xl font-bold text-ink-gray-9 mt-1">
                {{ summaryMetrics.resolved_tickets }}
              </div>
            </div>
            <div class="bg-surface-gray-1 border border-outline-gray-1 rounded-md p-3 text-center">
              <div class="text-xs text-ink-gray-6">{{ __('Overall SLA %') }}</div>
              <div class="text-2xl font-bold text-ink-gray-9 mt-1">
                {{ summaryMetrics.overall_sla_adherence }}%
              </div>
            </div>
          </div>

          <!-- Action bar with Export Formats & Digest -->
          <div class="flex flex-wrap items-center justify-between gap-2 border-t border-b border-outline-gray-1 py-2">
            <div class="text-xs text-ink-gray-6">
              {{ __("Export or Dispatch Analytics:") }}
            </div>
            <div class="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                :label="__('CSV')"
                :loading="isExportingCsv"
                @click="exportCSV"
              >
                <template #prefix>
                  <LucideDownload class="size-3.5 text-ink-gray-6" />
                </template>
              </Button>
              <Button
                variant="outline"
                size="sm"
                :label="__('JSON')"
                :loading="isExportingJson"
                @click="exportJSON"
              >
                <template #prefix>
                  <LucideFileText class="size-3.5 text-ink-gray-6" />
                </template>
              </Button>
              <Button
                variant="outline"
                size="sm"
                :label="__('Print / PDF')"
                :loading="isExportingHtml"
                @click="exportHTML"
              >
                <template #prefix>
                  <LucidePrinter class="size-3.5 text-ink-gray-6" />
                </template>
              </Button>
              <Button
                variant="outline"
                size="sm"
                :label="__('Email Digest')"
                :loading="isSendingDigest"
                @click="emailDigest"
              >
                <template #prefix>
                  <LucideMail class="size-3.5 text-ink-gray-6" />
                </template>
              </Button>
            </div>
          </div>

          <!-- Report Breakdown Table -->
          <div class="border border-outline-gray-2 rounded-lg overflow-hidden">
            <div
              class="grid grid-cols-12 bg-surface-gray-2 text-xs font-semibold text-ink-gray-7 px-3 py-2 border-b border-outline-gray-2"
            >
              <div class="col-span-4">{{ __('Dimension') }}</div>
              <div class="col-span-2 text-center">{{ __('Total') }}</div>
              <div class="col-span-2 text-center">{{ __('Open') }}</div>
              <div class="col-span-2 text-center">{{ __('Resolved') }}</div>
              <div class="col-span-2 text-right">{{ __('SLA %') }}</div>
            </div>
            <div class="max-h-60 overflow-y-auto divide-y divide-outline-gray-1">
              <div
                v-for="row in tableRows"
                :key="row.group"
                class="grid grid-cols-12 items-center text-xs px-3 py-2.5 hover:bg-surface-gray-1 transition-colors"
              >
                <div class="col-span-4 font-medium text-ink-gray-9 truncate">
                  {{ row.group || __("Unassigned") }}
                </div>
                <div class="col-span-2 text-center text-ink-gray-9 font-semibold">
                  {{ row.count }}
                </div>
                <div class="col-span-2 text-center text-ink-gray-8">
                  {{ row.open }}
                </div>
                <div class="col-span-2 text-center text-ink-gray-7">
                  {{ row.resolved }}
                </div>
                <div class="col-span-2 text-right">
                  <span
                    class="font-semibold px-2 py-0.5 rounded text-xs"
                    :class="
                      row.sla_compliance_rate >= 90
                        ? 'bg-surface-gray-2 text-ink-gray-9'
                        : 'bg-surface-gray-3 text-ink-gray-8'
                    "
                  >
                    {{ row.sla_compliance_rate?.toFixed(0) }}%
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>
    <template #actions>
      <div class="flex justify-end">
        <Button
          variant="subtle"
          :label="__('Close')"
          @click="isOpen = false"
        />
      </div>
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { __ } from "@/translation";
import {
  Button,
  Dialog,
  FormControl,
  LoadingIndicator,
  createResource,
  toast,
} from "frappe-ui";
import { computed, reactive, ref } from "vue";
import LucideBarChart2 from "~icons/lucide/bar-chart-2";
import LucideDownload from "~icons/lucide/download";
import LucideFileText from "~icons/lucide/file-text";
import LucideMail from "~icons/lucide/mail";
import LucidePrinter from "~icons/lucide/printer";

const props = defineProps<{
  modelValue: boolean;
}>();

const emit = defineEmits<{
  (e: "update:modelValue", value: boolean): void;
}>();

const isOpen = computed({
  get: () => props.modelValue,
  set: (val) => emit("update:modelValue", val),
});

const filters = reactive({
  group_by: "customer",
  status: "",
  priority: "",
});

const isExportingCsv = ref(false);
const isExportingJson = ref(false);
const isExportingHtml = ref(false);
const isSendingDigest = ref(false);

const reportResource = createResource({
  url: "helpdesk.api.custom_reports.generate_ticket_report",
  auto: false,
});

const reportData = computed(() => reportResource.data);

const summaryMetrics = computed(() => {
  const sum = reportData.value?.summary || {};
  return {
    total_tickets: sum.total_tickets || reportData.value?.total_tickets || 0,
    open_tickets: sum.open_tickets || 0,
    resolved_tickets: sum.resolved_tickets || 0,
    overall_sla_adherence: sum.overall_sla_adherence !== undefined ? sum.overall_sla_adherence : 100,
  };
});

const tableRows = computed(() => {
  if (reportData.value?.breakdown?.length) {
    return reportData.value.breakdown;
  }
  if (reportData.value?.rows?.length) {
    return reportData.value.rows.map((r: any) => ({
      group: r.group_label,
      count: r.total_tickets,
      open: r.open_tickets,
      resolved: r.resolved_tickets,
      breached: r.sla_breached,
      sla_compliance_rate: r.sla_adherence_percent,
    }));
  }
  return [];
});

function runReport() {
  reportResource.submit({
    group_by: filters.group_by,
    status: filters.status || null,
    priority: filters.priority || null,
  });
}

function triggerDownload(content: string, filename: string, mimeType: string) {
  const blob = new Blob([content], { type: mimeType });
  const link = document.createElement("a");
  const url = URL.createObjectURL(blob);
  link.setAttribute("href", url);
  link.setAttribute("download", filename);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

const csvResource = createResource({
  url: "helpdesk.api.custom_reports.export_report_csv",
  auto: false,
});

async function exportCSV() {
  isExportingCsv.value = true;
  try {
    const res = await csvResource.submit({
      group_by: filters.group_by,
      status: filters.status || null,
      priority: filters.priority || null,
    });
    if (res?.csv_content) {
      triggerDownload(
        res.csv_content,
        res.filename || `helpdesk_${filters.group_by}_report.csv`,
        "text/csv;charset=utf-8;"
      );
      toast.success(__("CSV report downloaded successfully"));
    }
  } catch (error: any) {
    toast.error(error.message || __("Failed to export CSV"));
  } finally {
    isExportingCsv.value = false;
  }
}

const jsonResource = createResource({
  url: "helpdesk.api.custom_reports.export_report_json",
  auto: false,
});

async function exportJSON() {
  isExportingJson.value = true;
  try {
    const res = await jsonResource.submit({
      group_by: filters.group_by,
      status: filters.status || null,
      priority: filters.priority || null,
    });
    if (res?.json_content) {
      triggerDownload(
        res.json_content,
        res.filename || `helpdesk_${filters.group_by}_report.json`,
        "application/json;charset=utf-8;"
      );
      toast.success(__("JSON report downloaded successfully"));
    }
  } catch (error: any) {
    toast.error(error.message || __("Failed to export JSON"));
  } finally {
    isExportingJson.value = false;
  }
}

const htmlResource = createResource({
  url: "helpdesk.api.custom_reports.export_report_html",
  auto: false,
});

async function exportHTML() {
  isExportingHtml.value = true;
  try {
    const res = await htmlResource.submit({
      group_by: filters.group_by,
      status: filters.status || null,
      priority: filters.priority || null,
    });
    if (res?.html_content) {
      const printWindow = window.open("", "_blank");
      if (printWindow) {
        printWindow.document.write(res.html_content);
        printWindow.document.close();
      } else {
        triggerDownload(
          res.html_content,
          res.filename || `helpdesk_${filters.group_by}_report.html`,
          "text/html;charset=utf-8;"
        );
      }
      toast.success(__("Executive report opened for printing"));
    }
  } catch (error: any) {
    toast.error(error.message || __("Failed to open report"));
  } finally {
    isExportingHtml.value = false;
  }
}

const digestResource = createResource({
  url: "helpdesk.api.custom_reports.send_scheduled_analytics_digest",
  auto: false,
});

async function emailDigest() {
  isSendingDigest.value = true;
  try {
    await digestResource.submit();
    toast.success(__("Support analytics digest dispatched to your inbox"));
  } catch (error: any) {
    toast.error(error.message || __("Failed to send email digest"));
  } finally {
    isSendingDigest.value = false;
  }
}
</script>
