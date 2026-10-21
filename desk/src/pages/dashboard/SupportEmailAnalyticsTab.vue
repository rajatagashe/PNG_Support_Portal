<template>
  <div class="space-y-4">
    <!-- Top Controls Toolbar -->
    <div class="flex flex-wrap items-center justify-between gap-3 bg-surface-white border border-outline-gray-2 rounded-lg p-3">
      <!-- View Mode Tabs: Daily / Weekly / Monthly -->
      <div class="flex items-center gap-1 bg-surface-gray-1 p-1 rounded-md border border-outline-gray-1">
        <Button
          v-for="mode in ['daily', 'weekly', 'monthly']"
          :key="mode"
          :variant="viewMode === mode ? 'solid' : 'ghost'"
          size="sm"
          class="capitalize text-xs"
          :label="__(mode)"
          @click="changeViewMode(mode)"
        />
      </div>

      <!-- Action Buttons -->
      <div class="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          :label="__('Sync Inbound Emails')"
          :loading="isSyncing"
          @click="triggerEmailSync"
        >
          <template #prefix>
            <LucideRefreshCw class="size-3.5 text-ink-gray-6" :class="{ 'animate-spin': isSyncing }" />
          </template>
        </Button>
        <Button
          variant="outline"
          size="sm"
          :label="__('Export Excel (.xlsx)')"
          :loading="isExportingXlsx"
          @click="exportExcel"
        >
          <template #prefix>
            <LucideFileSpreadsheet class="size-3.5 text-ink-gray-6" />
          </template>
        </Button>
        <Button
          variant="outline"
          size="sm"
          :label="__('Export CSV')"
          :loading="isExportingCsv"
          @click="exportCSV"
        >
          <template #prefix>
            <LucideDownload class="size-3.5 text-ink-gray-6" />
          </template>
        </Button>
      </div>
    </div>

    <!-- Filter Bar -->
    <div class="grid grid-cols-1 sm:grid-cols-4 gap-3 bg-surface-gray-1 border border-outline-gray-1 p-3 rounded-lg text-xs">
      <Link
        class="w-full"
        doctype="HD Customer"
        variant="outline"
        :placeholder="__('Filter by CGD Organization')"
        :label="__('CGD Entity')"
        v-model="filters.cgd"
        @change="reloadAnalytics"
      />
      <Link
        class="w-full"
        doctype="HD Team"
        variant="outline"
        :placeholder="__('Filter by Team')"
        :label="__('Support Team')"
        v-model="filters.team"
        @change="reloadAnalytics"
      />
      <FormControl
        v-model="filters.status"
        type="select"
        :label="__('Status')"
        :options="[
          { label: __('All Statuses'), value: '' },
          { label: __('Open'), value: 'Open' },
          { label: __('Pending'), value: 'Pending' },
          { label: __('Replied'), value: 'Replied' },
          { label: __('Resolved'), value: 'Resolved' },
          { label: __('Closed'), value: 'Closed' },
        ]"
        @change="reloadAnalytics"
      />
      <div class="flex items-end">
        <TextInput
          v-model="filters.search"
          class="w-full"
          :placeholder="__('Search sender or subject...')"
          variant="outline"
          @input="debouncedSearch"
        />
      </div>
    </div>

    <!-- Period Comparison Subtitle -->
    <div class="flex items-center justify-between text-xs text-ink-gray-6 px-1">
      <div>
        <span class="font-medium text-ink-gray-9">{{ analyticsData?.period_label }}</span>
        <span class="ml-2 italic text-ink-gray-5">({{ analyticsData?.comparison_label }})</span>
      </div>
      <div v-if="lastSyncedAt" class="text-ink-gray-5">
        {{ __('Last Synced:') }} {{ lastSyncedAt }}
      </div>
    </div>

    <!-- Summary KPI Cards -->
    <div class="grid grid-cols-2 md:grid-cols-5 gap-3">
      <!-- Total Received -->
      <div class="bg-surface-white border border-outline-gray-2 rounded-lg p-3 shadow-sm">
        <span class="text-xs text-ink-gray-6">{{ __('Total Emails Received') }}</span>
        <div class="flex items-baseline justify-between mt-1">
          <span class="text-2xl font-bold text-ink-gray-9">
            {{ summary.total_received?.value || 0 }}
          </span>
          <span
            v-if="summary.total_received?.comparison"
            class="text-xs font-semibold px-1.5 py-0.5 rounded"
            :class="
              summary.total_received.comparison.diff >= 0
                ? 'bg-surface-gray-2 text-ink-gray-9'
                : 'bg-surface-gray-3 text-ink-gray-7'
            "
          >
            {{ summary.total_received.comparison.diff >= 0 ? '+' : '' }}{{ summary.total_received.comparison.pct }}%
          </span>
        </div>
      </div>

      <!-- New / Unassigned -->
      <div class="bg-surface-white border border-outline-gray-2 rounded-lg p-3 shadow-sm">
        <span class="text-xs text-ink-gray-6">{{ __('Unassigned Emails') }}</span>
        <div class="flex items-baseline justify-between mt-1">
          <span class="text-2xl font-bold text-ink-gray-9">
            {{ summary.unassigned?.value || 0 }}
          </span>
          <span
            v-if="summary.unassigned?.comparison"
            class="text-xs font-semibold px-1.5 py-0.5 rounded bg-surface-gray-2 text-ink-gray-8"
          >
            {{ summary.unassigned.comparison.diff >= 0 ? '+' : '' }}{{ summary.unassigned.comparison.diff }}
          </span>
        </div>
      </div>

      <!-- Assigned -->
      <div class="bg-surface-white border border-outline-gray-2 rounded-lg p-3 shadow-sm">
        <span class="text-xs text-ink-gray-6">{{ __('Assigned Emails') }}</span>
        <div class="flex items-baseline justify-between mt-1">
          <span class="text-2xl font-bold text-ink-gray-9">
            {{ summary.assigned?.value || 0 }}
          </span>
          <span
            v-if="summary.assigned?.comparison"
            class="text-xs font-semibold px-1.5 py-0.5 rounded bg-surface-gray-2 text-ink-gray-8"
          >
            {{ summary.assigned.comparison.diff >= 0 ? '+' : '' }}{{ summary.assigned.comparison.diff }}
          </span>
        </div>
      </div>

      <!-- In Progress -->
      <div class="bg-surface-white border border-outline-gray-2 rounded-lg p-3 shadow-sm">
        <span class="text-xs text-ink-gray-6">{{ __('Currently In Progress') }}</span>
        <div class="flex items-baseline justify-between mt-1">
          <span class="text-2xl font-bold text-ink-gray-9">
            {{ summary.in_progress?.value || 0 }}
          </span>
          <span
            v-if="summary.in_progress?.comparison"
            class="text-xs font-semibold px-1.5 py-0.5 rounded bg-surface-gray-2 text-ink-gray-8"
          >
            {{ summary.in_progress.comparison.diff >= 0 ? '+' : '' }}{{ summary.in_progress.comparison.diff }}
          </span>
        </div>
      </div>

      <!-- Resolved -->
      <div class="bg-surface-white border border-outline-gray-2 rounded-lg p-3 shadow-sm">
        <span class="text-xs text-ink-gray-6">{{ __('Resolved / Closed') }}</span>
        <div class="flex items-baseline justify-between mt-1">
          <span class="text-2xl font-bold text-ink-gray-9">
            {{ summary.resolved?.value || 0 }}
          </span>
          <span
            v-if="summary.resolved?.comparison"
            class="text-xs font-semibold px-1.5 py-0.5 rounded bg-surface-gray-2 text-ink-gray-8"
          >
            {{ summary.resolved.comparison.diff >= 0 ? '+' : '' }}{{ summary.resolved.comparison.diff }}
          </span>
        </div>
      </div>
    </div>

    <!-- CGD & Team Distribution Row -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <!-- CGD Entity Distribution -->
      <div class="bg-surface-white border border-outline-gray-2 rounded-lg p-3 shadow-sm">
        <div class="flex items-center gap-2 mb-2 font-semibold text-xs text-ink-gray-8">
          <LucideBuilding2 class="size-4" />
          <span>{{ __('Emails by CGD Organization') }}</span>
        </div>
        <div v-if="!analyticsData?.cgd_distribution?.length" class="text-xs text-ink-gray-5 py-3 text-center">
          {{ __('No CGD emails recorded in this period.') }}
        </div>
        <div v-else class="space-y-1.5 max-h-36 overflow-y-auto pr-1">
          <div
            v-for="item in analyticsData.cgd_distribution"
            :key="item.cgd_id"
            class="flex items-center justify-between text-xs p-1.5 rounded hover:bg-surface-gray-1"
          >
            <div class="flex items-center gap-1.5 truncate">
              <LucideCrown v-if="item.is_vip" class="size-3 text-ink-gray-9 shrink-0" />
              <span class="truncate font-medium text-ink-gray-9">{{ item.cgd_name }}</span>
            </div>
            <div class="flex items-center gap-2 shrink-0">
              <span class="font-bold text-ink-gray-9">{{ item.count }}</span>
              <span class="text-[11px] text-ink-gray-5">({{ item.open_count }} open)</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Team Distribution -->
      <div class="bg-surface-white border border-outline-gray-2 rounded-lg p-3 shadow-sm">
        <div class="flex items-center gap-2 mb-2 font-semibold text-xs text-ink-gray-8">
          <LucideUsers class="size-4" />
          <span>{{ __('Emails by Assigned Team') }}</span>
        </div>
        <div v-if="!analyticsData?.team_distribution?.length" class="text-xs text-ink-gray-5 py-3 text-center">
          {{ __('No team assignments in this period.') }}
        </div>
        <div v-else class="space-y-1.5 max-h-36 overflow-y-auto pr-1">
          <div
            v-for="item in analyticsData.team_distribution"
            :key="item.team_name"
            class="flex items-center justify-between text-xs p-1.5 rounded hover:bg-surface-gray-1"
          >
            <span class="truncate font-medium text-ink-gray-9">{{ item.team_name }}</span>
            <div class="flex items-center gap-2 shrink-0">
              <span class="font-bold text-ink-gray-9">{{ item.count }}</span>
              <span class="text-[11px] text-ink-gray-5">({{ item.open_count }} open)</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Inbound Support Emails Table -->
    <div class="bg-surface-white border border-outline-gray-2 rounded-lg shadow-sm overflow-hidden">
      <div class="p-3 border-b border-outline-gray-2 flex items-center justify-between">
        <div class="flex items-center gap-2">
          <LucideMail class="size-4 text-ink-gray-7" />
          <span class="font-semibold text-sm text-ink-gray-9">
            {{ __('Inbound Support Emails & Tickets') }}
          </span>
          <span class="text-xs text-ink-gray-5">({{ emailsData.total_count || 0 }} total)</span>
        </div>
        <div class="flex items-center gap-2 text-xs">
          <Button
            variant="ghost"
            size="sm"
            :label="__('Previous')"
            :disabled="currentPage <= 1"
            @click="prevPage"
          />
          <span class="text-ink-gray-6">{{ __('Page') }} {{ currentPage }}</span>
          <Button
            variant="ghost"
            size="sm"
            :label="__('Next')"
            :disabled="!emailsData.has_more"
            @click="nextPage"
          />
        </div>
      </div>

      <!-- Loading Indicator -->
      <div v-if="emailsResource.loading" class="flex justify-center py-10">
        <LoadingIndicator class="size-6 text-ink-gray-6" />
      </div>

      <!-- Empty -->
      <div
        v-else-if="!emailsData.emails?.length"
        class="text-center py-10 text-sm text-ink-gray-5"
      >
        {{ __('No support emails found matching the current filters.') }}
      </div>

      <!-- Table Rows -->
      <div v-else class="overflow-x-auto">
        <table class="w-full text-xs text-left">
          <thead class="bg-surface-gray-1 text-ink-gray-7 uppercase font-semibold border-b border-outline-gray-2">
            <tr>
              <th class="p-2.5">{{ __('Ticket / Subject') }}</th>
              <th class="p-2.5">{{ __('Sender') }}</th>
              <th class="p-2.5">{{ __('CGD Organization') }}</th>
              <th class="p-2.5">{{ __('Assigned Team') }}</th>
              <th class="p-2.5">{{ __('Assignee') }}</th>
              <th class="p-2.5">{{ __('Received Time') }}</th>
              <th class="p-2.5 text-center">{{ __('Status') }}</th>
              <th class="p-2.5 text-right">{{ __('Action') }}</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-outline-gray-1">
            <tr
              v-for="em in emailsData.emails"
              :key="em.ticket_id"
              class="hover:bg-surface-gray-1 transition-colors"
            >
              <td class="p-2.5 max-w-xs">
                <router-link
                  :to="`/tickets/${em.ticket_id}`"
                  class="font-medium text-ink-gray-9 hover:underline truncate block"
                >
                  {{ em.subject }}
                </router-link>
                <span class="text-[11px] text-ink-gray-5 truncate block font-mono">
                  #{{ em.ticket_id }} &bull; {{ em.original_message_id }}
                </span>
              </td>
              <td class="p-2.5 whitespace-nowrap text-ink-gray-8">
                <div class="font-medium text-ink-gray-9">{{ em.sender_name }}</div>
                <div class="text-[11px] text-ink-gray-5">{{ em.sender_email }}</div>
              </td>
              <td class="p-2.5 whitespace-nowrap">
                <div class="flex items-center gap-1.5">
                  <LucideCrown v-if="em.is_vip" class="size-3 text-ink-gray-9" />
                  <span class="font-medium text-ink-gray-9">{{ em.cgd_name }}</span>
                </div>
              </td>
              <td class="p-2.5 whitespace-nowrap text-ink-gray-8">
                {{ em.team_name }}
              </td>
              <td class="p-2.5 whitespace-nowrap text-ink-gray-8">
                {{ em.assignee_label }}
              </td>
              <td class="p-2.5 whitespace-nowrap text-ink-gray-6">
                <div>{{ em.received_date }}</div>
                <div class="text-[11px]">{{ em.received_time }}</div>
              </td>
              <td class="p-2.5 text-center whitespace-nowrap">
                <span
                  class="px-2 py-0.5 rounded text-[11px] font-semibold"
                  :class="
                    em.status === 'Resolved' || em.status === 'Closed'
                      ? 'bg-surface-gray-2 text-ink-gray-9'
                      : 'bg-surface-gray-3 text-ink-gray-8'
                  "
                >
                  {{ em.status }}
                </span>
              </td>
              <td class="p-2.5 text-right whitespace-nowrap">
                <Button
                  variant="outline"
                  size="sm"
                  :label="__('Reassign')"
                  @click="openReassignModal(em)"
                />
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Quick Reassign Modal -->
    <QuickReassignModal
      v-if="selectedTicketForReassign"
      v-model="showReassignModal"
      :ticket-id="selectedTicketForReassign.ticket_id"
      :subject="selectedTicketForReassign.subject"
      :current-team="selectedTicketForReassign.team_id"
      :current-agent="selectedTicketForReassign.assignees?.[0]"
      :current-status="selectedTicketForReassign.status"
      @assigned="handleAssignmentComplete"
    />
  </div>
