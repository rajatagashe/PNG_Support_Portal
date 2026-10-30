<template>
  <div class="flex flex-col">
    <LayoutHeader>
      <template #left-header>
        <div class="text-lg-medium text-ink-gray-9">
          {{ __(dashboardTitle) }}
        </div>
      </template>
      <template #right-header>
        <div class="flex items-center gap-2">
          <Button
            v-if="activeTab !== 'support_emails'"
            variant="outline"
            size="sm"
            :label="__('Custom Report')"
            @click="showCustomReportModal = true"
          >
            <template #prefix>
              <LucideFileSpreadsheet class="size-4 text-ink-gray-6" />
            </template>
          </Button>
          <!-- Segmented pill toggle: visible to managers and agents -->
          <div>
            <TabButtons v-model="activeTab" :options="tabButtons" />
          </div>
        </div>
      </template>
    </LayoutHeader>

    <div v-if="activeTab === 'support_emails'" class="px-4 py-4 w-full">
      <SupportEmailAnalyticsTab />
    </div>

    <div v-else class="px-4 py-4 w-full overflow-y-scroll">
      <!-- Filters -->
      <div class="mb-4 flex flex-wrap items-center gap-3 p-3 bg-slate-50/90 border border-slate-200/90 rounded-2xl shadow-xs">
        <Dropdown v-if="!showDatePicker" :options="options">
          <template #default>
            <div
              class="flex justify-between !min-w-48 items-center bg-white border border-slate-300 rounded-lg text-slate-800 px-3 py-1.5 hover:border-slate-400 hover:shadow-xs focus:border-slate-400 focus:shadow-xs focus:ring-0 focus-visible:ring-0 transition-colors h-8 cursor-pointer shadow-2xs"
            >
              <div class="flex items-center">
                <LucideCalendar class="size-4 text-slate-500 me-2" />
                <span class="text-sm font-medium whitespace-nowrap">{{ preset }}</span>
              </div>
              <LucideChevronDown class="size-4 text-slate-500" />
            </div>
          </template>
        </Dropdown>
        <DateRangePicker
          v-else
          class="!w-48 bg-white rounded-lg shadow-2xs"
          ref="datePickerRef"
          v-model="periodRange"
          variant="outline"
          :placeholder="__('Period')"
          :format="'MMM D'"
          @update:open="onPickerToggle"
        >
          <template #prefix>
            <!-- ms-px: TextInput anchors the prefix to the wrapper, which sits
                 outside the input's 1px border, so it lands 1px left of the
                 preset trigger's icon. -->
            <LucideCalendar class="size-4 text-slate-500 ms-px me-2" />
          </template>
        </DateRangePicker>
        <Link
          v-if="isManager && !viewMyStats"
          class="w-48 bg-white rounded-lg shadow-2xs"
          doctype="HD Team"
          variant="outline"
          :placeholder="__('Team')"
          v-model="filters.team"
        >
          <template #prefix>
            <LucideUsers class="size-4 text-slate-500 me-1" />
          </template>
          <!-- One line per row: the filter only needs the name. -->
          <template #item-label="{ item }">
            <div class="truncate">{{ item.label }}</div>
          </template>
        </Link>
        <Link
          v-if="isManager && !viewMyStats"
          class="w-48 bg-white rounded-lg shadow-2xs"
          doctype="HD Agent"
          variant="outline"
          :placeholder="__('Agent')"
          v-model="filters.agent"
          :filters="agentFilter"
        >
          <template #prefix>
            <LucideUser class="size-4 text-slate-500 me-1" />
          </template>
          <!-- One line per row: the filter only needs the name. -->
          <template #item-label="{ item }">
            <div class="truncate">{{ item.label }}</div>
          </template>
          <!-- An empty list means an empty team, not a failed search. -->
          <template #empty>
            {{
              filters.team && !teamMembers.data?.length
                ? __("No agents in this team")
                : __("No results")
            }}
          </template>
        </Link>
      </div>
      <!-- Charts -->

      <!-- Modernized Executive Number Cards (Inspired by Reference Palette) -->
      <div
        class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3.5 mb-4 px-1"
        v-if="!numberCards.loading"
      >
        <Tooltip
          v-for="({ tooltip, ...card }, index) in numberCards.data"
          :key="index"
          :text="tooltip"
        >
          <div
            class="border rounded-2xl p-3.5 sm:p-4 shadow-xs transition-all duration-200 hover:shadow-md hover:-translate-y-0.5 flex flex-col justify-between select-none group min-h-[148px]"
            :class="[getKpiCardConfig(index, card).cardBg, getKpiCardConfig(index, card).cardBorder]"
          >
            <!-- Top Row: Colored Dot + Title + Subtle Glyph -->
            <div class="flex items-center justify-between gap-1.5">
              <div class="flex items-center gap-2 min-w-0">
                <span
                  class="size-2 rounded-full shrink-0"
                  :class="getKpiCardConfig(index, card).dotColor"
                />
                <span
                  class="text-xs sm:text-sm font-semibold text-slate-800 tracking-tight truncate"
                  :title="card.title"
                >
                  {{ __(card.title) }}
                </span>
              </div>
              <div class="size-6 rounded-md flex items-center justify-center shrink-0 text-slate-400 group-hover:scale-110 transition-transform">
                <component :is="getKpiCardConfig(index, card).icon" class="size-3.5" />
              </div>
            </div>

            <!-- Value & Subtext (Executive Navy Typography) -->
            <div class="mt-1.5">
              <div class="flex items-baseline">
                <span class="text-2xl sm:text-3xl font-extrabold text-[#1b2a5b] tracking-tight leading-none">
                  {{ card.value !== null && card.value !== undefined ? card.value : "-" }}
                </span>
                <span
                  v-if="card.suffix && card.value !== null && card.value !== undefined"
                  class="text-xs font-bold text-slate-500 ms-1"
                >
                  {{ card.suffix }}
                </span>
              </div>
              <div class="text-[11px] text-slate-500 font-medium truncate mt-1">
                {{ __(getKpiCardConfig(index, card).subtext) }}
              </div>
            </div>

            <!-- Meter Progress Line & Ratio Label -->
            <div class="mt-2">
              <div class="h-1.5 w-full bg-[#eef2f6] rounded-full overflow-hidden">
                <div
                  class="h-full rounded-full transition-all duration-500"
                  :class="getKpiCardConfig(index, card).barColor"
                  :style="{ width: getKpiCardConfig(index, card).barWidth }"
                />
              </div>

              <div class="flex items-center justify-between text-[11px] font-semibold mt-1">
                <span :class="getKpiCardConfig(index, card).ratioColor">
                  {{ getKpiCardConfig(index, card).ratioText }}
                </span>
                <span
                  v-if="card.delta !== null && card.delta !== undefined"
                  class="text-[10px] font-bold px-1.5 py-0.2 rounded-full inline-flex items-center gap-0.5"
                  :class="
                    (card.negativeIsBetter ? card.delta <= 0 : card.delta >= 0)
                      ? 'bg-emerald-100 text-emerald-800'
                      : 'bg-rose-100 text-rose-800'
                  "
                >
                  <LucideTrendingUp
                    v-if="card.delta >= 0"
                    class="size-2.5"
                    :class="card.negativeIsBetter ? 'text-rose-600' : 'text-emerald-600'"
                  />
                  <LucideTrendingDown
                    v-else
                    class="size-2.5"
                    :class="card.negativeIsBetter ? 'text-emerald-600' : 'text-rose-600'"
                  />
                  <span>{{ card.delta >= 0 ? '+' : '' }}{{ card.delta }}{{ card.deltaSuffix || '' }}</span>
                </span>
              </div>
            </div>

            <!-- Footer: Context + Details Link -->
            <div class="flex items-center justify-between pt-2 mt-1.5 border-t border-slate-200/60 text-[11px] font-medium text-slate-500">
              <span>{{ __(getKpiCardConfig(index, card).footerLeft) }}</span>
              <router-link
                to="/tickets"
                class="text-[#ea580c] hover:text-[#c2410c] font-semibold inline-flex items-center gap-0.5 transition-colors cursor-pointer"
              >
                <span>{{ __('Details') }}</span>
                <LucideChevronDown class="size-3" />
              </router-link>
            </div>
          </div>
        </Tooltip>
      </div>
      <div
        v-if="!loading && !isEmpty"
        class="transition-all animate-fade-in duration-300"
      >
        <!-- Trend Charts -->
        <div
          class="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-4 px-1"
          v-if="!trendData.loading"
        >
          <template v-for="(chart, index) in trendData.data" :key="index">
            <!-- has data -->
            <ChartCard v-if="!isChartEmpty(chart)" class="h-80">
              <component :is="getChartType(chart)" />
            </ChartCard>

            <!-- chart with no data -->
            <SkeletonLoader
              v-else
              :variants="['bar-chart', 'empty-state']"
              :bar-chart-count="1"
              :has-applied-filter="hasAppliedFilter"
              :empty-states="chartEmptyState(chart)"
            />
          </template>
        </div>
        <!-- Master Data Charts -->
        <div
          class="grid grid-cols-1 md:grid-cols-2 gap-4 w-full mt-4 px-1"
          v-if="!masterData.loading"
        >
          <template v-for="(chart, index) in masterData.data" :key="index">
            <!-- has data -->
            <ChartCard v-if="!isChartEmpty(chart)" class="h-80">
              <component :is="getChartType(chart)" />
            </ChartCard>

            <!-- chart with no data -->
            <SkeletonLoader
              v-else
              :variants="['bar-chart', 'empty-state']"
              :bar-chart-count="1"
              :has-applied-filter="hasAppliedFilter"
              :empty-states="chartEmptyState(chart)"
            />
          </template>
        </div>

        <!-- Tag Charts: org level insight, an agent cannot act on their own tag mix -->
        <div
          class="grid grid-cols-1 md:grid-cols-2 gap-4 w-full mt-4 px-1"
          v-if="isManager && !tagData.loading"
        >
          <template v-for="(chart, index) in tagData.data" :key="index">
            <!-- has data -->
            <ChartCard v-if="!isChartEmpty(chart)" class="h-80">
              <component :is="getChartType(chart)" />
            </ChartCard>

            <!-- chart with no data -->
            <SkeletonLoader
              v-else
              :variants="['bar-chart', 'empty-state']"
              :bar-chart-count="1"
              :has-applied-filter="hasAppliedFilter"
              :empty-states="chartEmptyState(chart)"
            />
          </template>
        </div>

        <!-- Operational Breakdown: CGD Multi-Tenant Health & CSAT Ratings -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-4 px-1">
          <CgdDistributionCard />
          <CsatLeaderboardCard />
        </div>
      </div>

      <!-- Skeleton Loading State -->
      <div class="flex flex-col gap-4">
        <SkeletonLoader
          v-if="numberCards.loading"
          :variants="['number-cards']"
          :number-cards-count="5"
          :loading="true"
        />
        <SkeletonLoader
          v-if="trendData.loading"
          :variants="['bar-chart']"
          :bar-chart-count="4"
          :loading="true"
        />
      </div>

      <!-- complete empty state -->
      <div
        v-if="isEmpty"
        class="transition-all animate-fade-in duration-300 relative"
      >
        <div>
          <SkeletonLoader
            :variants="['bar-chart', 'empty-state']"
            :bar-chart-count="emptyStates.length"
            :empty-states="emptyStates"
            :has-applied-filter="hasAppliedFilter"
          />
        </div>
      </div>
    </div>
    <CustomReportsModal v-model="showCustomReportModal" />
  </div>
