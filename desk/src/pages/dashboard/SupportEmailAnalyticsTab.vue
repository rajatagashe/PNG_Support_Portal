<template>
  <div class="space-y-4">
    <!-- Top Controls Toolbar -->
    <div class="flex flex-wrap items-center justify-between gap-3 bg-surface-white border border-outline-gray-2 rounded-xl p-3.5 shadow-xs">
      <!-- View Mode Tabs: Daily / Weekly / Monthly -->
      <div class="flex items-center gap-1 bg-surface-gray-2 p-1 rounded-lg border border-outline-gray-2">
        <button
          v-for="mode in ['daily', 'weekly', 'monthly']"
          :key="mode"
          type="button"
          class="px-3 py-1 text-xs font-medium rounded-md capitalize transition-all focus:outline-none"
          :class="
            viewMode === mode
              ? 'bg-surface-white text-primary shadow-xs font-semibold'
              : 'text-ink-gray-6 hover:text-ink-gray-9'
          "
          @click="changeViewMode(mode)"
        >
          {{ __(mode) }}
        </button>
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
            <LucideRefreshCw class="size-3.5 text-primary" :class="{ 'animate-spin': isSyncing }" />
          </template>
        </Button>
        <Button
          variant="outline"
          size="sm"
          :label="__('Export Excel')"
          :loading="isExportingXlsx"
          @click="exportExcel"
        >
          <template #prefix>
            <LucideFileSpreadsheet class="size-3.5 text-emerald-600" />
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
    <div class="grid grid-cols-1 sm:grid-cols-5 gap-3 bg-surface-white border border-outline-gray-2 p-3.5 rounded-xl shadow-xs text-xs">
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
      <FormControl
        v-model="filters.readState"
        type="select"
        :label="__('Read State')"
        :options="[
          { label: __('All Emails'), value: '' },
          { label: __('Unread'), value: 'unread' },
          { label: __('Read'), value: 'read' },
        ]"
        @change="reloadAnalytics"
      />
      <div class="flex items-end">
        <TextInput
          v-model="filters.search"
          class="w-full"
          :aria-label="__('Search support emails')"
          :placeholder="__('Search sender, subject or message...')"
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
      <div class="bg-surface-white border border-outline-gray-2 border-t-3 border-t-blue-600 rounded-xl p-3.5 shadow-xs transition-all hover:shadow-sm">
        <span class="text-xs font-medium text-ink-gray-6">{{ __('Total Emails Received') }}</span>
        <div class="flex items-baseline justify-between mt-1">
          <span class="text-2xl font-bold text-ink-gray-9">
            {{ summary.total_received?.value || 0 }}
          </span>
          <span
            v-if="summary.total_received?.comparison"
            class="text-[11px] font-semibold px-1.5 py-0.5 rounded-full"
            :class="
              summary.total_received.comparison.diff >= 0
                ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                : 'bg-rose-50 text-rose-700 border border-rose-200'
            "
          >
            {{ summary.total_received.comparison.diff >= 0 ? '+' : '' }}{{ summary.total_received.comparison.pct }}%
          </span>
        </div>
      </div>

      <!-- New / Unassigned -->
      <div class="bg-surface-white border border-outline-gray-2 border-t-3 border-t-sky-500 rounded-xl p-3.5 shadow-xs transition-all hover:shadow-sm">
        <span class="text-xs font-medium text-ink-gray-6">{{ __('Unassigned Emails') }}</span>
        <div class="flex items-baseline justify-between mt-1">
          <span class="text-2xl font-bold text-ink-gray-9">
            {{ summary.unassigned?.value || 0 }}
          </span>
          <span
            v-if="summary.unassigned?.comparison"
            class="text-[11px] font-semibold px-1.5 py-0.5 rounded-full bg-surface-gray-2 text-ink-gray-7 border border-outline-gray-2"
          >
            {{ summary.unassigned.comparison.diff >= 0 ? '+' : '' }}{{ summary.unassigned.comparison.diff }}
          </span>
        </div>
      </div>

      <!-- Assigned -->
      <div class="bg-surface-white border border-outline-gray-2 border-t-3 border-t-indigo-500 rounded-xl p-3.5 shadow-xs transition-all hover:shadow-sm">
        <span class="text-xs font-medium text-ink-gray-6">{{ __('Assigned Emails') }}</span>
        <div class="flex items-baseline justify-between mt-1">
          <span class="text-2xl font-bold text-ink-gray-9">
            {{ summary.assigned?.value || 0 }}
          </span>
          <span
            v-if="summary.assigned?.comparison"
            class="text-[11px] font-semibold px-1.5 py-0.5 rounded-full bg-surface-gray-2 text-ink-gray-7 border border-outline-gray-2"
          >
            {{ summary.assigned.comparison.diff >= 0 ? '+' : '' }}{{ summary.assigned.comparison.diff }}
          </span>
        </div>
      </div>

      <!-- In Progress -->
      <div class="bg-surface-white border border-outline-gray-2 border-t-3 border-t-amber-500 rounded-xl p-3.5 shadow-xs transition-all hover:shadow-sm">
        <span class="text-xs font-medium text-ink-gray-6">{{ __('Currently In Progress') }}</span>
        <div class="flex items-baseline justify-between mt-1">
          <span class="text-2xl font-bold text-ink-gray-9">
            {{ summary.in_progress?.value || 0 }}
          </span>
          <span
            v-if="summary.in_progress?.comparison"
            class="text-[11px] font-semibold px-1.5 py-0.5 rounded-full bg-surface-gray-2 text-ink-gray-7 border border-outline-gray-2"
          >
            {{ summary.in_progress.comparison.diff >= 0 ? '+' : '' }}{{ summary.in_progress.comparison.diff }}
          </span>
        </div>
      </div>

      <!-- Resolved -->
      <div class="bg-surface-white border border-outline-gray-2 border-t-3 border-t-emerald-500 rounded-xl p-3.5 shadow-xs transition-all hover:shadow-sm">
        <span class="text-xs font-medium text-ink-gray-6">{{ __('Resolved / Closed') }}</span>
        <div class="flex items-baseline justify-between mt-1">
          <span class="text-2xl font-bold text-ink-gray-9">
            {{ summary.resolved?.value || 0 }}
          </span>
          <span
            v-if="summary.resolved?.comparison"
            class="text-[11px] font-semibold px-1.5 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200"
          >
            {{ summary.resolved.comparison.diff >= 0 ? '+' : '' }}{{ summary.resolved.comparison.diff }}
          </span>
        </div>
      </div>
    </div>

    <!-- CGD & Team Distribution Row -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <!-- CGD Entity Distribution -->
      <div class="bg-surface-white border border-outline-gray-2 rounded-xl p-4 shadow-xs">
        <div class="flex items-center justify-between pb-2.5 mb-3 border-b border-outline-gray-1">
          <div class="flex items-center gap-2 font-semibold text-xs text-ink-gray-9">
            <LucideBuilding2 class="size-4 text-primary" />
            <span>{{ __('Emails by CGD Organization') }}</span>
          </div>
          <span class="text-[11px] text-ink-gray-5">{{ analyticsData?.cgd_distribution?.length || 0 }} {{ __('entities') }}</span>
        </div>
        <div v-if="!analyticsData?.cgd_distribution?.length" class="text-xs text-ink-gray-5 py-6 text-center">
          {{ __('No CGD emails recorded in this period.') }}
        </div>
        <div v-else class="space-y-2.5 max-h-48 overflow-y-auto pr-1">
          <div
            v-for="item in analyticsData.cgd_distribution"
            :key="item.cgd_id"
            class="p-2 rounded-lg bg-surface-gray-1/70 hover:bg-surface-gray-1 transition-colors"
          >
            <div class="flex items-center justify-between text-xs mb-1">
              <div class="flex items-center gap-1.5 truncate">
                <LucideCrown v-if="item.is_vip" class="size-3.5 text-amber-500 shrink-0" />
                <span class="truncate font-semibold text-ink-gray-9">{{ item.cgd_name }}</span>
              </div>
              <div class="flex items-center gap-2 shrink-0">
                <span class="font-bold text-ink-gray-9">{{ item.count }}</span>
                <span class="text-[11px] text-amber-600 font-medium" v-if="item.open_count > 0">({{ item.open_count }} {{ __('open') }})</span>
              </div>
            </div>
            <!-- Progress Bar -->
            <div class="w-full bg-surface-gray-3 rounded-full h-1.5 overflow-hidden">
              <div
                class="bg-primary h-1.5 rounded-full transition-all duration-300"
                :style="{
                  width: `${Math.min(100, (item.count / (summary.total_received?.value || 1)) * 100)}%`
                }"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- Team Distribution -->
      <div class="bg-surface-white border border-outline-gray-2 rounded-xl p-4 shadow-xs">
        <div class="flex items-center justify-between pb-2.5 mb-3 border-b border-outline-gray-1">
          <div class="flex items-center gap-2 font-semibold text-xs text-ink-gray-9">
            <LucideUsers class="size-4 text-indigo-600" />
            <span>{{ __('Emails by Assigned Team') }}</span>
          </div>
          <span class="text-[11px] text-ink-gray-5">{{ analyticsData?.team_distribution?.length || 0 }} {{ __('teams') }}</span>
        </div>
        <div v-if="!analyticsData?.team_distribution?.length" class="text-xs text-ink-gray-5 py-6 text-center">
          {{ __('No team assignments in this period.') }}
        </div>
        <div v-else class="space-y-2.5 max-h-48 overflow-y-auto pr-1">
          <div
            v-for="item in analyticsData.team_distribution"
            :key="item.team_name"
            class="p-2 rounded-lg bg-surface-gray-1/70 hover:bg-surface-gray-1 transition-colors"
          >
            <div class="flex items-center justify-between text-xs mb-1">
              <span class="truncate font-semibold text-ink-gray-9">{{ item.team_name }}</span>
              <div class="flex items-center gap-2 shrink-0">
                <span class="font-bold text-ink-gray-9">{{ item.count }}</span>
                <span class="text-[11px] text-amber-600 font-medium" v-if="item.open_count > 0">({{ item.open_count }} {{ __('open') }})</span>
              </div>
            </div>
            <!-- Progress Bar -->
            <div class="w-full bg-surface-gray-3 rounded-full h-1.5 overflow-hidden">
              <div
                class="bg-indigo-500 h-1.5 rounded-full transition-all duration-300"
                :style="{
                  width: `${Math.min(100, (item.count / (summary.total_received?.value || 1)) * 100)}%`
                }"
              />
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Inbound Support Emails Table -->
    <div class="bg-surface-white border border-outline-gray-2 rounded-xl shadow-xs overflow-hidden">
      <div class="p-3.5 border-b border-outline-gray-2 flex items-center justify-between bg-surface-gray-1/40">
        <div class="flex items-center gap-2.5">
          <div class="flex size-7 items-center justify-center rounded-lg bg-blue-50 text-primary border border-blue-200">
            <LucideMail class="size-3.5" />
          </div>
          <span class="font-semibold text-sm text-ink-gray-9">
            {{ __('Inbound Support Emails & Tickets') }}
          </span>
          <span class="px-2 py-0.5 rounded-full text-xs font-semibold bg-surface-gray-2 text-ink-gray-7 border border-outline-gray-2">
            {{ emailsData.total_count || 0 }} {{ __('total') }}
          </span>
        </div>
        <div class="flex items-center gap-2 text-xs">
          <Button
            variant="outline"
            size="sm"
            :label="__('Previous')"
            :disabled="currentPage <= 1"
            @click="prevPage"
          />
          <span class="text-ink-gray-6 px-1">{{ __('Page') }} {{ currentPage }}</span>
          <Button
            variant="outline"
            size="sm"
            :label="__('Next')"
            :disabled="!emailsData.has_more"
            @click="nextPage"
          />
        </div>
      </div>

      <!-- Loading Indicator -->
      <div v-if="emailsResource.loading" class="flex justify-center py-12">
        <LoadingIndicator class="size-6 text-primary" />
      </div>

      <!-- Empty -->
      <div
        v-else-if="!emailsData.emails?.length"
        class="text-center py-12 text-sm text-ink-gray-5"
      >
        <LucideMail class="size-8 text-ink-gray-4 mx-auto mb-2 opacity-50" />
        {{ __('No support emails found matching the current filters.') }}
      </div>

      <!-- Table Rows -->
      <div v-else class="overflow-x-auto">
        <table class="w-full text-xs text-left">
          <thead class="bg-surface-gray-1 text-ink-gray-7 uppercase tracking-wider font-semibold border-b border-outline-gray-2">
            <tr>
              <th class="p-3">{{ __('Ticket / Subject') }}</th>
              <th class="p-3">{{ __('Sender') }}</th>
              <th class="p-3">{{ __('CGD Organization') }}</th>
              <th class="p-3">{{ __('Assigned Team') }}</th>
              <th class="p-3">{{ __('Assignee') }}</th>
              <th class="p-3">{{ __('Received Time') }}</th>
              <th class="p-3 text-center">{{ __('Status') }}</th>
              <th class="p-3 text-right">{{ __('Action') }}</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-outline-gray-1">
            <tr
              v-for="em in emailsData.emails"
              :key="em.ticket_id"
              class="hover:bg-blue-50/30 transition-colors group"
            >
              <td class="p-3 max-w-xs">
                <div class="flex items-center gap-2 min-w-0">
                  <span
                    v-if="em.is_unread"
                    class="size-2 shrink-0 rounded-full bg-blue-600 ring-4 ring-blue-100"
                    :title="__('Unread')"
                  />
                  <span v-if="em.is_unread" class="sr-only">{{ __('Unread') }}</span>
                  <router-link
                    v-if="!authStore.isEmailUserOnly"
                    :to="`/tickets/${em.ticket_id}`"
                    class="text-ink-gray-9 hover:text-primary hover:underline truncate block"
                    :class="em.is_unread ? 'font-semibold text-ink-gray-9' : 'font-medium text-ink-gray-8'"
                  >
                    {{ em.subject }}
                  </router-link>
                  <button
                    v-else
                    type="button"
                    class="text-left text-ink-gray-9 hover:text-primary hover:underline truncate block focus:outline-none focus-visible:ring-2 focus-visible:ring-primary rounded"
                    :class="em.is_unread ? 'font-semibold text-ink-gray-9' : 'font-medium text-ink-gray-8'"
                    :title="em.subject"
                    @click="openEmailDetail(em.ticket_id)"
                  >
                    {{ em.subject }}
                  </button>
                  <LucidePaperclip
                    v-if="em.has_attachments"
                    class="size-3.5 shrink-0 text-ink-gray-4"
                    :aria-label="__('Has attachments')"
                  />
                </div>
                <span class="text-[11px] text-ink-gray-5 truncate block font-mono mt-0.5">
                  #{{ em.ticket_id }} &bull; {{ em.original_message_id }}
                </span>
              </td>
              <td class="p-3 whitespace-nowrap text-ink-gray-8">
                <div class="font-medium text-ink-gray-9">{{ em.sender_name }}</div>
                <div class="text-[11px] text-ink-gray-5">{{ em.sender_email }}</div>
              </td>
              <td class="p-3 whitespace-nowrap">
                <div class="flex items-center gap-1.5">
                  <span
                    v-if="em.is_vip"
                    class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-50 text-amber-800 border border-amber-300"
                  >
                    <LucideCrown class="size-3 text-amber-600" />
                    {{ em.cgd_name }}
                  </span>
                  <span
                    v-else
                    class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-surface-gray-2 text-ink-gray-8 border border-outline-gray-2"
                  >
                    {{ em.cgd_name }}
                  </span>
                </div>
              </td>
              <td class="p-3 whitespace-nowrap text-ink-gray-8 font-medium">
                {{ em.team_name }}
              </td>
              <td class="p-3 whitespace-nowrap text-ink-gray-7">
                {{ em.assignee_label }}
              </td>
              <td class="p-3 whitespace-nowrap text-ink-gray-6">
                <div>{{ em.received_date }}</div>
                <div class="text-[11px] text-ink-gray-5">{{ em.received_time }}</div>
              </td>
              <td class="p-3 text-center whitespace-nowrap">
                <span
                  class="px-2.5 py-0.5 rounded-full text-[11px] font-semibold border inline-flex items-center gap-1.5"
                  :class="getStatusBadgeClass(em.status)"
                >
                  <span class="size-1.5 rounded-full" :class="getStatusDotClass(em.status)" />
                  {{ em.status }}
                </span>
              </td>
              <td class="p-3 text-right whitespace-nowrap space-x-1.5">
                <Button
                  variant="outline"
                  size="sm"
                  :label="__('View')"
                  @click="openEmailDetail(em.ticket_id)"
                />
                <Button
                  v-if="!authStore.isEmailUserOnly"
                  variant="subtle"
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

    <SupportEmailDetail
      v-model="showEmailDetail"
      :ticket-id="selectedEmailTicket"
      @changed="emailsResource.reload()"
    />

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
import { useAuthStore } from "@/stores/auth";
import { globalStore } from "@/stores/globalStore";
import {
  Button,
  FormControl,
  LoadingIndicator,
  TextInput,
  createResource,
  toast,
} from "frappe-ui";
import { computed, onMounted, onUnmounted, reactive, ref } from "vue";
import LucideBuilding2 from "~icons/lucide/building-2";
import LucideCrown from "~icons/lucide/crown";
import LucideDownload from "~icons/lucide/download";
import LucideFileSpreadsheet from "~icons/lucide/file-spreadsheet";
import LucideMail from "~icons/lucide/mail";
import LucidePaperclip from "~icons/lucide/paperclip";
import LucideRefreshCw from "~icons/lucide/refresh-cw";
import LucideUsers from "~icons/lucide/users";
import QuickReassignModal from "@/components/ticket-agent/QuickReassignModal.vue";
import SupportEmailDetail from "@/pages/support-emails/SupportEmailDetail.vue";