</template>

<script setup lang="ts">
import { __ } from "@/translation";
import { Link } from "@framework/ui";
import {
  Button,
  FormControl,
  LoadingIndicator,
  TextInput,
  createResource,
  toast,
} from "frappe-ui";
import { computed, onMounted, reactive, ref } from "vue";
import LucideBuilding2 from "~icons/lucide/building-2";
import LucideCrown from "~icons/lucide/crown";
import LucideDownload from "~icons/lucide/download";
import LucideFileSpreadsheet from "~icons/lucide/file-spreadsheet";
import LucideMail from "~icons/lucide/mail";
import LucideRefreshCw from "~icons/lucide/refresh-cw";
import LucideUsers from "~icons/lucide/users";
import QuickReassignModal from "@/components/ticket-agent/QuickReassignModal.vue";

const viewMode = ref<"daily" | "weekly" | "monthly">("daily");
const currentPage = ref(1);
const isSyncing = ref(false);
const isExportingXlsx = ref(false);
const isExportingCsv = ref(false);
const lastSyncedAt = ref("");

const filters = reactive({
  cgd: "",
  team: "",
  status: "",
  search: "",
});

const showReassignModal = ref(false);
const selectedTicketForReassign = ref<any>(null);

function openReassignModal(ticket: any) {
  selectedTicketForReassign.value = ticket;
  showReassignModal.value = true;
}