</template>

<script setup lang="ts">
import { useScreenSize } from "@/composables/screen";
import { useAuthStore } from "@/stores/auth";
import { __ } from "@/translation";
import { Link } from "@framework/ui";
import { useStorage } from "@vueuse/core";
import {
  Button,
  DateRangePicker,
  Dropdown,
  TabButtons,
  Tooltip,
  createResource,
  dayjs,
  usePageMeta,
} from "frappe-ui";
import { BarChart, ChartCard, DonutChart, NumberCard } from "frappe-ui/charts";
import { computed, h, onMounted, reactive, ref, watch } from "vue";
import LucideBuilding2 from "~icons/lucide/building-2";
import LucideUser from "~icons/lucide/user";
import LucideMail from "~icons/lucide/mail";
import LucideFileSpreadsheet from "~icons/lucide/file-spreadsheet";
import LucideCheckCircle2 from "~icons/lucide/check-circle-2";
import LucideClock from "~icons/lucide/clock";
import LucideShieldCheck from "~icons/lucide/shield-check";
import LucideStar from "~icons/lucide/star";
import LucideTicket from "~icons/lucide/ticket";
import LucideTrendingDown from "~icons/lucide/trending-down";
import LucideTrendingUp from "~icons/lucide/trending-up";
import CsatLeaderboardCard from "./CsatLeaderboardCard.vue";
import CgdDistributionCard from "./CgdDistributionCard.vue";
import CustomReportsModal from "./CustomReportsModal.vue";
import SupportEmailAnalyticsTab from "./SupportEmailAnalyticsTab.vue";
const { isMobileView } = useScreenSize();
const showCustomReportModal = ref(false);