const authStore = useAuthStore();
const { $socket } = globalStore();

function handleRealtimeUpdate() {
  emailsResource.reload();
  analyticsResource.reload();
}

onMounted(() => {
  if ($socket) {
    $socket.on("helpdesk:new-ticket", handleRealtimeUpdate);
    $socket.on("helpdesk:support-email-synced", handleRealtimeUpdate);
    $socket.on("helpdesk:support-email-received", handleRealtimeUpdate);
  }
});

onUnmounted(() => {
  if ($socket) {
    $socket.off("helpdesk:new-ticket", handleRealtimeUpdate);
    $socket.off("helpdesk:support-email-synced", handleRealtimeUpdate);
    $socket.off("helpdesk:support-email-received", handleRealtimeUpdate);
  }
});

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
  readState: "",
});

const showEmailDetail = ref(false);
const selectedEmailTicket = ref<string | null>(null);

function openEmailDetail(ticketId: string) {
  selectedEmailTicket.value = ticketId;
  showEmailDetail.value = true;
}

function emailListParams(page: number) {
  return {
    page,
    page_length: 15,
    cgd: filters.cgd || null,
    team: filters.team || null,
    status: filters.status || null,
    search_text: filters.search || null,
    read_state: filters.readState || null,
  };
}

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
  params: emailListParams(currentPage.value),
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
  emailsResource.fetch(emailListParams(1));
}