function handleAssignmentComplete() {
  emailsResource.reload();
  analyticsResource.reload();
}

const analyticsResource = createResource({
  url: "helpdesk.api.email_management.get_email_dashboard_analytics",
  params: {
    view_mode: viewMode.value,
    cgd: filters.cgd || null,
    team: filters.team || null,
    status: filters.status || null,
  },
  auto: true,
});

const analyticsData = computed(() => analyticsResource.data || {});
const summary = computed(() => analyticsData.value?.summary || {});

const emailsResource = createResource({
  url: "helpdesk.api.email_management.get_support_emails",
  params: {
    page: currentPage.value,
    page_length: 15,
    cgd: filters.cgd || null,
    team: filters.team || null,
    status: filters.status || null,
    search_text: filters.search || null,
  },
  auto: true,
});

const emailsData = computed(() => emailsResource.data || { emails: [], total_count: 0 });

function changeViewMode(mode: string) {
  viewMode.value = mode as any;
  reloadAnalytics();
}

function reloadAnalytics() {
  currentPage.value = 1;
  analyticsResource.fetch({
    view_mode: viewMode.value,
    cgd: filters.cgd || null,
    team: filters.team || null,
    status: filters.status || null,
  });
  emailsResource.fetch({
    page: 1,
    page_length: 15,
    cgd: filters.cgd || null,
    team: filters.team || null,
    status: filters.status || null,
    search_text: filters.search || null,
  });
}