function getKpiCardConfig(index: number, card: any) {
  switch (index) {
    case 0: // Tickets
      return {
        cardBg: "bg-[#fefdfa]",
        cardBorder: "border-amber-200/90 hover:border-amber-400",
        dotColor: "bg-[#f59e0b]",
        barColor: "bg-[#f59e0b]",
        barWidth: "100%",
        ratioColor: "text-amber-700",
        ratioText:
          card.delta !== null && card.delta !== undefined
            ? `${card.delta >= 0 ? "+" : ""}${card.delta}${card.deltaSuffix || "%"} vs last period`
            : "Total volume",
        subtext: "Logged support tickets",
        footerLeft: "All tickets",
        icon: LucideTicket,
      };
    case 1: // % SLA Fulfilled
      const slaVal = Math.min(100, Math.max(0, parseFloat(card.value) || 0));
      return {
        cardBg: "bg-[#fbfefd]",
        cardBorder: "border-emerald-200/90 hover:border-emerald-400",
        dotColor: "bg-[#10b981]",
        barColor: "bg-[#10b981]",
        barWidth: `${slaVal}%`,
        ratioColor: "text-emerald-700",
        ratioText: `${card.value !== null && card.value !== undefined ? card.value : 0}% compliance`,
        subtext: "Response & resolution SLA",
        footerLeft: "SLA target: 95%",
        icon: LucideShieldCheck,
      };
    case 2: // Avg. First Response
      return {
        cardBg: "bg-[#fffdfc]",
        cardBorder: "border-orange-200/90 hover:border-orange-400",
        dotColor: "bg-[#ea580c]",
        barColor: "bg-[#ea580c]",
        barWidth: "72%",
        ratioColor: "text-orange-700",
        ratioText:
          card.delta !== null && card.delta !== undefined
            ? `${card.delta <= 0 ? "Improved " : "Increased "}${Math.abs(card.delta)}${card.deltaSuffix || "%"}`
            : "First reply latency",
        subtext: "First agent reply duration",
        footerLeft: "Target: <2h",
        icon: LucideClock,
      };
    case 3: // Avg. Resolution
      return {
        cardBg: "bg-[#fafbfd]",
        cardBorder: "border-slate-300 hover:border-indigo-400",
        dotColor: "bg-[#1b2a5b]",
        barColor: "bg-[#1b2a5b]",
        barWidth: "64%",
        ratioColor: "text-slate-800",
        ratioText:
          card.delta !== null && card.delta !== undefined
            ? `${card.delta <= 0 ? "Faster " : "Slower "}${Math.abs(card.delta)}${card.deltaSuffix || "%"}`
            : "Full lifecycle duration",
        subtext: "Full resolution cycle",
        footerLeft: "Target: <24h",
        icon: LucideCheckCircle2,
      };
    case 4: // Avg. Feedback Rating
      const rating = Math.min(5, Math.max(0, parseFloat(card.value) || 0));
      return {
        cardBg: "bg-[#fefbfb]",
        cardBorder: "border-rose-300 hover:border-rose-400",
        dotColor: "bg-[#ef4444]",
        barColor: "bg-[#ef4444]",
        barWidth: `${(rating / 5) * 100}%`,
        ratioColor: "text-rose-700",
        ratioText: `${card.value !== null && card.value !== undefined ? card.value : "0.0"} / 5.0 score`,
        subtext: "Customer satisfaction score",
        footerLeft: "CSAT rating",
        icon: LucideStar,
      };
    default:
      return {
        cardBg: "bg-white",
        cardBorder: "border-slate-300 hover:border-slate-400",
        dotColor: "bg-slate-400",
        barColor: "bg-slate-400",
        barWidth: "50%",
        ratioColor: "text-slate-600",
        ratioText: "",
        subtext: "",
        footerLeft: "Status",
        icon: LucideTicket,
      };
  }
}