let searchTimeout: any = null;
function debouncedSearch() {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => {
    currentPage.value = 1;
    emailsResource.fetch(emailListParams(1));
  }, 350);
}

function nextPage() {
  if (emailsData.value.has_more) {
    currentPage.value++;
    emailsResource.fetch(emailListParams(currentPage.value));
  }
}

function prevPage() {
  if (currentPage.value > 1) {
    currentPage.value--;
    emailsResource.fetch(emailListParams(currentPage.value));
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
      const inProgress = res.synced_accounts?.some((a: any) => a.status === "in_progress");
      if (res.total_new_emails > 0) {
        toast.success(
          __("Real-time sync complete: Retrieved {0} new support email(s).", [res.total_new_emails])
        );
      } else if (inProgress) {
        toast.info(__("A sync is already running. New emails will appear shortly."));
      } else if (!res.synced_accounts?.length) {
        toast.info(__("No support mailbox is connected yet."));
      } else {
        toast.success(__("Support mailbox is up to date. No new incoming emails."));
      }
      lastSyncedAt.value = new Date().toLocaleTimeString();
      reloadAnalytics();
    } else {
      const errMsg =
        res?.errors?.[0]?.message ||
        __("Email sync completed with errors. Check mail server settings.");
      toast.error(errMsg);
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

function getStatusBadgeClass(status: string) {
  switch (status) {
    case "Open":
      return "bg-sky-50 text-sky-700 border-sky-200";
    case "Pending":
      return "bg-amber-50 text-amber-700 border-amber-200";
    case "Replied":
      return "bg-blue-50 text-blue-700 border-blue-200";
    case "Resolved":
      return "bg-emerald-50 text-emerald-700 border-emerald-200";
    case "Closed":
      return "bg-slate-100 text-slate-700 border-slate-200";
    default:
      return "bg-surface-gray-2 text-ink-gray-7 border-outline-gray-2";
  }
}

function getStatusDotClass(status: string) {
  switch (status) {
    case "Open":
      return "bg-sky-500";
    case "Pending":
      return "bg-amber-500";
    case "Replied":
      return "bg-blue-500";
    case "Resolved":
      return "bg-emerald-500";
    case "Closed":
      return "bg-slate-400";
    default:
      return "bg-surface-gray-4";
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