let searchTimeout: any = null;
function debouncedSearch() {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => {
    emailsResource.fetch({
      page: 1,
      page_length: 15,
      cgd: filters.cgd || null,
      team: filters.team || null,
      status: filters.status || null,
      search_text: filters.search || null,
    });
  }, 350);
}

function nextPage() {
  if (emailsData.value.has_more) {
    currentPage.value++;
    emailsResource.fetch({
      page: currentPage.value,
      page_length: 15,
      cgd: filters.cgd || null,
      team: filters.team || null,
      status: filters.status || null,
      search_text: filters.search || null,
    });
  }
}

function prevPage() {
  if (currentPage.value > 1) {
    currentPage.value--;
    emailsResource.fetch({
      page: currentPage.value,
      page_length: 15,
      cgd: filters.cgd || null,
      team: filters.team || null,
      status: filters.status || null,
      search_text: filters.search || null,
    });
  }
}

const syncResource = createResource({
  url: "helpdesk.api.email_management.sync_support_emails",
  auto: false,
});

async function triggerEmailSync() {
  isSyncing.value = true;
  try {
    const res = await syncResource.submit();
    if (res?.success) {
      toast.success(
        __("Email sync complete. Retrieved {0} new emails.", [res.total_new_emails])
      );
      lastSyncedAt.value = new Date().toLocaleTimeString();
      reloadAnalytics();
    } else {
      toast.error(__("Email sync completed with errors. Check system logs."));
    }
  } catch (err: any) {
    toast.error(err.message || __("Failed to sync emails."));
  } finally {
    isSyncing.value = false;
  }
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

const xlsxResource = createResource({
  url: "helpdesk.api.email_management.export_email_report_xlsx",
  auto: false,
});

async function exportExcel() {
  isExportingXlsx.value = true;
  try {
    const res = await xlsxResource.submit({
      cgd: filters.cgd || null,
      team: filters.team || null,
      status: filters.status || null,
    });
    if (res?.base64_content) {
      // Decode base64 to binary byte array for clean xlsx download
      const binaryString = atob(res.base64_content);
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
      link.setAttribute("download", res.filename || "Support_Email_Report.xlsx");
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

      toast.success(__("Multi-sheet Excel report exported successfully."));
    }
  } catch (error: any) {
    toast.error(error.message || __("Failed to export Excel report."));
  } finally {
    isExportingXlsx.value = false;
  }
}

const csvExportResource = createResource({
  url: "helpdesk.api.email_management.export_email_report_csv",
  auto: false,
});

async function exportCSV() {
  isExportingCsv.value = true;
  try {
    const res = await csvExportResource.submit({
      cgd: filters.cgd || null,
      team: filters.team || null,
      status: filters.status || null,
    });
    if (res?.csv_content) {
      triggerDownload(
        res.csv_content,
        res.filename || "Support_Email_Report.csv",
        "text/csv;charset=utf-8;"
      );
      toast.success(__("CSV report exported successfully."));
    }
  } catch (error: any) {
    toast.error(error.message || __("Failed to export CSV report."));
  } finally {
    isExportingCsv.value = false;
  }
}
</script>