interface NumberCardData {
  title: string;
  value: number | null;
  delta: number | null;
  deltaSuffix: string;
  suffix?: string;
  negativeIsBetter?: boolean;
  tooltip: string;
}

type Filters = {
  period: string;
  agent: null | string;
  team: null | string;
};

const filters = reactive<Filters>({
  period: getLastXDays(),
  agent: null,
  team: null,
});

interface ChartData {
  data: ChartValues[];
  title: string;
  type: "bar" | "donut";
}

interface ChartValues {
  date: Date;
  Open: number;
  Closed: number;
  "SLA Fulfilled": number;
}

const dashboardTitle = computed(() => {
  if (activeTab.value === "support_emails") return __("Support Email Management & Analytics");
  if (!isManager) return __("Agent Dashboard");
  return viewMyStats.value ? __("My Dashboard") : __("Organization Dashboard");
});

interface ChartEmptyState {
  // header of the card, shown untranslated only when the chart itself is missing
  chartTitle: string;
  chartSubtitle?: string;
  title: string;
  message: string;
}

// Chart key (stable, untranslated identifier from the dashboard APIs) → empty state copy.
const emptyStateByChart: Record<string, ChartEmptyState> = {
  ticket_trend: {
    chartTitle: "Ticket Trend",
    title: "No ticket activity",
    message: "Ticket trends will appear here once tickets are created.",
  },
  feedback_trend: {
    chartTitle: "Feedback Trend",
    title: "No feedback data",
    message: "Feedback insights will appear once responses are collected.",
  },
  tickets_by_team: {
    chartTitle: "Tickets by Team",
    title: "No team data",
    message: "Tickets will be grouped by team once available.",
  },
  tickets_by_type: {
    chartTitle: "Tickets by Type",
    title: "No ticket type data",
    message: "Tickets will be categorized by type once created.",
  },
  tickets_by_priority: {
    chartTitle: "Tickets by Priority",
    title: "No priority data",
    message: "Ticket priorities will be reflected here once assigned.",
  },
  tickets_by_channel: {
    chartTitle: "Tickets by Channel",
    title: "No channel data",
    message: "Tickets will be grouped by channel once received.",
  },
  top_tags: {
    chartTitle: "Top Tags",
    title: "No tags used yet",
    message: "The most used tags will be ranked here once tickets are tagged.",
  },
  tag_trend: {
    chartTitle: "Tag Trend",
    title: "No tag activity",
    message: "Daily tag volume will appear here once tickets are tagged.",
  },
};

const managerOnlyCharts = ["top_tags", "tag_trend"];

// whole dashboard empty: no chart payload to read titles from, so fall back to ours
const emptyStates = computed(() =>
  Object.entries(emptyStateByChart)
    .filter(([key]) => isManager || !managerOnlyCharts.includes(key))
    .map(([, state]) => state)
);

function chartEmptyState(chart: any) {
  const state = emptyStateByChart[chart?.key] ?? {
    title: `No ${String(chart?.title).toLowerCase()} available`,
  };
  return [
    { ...state, chartTitle: chart?.title, chartSubtitle: chart?.subtitle },
  ];
}

const tabButtons = computed(() => {
  const isMobile = isMobileView.value;
  const tabs = [];
  if (isManager) {
    tabs.push({
      value: "organization",
      label: __("My Organization"),
      [isMobile ? "icon" : "iconLeft"]: h(LucideBuilding2, { class: "size-4" }),
    });
  }
  tabs.push({
    value: "my_stats",
    label: __("My Stats"),
    [isMobile ? "icon" : "iconLeft"]: h(LucideUser, { class: "size-4" }),
  });
  tabs.push({
    value: "support_emails",
    label: __("Support Emails"),
    [isMobile ? "icon" : "iconLeft"]: h(LucideMail, { class: "size-4" }),
  });
  return tabs;
});

const hasAppliedFilter = computed(() =>
  Boolean(
    filters.agent ||
      filters.team ||
      (filters.period && filters.period !== getLastXDays(30))
  )
);

const isEmpty = computed(() => {
  if (!numberCards.data || !trendData.data || !masterData.data) return false;
  return (
    (numberCards.data as NumberCardData[]).every((d) => !d.value) &&
    (trendData.data as ChartData[]).every((d) => !d.data?.length) &&
    (masterData.data as ChartData[]).every((d) => !d.data?.length)
  );
});

const parseFilters = (filters: Filters) => {
  return {
    from_date: filters.period?.split(",")[0] ?? null,
    to_date: filters.period?.split(",")[1] ?? null,
    team: filters.team,
    agent: filters.agent,
  };
};

// No `cache` key here: a static cache key makes frappe-ui return the same
// resource instance across navigations, still bound to the previous mount's
// `filters` closure, so reloads after navigating back send stale params.
const numberCards = createResource({
  url: "helpdesk.api.dashboard.get_dashboard_data",
  makeParams: () => ({
    dashboard_type: "number_card",
    filters: parseFilters(filters),
  }),
});

const masterData = createResource({
  url: "helpdesk.api.dashboard.get_dashboard_data",
  makeParams: () => ({
    dashboard_type: "master",
    filters: parseFilters(filters),
  }),
});

const trendData = createResource({
  url: "helpdesk.api.dashboard.get_dashboard_data",
  makeParams: () => ({
    dashboard_type: "trend",
    filters: parseFilters(filters),
  }),
});

const tagData = createResource({
  url: "helpdesk.api.dashboard.get_dashboard_data",
  makeParams: () => ({
    dashboard_type: "tags",
    filters: parseFilters(filters),
  }),
});

const agentFilter = ref(null);
const teamMembers = createResource({
  url: "helpdesk.helpdesk.doctype.hd_team.hd_team.get_team_members",
  cache: ["Analytics", "TeamMembers"],
  params: {
    team: filters.team,
  },
  onSuccess: (data) => {
    agentFilter.value = { name: ["in", data] };
  },
});

const { isManager, userId } = useAuthStore();

const viewMyStats = ref(false);
const activeTab = useStorage("dashboard_active_tab", "organization");
function validateView(myStats: boolean) {
  viewMyStats.value = myStats;
  if (myStats) {
    filters.team = null;
    filters.agent = userId;
  } else {
    filters.agent = null;
  }
}

watch(activeTab, (val) => {
  if (val === "support_emails") return;
  validateView(val === "my_stats");
});

watch(
  () => filters.team,
  (newVal) => {
    filters.agent = null; // Reset agent when team is selected
    if (newVal) {
      teamMembers.update({
        params: {
          team: newVal,
        },
      });
      teamMembers.reload();
    }
    if (!newVal) {
      agentFilter.value = null; // Reset agent filter if no team is selected
    }
  }
);

//check empty for individual charts
function isChartEmpty(chart: any) {
  if (!chart.data?.length) return true;
  return chart.data.every((row: any) =>
    Object.entries(row)
      .filter(([key]) => key !== "date")
      .every(([, val]) => val === null || val === 0)
  );
}

const loading = computed(() => {
  return numberCards.loading || masterData.loading || trendData.loading;
});

// api already sends the frappe-ui props for each chart
function getChartType({ type, key, ...props }: any) {
  return h(type === "donut" ? DonutChart : BarChart, props);
}

// include today, so last 7 days is today and the 6 days before
function getLastXDays(range: number = 30): string {
  const today = new Date();
  const lastXDate = new Date(today);

  lastXDate.setDate(today.getDate() - (range - 1));
  return `${dayjs(lastXDate).format("YYYY-MM-DD")},${dayjs(today).format(
    "YYYY-MM-DD"
  )}`;
}

const showDatePicker = ref(false);
const datePickerRef = ref(null);
const preset = ref(__("Last 30 Days"));

// frappe-ui v1 DateRangePicker models a [from, to] tuple; filters.period and
// the API keep the legacy "from,to" string, so convert at the picker boundary.
const periodRange = computed({
  get: (): string[] => (filters.period ? filters.period.split(",") : []),
  set: (range: string[]) => {
    showDatePicker.value = false;
    filters.period = range?.length ? range.join(",") : "";
    preset.value = formatter(filters.period);
  },
});

// dismissing the calendar without a range would otherwise leave an empty
// field where the preset menu used to be, with no way back to it
function onPickerToggle(open: boolean) {
  if (!open && !filters.period) {
    showDatePicker.value = false;
    preset.value = formatter("");
  }
}

const options = computed(() => [
  {
    group: __("Presets"),
    hideLabel: true,
    options: [
      {
        label: __("Today"),
        onClick: () => {
          preset.value = __("Today");
          filters.period = getLastXDays(1);
        },
      },
      {
        label: __("Last 7 Days"),
        onClick: () => {
          preset.value = __("Last 7 Days");
          filters.period = getLastXDays(7);
        },
      },
      {
        label: __("Last 30 Days"),
        onClick: () => {
          preset.value = __("Last 30 Days");
          filters.period = getLastXDays(30);
        },
      },
      {
        label: __("Last 60 Days"),
        onClick: () => {
          preset.value = __("Last 60 Days");
          filters.period = getLastXDays(60);
        },
      },
      {
        label: __("Last 90 Days"),
        onClick: () => {
          preset.value = __("Last 90 Days");
          filters.period = getLastXDays(90);
        },
      },
    ],
  },
  {
    label: __("Custom Range"),
    onClick: () => {
      showDatePicker.value = true;
      setTimeout(() => {
        datePickerRef.value?.open();
      }, 0);
      preset.value = __("Custom Range");
      filters.period = null; // Reset period to allow custom date selection
    },
  },
]);

function formatter(range: string) {
  if (!range) {
    filters.period = getLastXDays();
    preset.value = __("Last 30 Days");
    return preset.value;
  }
  let [from, to] = range.split(",");
  return `${formatRange(from)} to ${formatRange(to)}`;
}

function formatRange(date: string) {
  const dateObj = new Date(date);
  return dateObj.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year:
      dateObj.getFullYear() === new Date().getFullYear()
        ? undefined
        : "numeric",
  });
}

watch(
  () => filters,
  () => {
    if (showDatePicker.value && !filters.period) return;
    numberCards.reload();
    masterData.reload();
    trendData.reload();
    if (isManager) tagData.reload();
  },
  { deep: true }
);

onMounted(() => {
  if (!isManager) {
    filters.agent = userId;
  } else {
    validateView(activeTab.value === "my_stats");
  }
  numberCards.reload();
  masterData.reload();
  trendData.reload();
  if (isManager) tagData.reload();
});

usePageMeta(() => {
  return {
    title: __("Dashboard"),
  };
});
</script>

<style scoped>
:deep(.form-control button) {
  @apply text-base rounded-4 h-7 py-1.5 border border-outline-gray-2 bg-surface-base placeholder-ink-gray-4 hover:border-outline-gray-3 hover:shadow-sm focus:bg-surface-base focus:border-outline-gray-4 focus:shadow-sm focus:ring-0 focus-visible:ring-0 text-ink-gray-8 transition-colors w-full dark:[color-scheme:dark];
}
:deep(.form-control button > div) {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

:deep(.form-control div) {
  width: 100%;
  display: flex;
}
</style>
