<template>
  <div class="space-y-4 antialiased">
    <!-- Top Controls Toolbar -->
    <div class="flex flex-wrap items-center justify-between gap-3 bg-slate-50/90 border border-slate-200/90 rounded-2xl p-3 sm:p-4 shadow-xs">
      <!-- View Mode Tabs: Daily / Weekly / Monthly -->
      <div class="flex items-center gap-1 bg-slate-200/80 p-1 rounded-xl border border-slate-300/80">
        <button
          v-for="mode in ['daily', 'weekly', 'monthly']"
          :key="mode"
          type="button"
          class="px-3.5 py-1 text-xs font-semibold rounded-lg capitalize transition-all focus:outline-none"
          :class="
            viewMode === mode
              ? 'bg-[#d9531e] text-white shadow-2xs'
              : 'text-slate-600 hover:text-slate-900 hover:bg-white/60'
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
          class="rounded-xl !bg-white !border-slate-300 hover:!border-slate-400 hover:!bg-slate-50 text-slate-800 shadow-2xs font-semibold"
          :label="__('Sync Inbound Emails')"
          :loading="isSyncing"
          @click="triggerEmailSync"
        >
          <template #prefix>
            <LucideRefreshCw class="size-3.5 text-[#d9531e]" :class="{ 'animate-spin': isSyncing }" />
          </template>
        </Button>
        <Button
          variant="outline"
          size="sm"
          class="rounded-xl !bg-white !border-slate-300 hover:!border-slate-400 hover:!bg-slate-50 text-slate-800 shadow-2xs font-semibold"
          :label="__('Export Excel (.xlsx)')"
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
          class="rounded-xl !bg-white !border-slate-300 hover:!border-slate-400 hover:!bg-slate-50 text-slate-800 shadow-2xs font-semibold"
          :label="__('Export CSV')"
          :loading="isExportingCsv"
          @click="exportCSV"
        >
          <template #prefix>
            <LucideDownload class="size-3.5 text-slate-600" />
          </template>
        </Button>
      </div>
    </div>

    <!-- Filter Bar Card -->
    <div class="bg-slate-50/90 border border-slate-200/90 rounded-2xl p-4 shadow-xs">
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 text-xs">
        <Link
          class="w-full bg-white rounded-lg"
          doctype="HD Customer"
          variant="outline"
          :placeholder="__('Filter by CGD Organization')"
          :label="__('CGD Entity')"
          v-model="filters.cgd"
          @change="reloadAnalytics"
        />
        <Link
          class="w-full bg-white rounded-lg"
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
          class="bg-white rounded-lg"
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
          class="bg-white rounded-lg"
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
            class="w-full bg-white rounded-lg"
            :aria-label="__('Search support emails')"
            :placeholder="__('Search sender, subject or message...')"
            variant="outline"
            @input="debouncedSearch"
          />
        </div>
      </div>
    </div>

    <!-- Period Comparison Subtitle -->
    <div class="flex items-center justify-between text-xs text-slate-600 px-1 font-medium">
      <div>
        <span class="font-bold text-slate-900">{{ analyticsData?.period_label }}</span>
        <span class="ml-2 italic text-slate-500">({{ analyticsData?.comparison_label }})</span>
      </div>
      <div v-if="lastSyncedAt" class="text-slate-500 font-semibold">
        {{ __('Last Synced:') }} {{ lastSyncedAt }}
      </div>
    </div>

    <!-- 5 ORIGINAL SUPPORT EMAIL KPI CARDS (Inspired by Reference Palette) -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3.5">
      <!-- 1. Total Emails Received -->
      <div class="bg-[#fefdfa] border border-amber-200/90 hover:border-amber-400 rounded-2xl p-3.5 sm:p-4 shadow-xs transition-all duration-200 hover:shadow-md hover:-translate-y-0.5 flex flex-col justify-between select-none group min-h-[148px]">
        <div class="flex items-center justify-between gap-1.5">
          <div class="flex items-center gap-2 min-w-0">
            <span class="size-2 rounded-full bg-[#f59e0b] shrink-0" />
            <span class="text-xs sm:text-sm font-semibold text-slate-800 tracking-tight truncate">{{ __('Total Emails Received') }}</span>
          </div>
          <div class="size-6 rounded-md flex items-center justify-center shrink-0 text-slate-400 group-hover:scale-110 transition-transform">
            <LucideInbox class="size-3.5" />
          </div>
        </div>
        <div class="mt-1.5">
          <div class="text-2xl sm:text-3xl font-extrabold text-[#1b2a5b] tracking-tight leading-none">
            {{ summary.total_received?.value || 0 }}
          </div>
          <div class="text-[11px] text-slate-500 font-medium truncate mt-1">
            {{ __('Inbound mailbox intake') }}
          </div>
        </div>
        <div class="mt-2">
          <div class="h-1.5 w-full bg-[#eef2f6] rounded-full overflow-hidden">
            <div class="h-full rounded-full bg-[#f59e0b] transition-all duration-500 w-full" />
          </div>
          <div class="flex items-center justify-between text-[11px] font-semibold mt-1">
            <span class="text-amber-700">
              {{ summary.total_received?.comparison ? (summary.total_received.comparison.diff >= 0 ? '+' : '') + summary.total_received.comparison.pct + '% vs previous' : '100% of total' }}
            </span>
            <span
              v-if="summary.total_received?.comparison"
              class="text-[10px] font-bold px-1.5 py-0.2 rounded-full inline-flex items-center gap-0.5"
              :class="
                summary.total_received.comparison.diff >= 0
                  ? 'bg-emerald-100 text-emerald-800'
                  : 'bg-rose-100 text-rose-800'
              "
            >
              <LucideTrendingUp v-if="summary.total_received.comparison.diff >= 0" class="size-2.5 text-emerald-600" />
              <LucideTrendingDown v-else class="size-2.5 text-rose-600" />
              <span>{{ summary.total_received.comparison.diff >= 0 ? '+' : '' }}{{ summary.total_received.comparison.pct }}%</span>
            </span>
          </div>
        </div>
        <div class="flex items-center justify-between pt-2 mt-1.5 border-t border-slate-200/60 text-[11px] font-medium text-slate-500">
          <span>{{ __('All inboxes') }}</span>
          <button
            type="button"
            class="text-[#ea580c] hover:text-[#c2410c] font-semibold inline-flex items-center gap-0.5 transition-colors cursor-pointer focus:outline-none"
            @click="onEmailKpiClick('all')"
          >
            <span>{{ __('Details') }}</span>
            <LucideChevronDown class="size-3" />
          </button>
        </div>
      </div>

      <!-- 2. Unassigned Emails -->
      <div class="bg-[#fffdfc] border border-orange-200/90 hover:border-orange-400 rounded-2xl p-3.5 sm:p-4 shadow-xs transition-all duration-200 hover:shadow-md hover:-translate-y-0.5 flex flex-col justify-between select-none group min-h-[148px]">
        <div class="flex items-center justify-between gap-1.5">
          <div class="flex items-center gap-2 min-w-0">
            <span class="size-2 rounded-full bg-[#ea580c] shrink-0" />
            <span class="text-xs sm:text-sm font-semibold text-slate-800 tracking-tight truncate">{{ __('Unassigned Emails') }}</span>
          </div>
          <div class="size-6 rounded-md flex items-center justify-center shrink-0 text-slate-400 group-hover:scale-110 transition-transform">
            <LucideAlertCircle class="size-3.5" />
          </div>
        </div>
        <div class="mt-1.5">
          <div class="text-2xl sm:text-3xl font-extrabold text-[#1b2a5b] tracking-tight leading-none">
            {{ summary.unassigned?.value || 0 }}
          </div>
          <div class="text-[11px] text-slate-500 font-medium truncate mt-1">
            {{ __('Awaiting queue dispatch') }}
          </div>
        </div>
        <div class="mt-2">
          <div class="h-1.5 w-full bg-[#eef2f6] rounded-full overflow-hidden">
            <div
              class="h-full rounded-full bg-[#ea580c] transition-all duration-500"
              :style="{ width: getEmailPct(summary.unassigned?.value) + '%' }"
            />
          </div>
          <div class="flex items-center justify-between text-[11px] font-semibold mt-1">
            <span class="text-orange-700">
              {{ getEmailPct(summary.unassigned?.value) }}% of total
            </span>
            <span
              v-if="summary.unassigned?.comparison"
              class="text-[10px] font-bold px-1.5 py-0.2 rounded-full bg-slate-100 text-slate-700 inline-flex items-center gap-0.5"
            >
              <LucideTrendingUp v-if="summary.unassigned.comparison.diff > 0" class="size-2.5 text-slate-600" />
              <LucideTrendingDown v-else-if="summary.unassigned.comparison.diff < 0" class="size-2.5 text-slate-600" />
              <span>{{ summary.unassigned.comparison.diff >= 0 ? '+' : '' }}{{ summary.unassigned.comparison.diff }}</span>
            </span>
          </div>
        </div>
        <div class="flex items-center justify-between pt-2 mt-1.5 border-t border-slate-200/60 text-[11px] font-medium text-slate-500">
          <span>{{ __('Needs triage') }}</span>
          <button
            type="button"
            class="text-[#ea580c] hover:text-[#c2410c] font-semibold inline-flex items-center gap-0.5 transition-colors cursor-pointer focus:outline-none"
            @click="onEmailKpiClick('unassigned')"
          >
            <span>{{ __('Details') }}</span>
            <LucideChevronDown class="size-3" />
          </button>
        </div>
      </div>

      <!-- 3. Assigned Emails -->
      <div class="bg-[#fafbfd] border border-slate-300 hover:border-indigo-400 rounded-2xl p-3.5 sm:p-4 shadow-xs transition-all duration-200 hover:shadow-md hover:-translate-y-0.5 flex flex-col justify-between select-none group min-h-[148px]">
        <div class="flex items-center justify-between gap-1.5">
          <div class="flex items-center gap-2 min-w-0">
            <span class="size-2 rounded-full bg-[#1b2a5b] shrink-0" />
            <span class="text-xs sm:text-sm font-semibold text-slate-800 tracking-tight truncate">{{ __('Assigned Emails') }}</span>
          </div>
          <div class="size-6 rounded-md flex items-center justify-center shrink-0 text-slate-400 group-hover:scale-110 transition-transform">
            <LucideUserCheck class="size-3.5" />
          </div>
        </div>
        <div class="mt-1.5">
          <div class="text-2xl sm:text-3xl font-extrabold text-[#1b2a5b] tracking-tight leading-none">
            {{ summary.assigned?.value || 0 }}
          </div>
          <div class="text-[11px] text-slate-500 font-medium truncate mt-1">
            {{ __('Allocated to active agents') }}
          </div>
        </div>
        <div class="mt-2">
          <div class="h-1.5 w-full bg-[#eef2f6] rounded-full overflow-hidden">
            <div
              class="h-full rounded-full bg-[#1b2a5b] transition-all duration-500"
              :style="{ width: getEmailPct(summary.assigned?.value) + '%' }"
            />
          </div>
          <div class="flex items-center justify-between text-[11px] font-semibold mt-1">
            <span class="text-slate-800">
              {{ getEmailPct(summary.assigned?.value) }}% of total
            </span>
            <span
              v-if="summary.assigned?.comparison"
              class="text-[10px] font-bold px-1.5 py-0.2 rounded-full bg-slate-100 text-slate-700 inline-flex items-center gap-0.5"
            >
              <LucideTrendingUp v-if="summary.assigned.comparison.diff > 0" class="size-2.5 text-slate-600" />
              <LucideTrendingDown v-else-if="summary.assigned.comparison.diff < 0" class="size-2.5 text-slate-600" />
              <span>{{ summary.assigned.comparison.diff >= 0 ? '+' : '' }}{{ summary.assigned.comparison.diff }}</span>
            </span>
          </div>
        </div>
        <div class="flex items-center justify-between pt-2 mt-1.5 border-t border-slate-200/60 text-[11px] font-medium text-slate-500">
          <span>{{ __('Active queue') }}</span>
          <button
            type="button"
            class="text-[#ea580c] hover:text-[#c2410c] font-semibold inline-flex items-center gap-0.5 transition-colors cursor-pointer focus:outline-none"
            @click="onEmailKpiClick('assigned')"
          >
            <span>{{ __('Details') }}</span>
            <LucideChevronDown class="size-3" />
          </button>
        </div>
      </div>

      <!-- 4. Currently In Progress -->
      <div class="bg-[#f8faff] border border-sky-200/90 hover:border-sky-400 rounded-2xl p-3.5 sm:p-4 shadow-xs transition-all duration-200 hover:shadow-md hover:-translate-y-0.5 flex flex-col justify-between select-none group min-h-[148px]">
        <div class="flex items-center justify-between gap-1.5">
          <div class="flex items-center gap-2 min-w-0">
            <span class="size-2 rounded-full bg-[#0284c7] shrink-0" />
            <span class="text-xs sm:text-sm font-semibold text-slate-800 tracking-tight truncate">{{ __('Currently In Progress') }}</span>
          </div>
          <div class="size-6 rounded-md flex items-center justify-center shrink-0 text-slate-400 group-hover:scale-110 transition-transform">
            <LucideClock class="size-3.5" />
          </div>
        </div>
        <div class="mt-1.5">
          <div class="text-2xl sm:text-3xl font-extrabold text-[#1b2a5b] tracking-tight leading-none">
            {{ summary.in_progress?.value || 0 }}
          </div>
          <div class="text-[11px] text-slate-500 font-medium truncate mt-1">
            {{ __('Under investigation · pending') }}
          </div>
        </div>
        <div class="mt-2">
          <div class="h-1.5 w-full bg-[#eef2f6] rounded-full overflow-hidden">
            <div
              class="h-full rounded-full bg-[#0284c7] transition-all duration-500"
              :style="{ width: getEmailPct(summary.in_progress?.value) + '%' }"
            />
          </div>
          <div class="flex items-center justify-between text-[11px] font-semibold mt-1">
            <span class="text-sky-800">
              {{ getEmailPct(summary.in_progress?.value) }}% of total
            </span>
            <span
              v-if="summary.in_progress?.comparison"
              class="text-[10px] font-bold px-1.5 py-0.2 rounded-full bg-slate-100 text-slate-700 inline-flex items-center gap-0.5"
            >
              <LucideTrendingUp v-if="summary.in_progress.comparison.diff > 0" class="size-2.5 text-slate-600" />
              <LucideTrendingDown v-else-if="summary.in_progress.comparison.diff < 0" class="size-2.5 text-slate-600" />
              <span>{{ summary.in_progress.comparison.diff >= 0 ? '+' : '' }}{{ summary.in_progress.comparison.diff }}</span>
            </span>
          </div>
        </div>
        <div class="flex items-center justify-between pt-2 mt-1.5 border-t border-slate-200/60 text-[11px] font-medium text-slate-500">
          <span>{{ __('In progress') }}</span>
          <button
            type="button"
            class="text-[#ea580c] hover:text-[#c2410c] font-semibold inline-flex items-center gap-0.5 transition-colors cursor-pointer focus:outline-none"
            @click="onEmailKpiClick('in_progress')"
          >
            <span>{{ __('Details') }}</span>
            <LucideChevronDown class="size-3" />
          </button>
        </div>
      </div>

      <!-- 5. Resolved / Closed -->
      <div class="bg-[#fbfefd] border border-emerald-200/90 hover:border-emerald-400 rounded-2xl p-3.5 sm:p-4 shadow-xs transition-all duration-200 hover:shadow-md hover:-translate-y-0.5 flex flex-col justify-between select-none group min-h-[148px]">
        <div class="flex items-center justify-between gap-1.5">
          <div class="flex items-center gap-2 min-w-0">
            <span class="size-2 rounded-full bg-[#10b981] shrink-0" />
            <span class="text-xs sm:text-sm font-semibold text-slate-800 tracking-tight truncate">{{ __('Resolved / Closed') }}</span>
          </div>
          <div class="size-6 rounded-md flex items-center justify-center shrink-0 text-slate-400 group-hover:scale-110 transition-transform">
            <LucideCheckCircle2 class="size-3.5" />
          </div>
        </div>
        <div class="mt-1.5">
          <div class="text-2xl sm:text-3xl font-extrabold text-[#1b2a5b] tracking-tight leading-none">
            {{ summary.resolved?.value || 0 }}
          </div>
          <div class="text-[11px] text-slate-500 font-medium truncate mt-1">
            {{ __('Resolution complete · closed') }}
          </div>
        </div>
        <div class="mt-2">
          <div class="h-1.5 w-full bg-[#eef2f6] rounded-full overflow-hidden">
            <div
              class="h-full rounded-full bg-[#10b981] transition-all duration-500"
              :style="{ width: getEmailPct(summary.resolved?.value) + '%' }"
            />
          </div>
          <div class="flex items-center justify-between text-[11px] font-semibold mt-1">
            <span class="text-emerald-700">
              {{ getEmailPct(summary.resolved?.value) }}% of total
            </span>
            <span
              v-if="summary.resolved?.comparison"
              class="text-[10px] font-bold px-1.5 py-0.2 rounded-full bg-emerald-100 text-emerald-800 inline-flex items-center gap-0.5"
            >
              <LucideTrendingUp v-if="summary.resolved.comparison.diff >= 0" class="size-2.5 text-emerald-600" />
              <LucideTrendingDown v-else class="size-2.5 text-rose-600" />
              <span>{{ summary.resolved.comparison.diff >= 0 ? '+' : '' }}{{ summary.resolved.comparison.diff }}</span>
            </span>
          </div>
        </div>
        <div class="flex items-center justify-between pt-2 mt-1.5 border-t border-slate-200/60 text-[11px] font-medium text-slate-500">
          <span>{{ __('Closed queries') }}</span>
          <button
            type="button"
            class="text-[#ea580c] hover:text-[#c2410c] font-semibold inline-flex items-center gap-0.5 transition-colors cursor-pointer focus:outline-none"
            @click="onEmailKpiClick('resolved')"
          >
            <span>{{ __('Details') }}</span>
            <LucideChevronDown class="size-3" />
          </button>
        </div>
      </div>
    </div>

    <!-- CGD & Team Distribution Row (Exact Original Distribution Calculations & Proportions) -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <!-- 1. Emails by CGD Organization -->
      <div class="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-xs">
        <div class="flex items-center justify-between pb-3 mb-3 border-b border-slate-100">
          <div class="flex items-center gap-2 font-bold text-xs text-slate-900 uppercase tracking-wider">
            <LucideBuilding2 class="size-4 text-[#d9531e]" />
            <span>{{ __('Emails by CGD Organization') }}</span>
          </div>
          <span class="text-[11px] font-bold text-slate-700 bg-slate-100 border border-slate-200 px-2.5 py-0.5 rounded-full">
            {{ analyticsData?.cgd_distribution?.length || 0 }} {{ __('entities') }}
          </span>
        </div>

        <div v-if="!analyticsData?.cgd_distribution?.length" class="text-xs text-slate-500 py-8 text-center">
          {{ __('No CGD emails recorded in this period.') }}
        </div>
        <div v-else class="space-y-3 max-h-56 overflow-y-auto pr-1">
          <div
            v-for="item in analyticsData.cgd_distribution"
            :key="item.cgd_id"
            class="p-2.5 rounded-xl bg-slate-50/90 hover:bg-slate-100/90 border border-slate-200/80 transition-colors"
          >
            <div class="flex items-center justify-between text-xs mb-1.5">
              <div class="flex items-center gap-1.5 truncate">
                <LucideCrown v-if="item.is_vip" class="size-3.5 text-amber-500 shrink-0" />
                <span class="truncate font-bold text-slate-900">{{ item.cgd_name }}</span>
              </div>
              <div class="flex items-center gap-2 shrink-0">
                <span class="font-extrabold text-slate-900">{{ item.count }}</span>
                <span class="text-[11px] text-amber-700 font-bold" v-if="item.open_count > 0">
                  ({{ item.open_count }} {{ __('open') }})
                </span>
              </div>
            </div>
            <!-- Proportional Progress Bar -->
            <div class="w-full bg-slate-200 rounded-full h-2 overflow-hidden shadow-inner">
              <div
                class="bg-[#d9531e] h-2 rounded-full transition-all duration-300"
                :style="{
                  width: `${Math.min(100, (item.count / (summary.total_received?.value || 1)) * 100)}%`
                }"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- 2. Emails by Assigned Team -->
      <div class="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-xs">
        <div class="flex items-center justify-between pb-3 mb-3 border-b border-slate-100">
          <div class="flex items-center gap-2 font-bold text-xs text-slate-900 uppercase tracking-wider">
            <LucideUsers class="size-4 text-indigo-600" />
            <span>{{ __('Emails by Assigned Team') }}</span>
          </div>
          <span class="text-[11px] font-bold text-slate-700 bg-slate-100 border border-slate-200 px-2.5 py-0.5 rounded-full">
            {{ analyticsData?.team_distribution?.length || 0 }} {{ __('teams') }}
          </span>
        </div>

        <div v-if="!analyticsData?.team_distribution?.length" class="text-xs text-slate-500 py-8 text-center">
          {{ __('No team assignments in this period.') }}
        </div>
        <div v-else class="space-y-3 max-h-56 overflow-y-auto pr-1">
          <div
            v-for="item in analyticsData.team_distribution"
            :key="item.team_name"
            class="p-2.5 rounded-xl bg-slate-50/90 hover:bg-slate-100/90 border border-slate-200/80 transition-colors"
          >
            <div class="flex items-center justify-between text-xs mb-1.5">
              <span class="truncate font-bold text-slate-900">{{ item.team_name }}</span>
              <div class="flex items-center gap-2 shrink-0">
                <span class="font-extrabold text-slate-900">{{ item.count }}</span>
                <span class="text-[11px] text-amber-700 font-bold" v-if="item.open_count > 0">
                  ({{ item.open_count }} {{ __('open') }})
                </span>
              </div>
            </div>
            <!-- Proportional Progress Bar -->
            <div class="w-full bg-slate-200 rounded-full h-2 overflow-hidden shadow-inner">
              <div
                class="bg-indigo-500 h-2 rounded-full transition-all duration-300"
                :style="{
                  width: `${Math.min(100, (item.count / (summary.total_received?.value || 1)) * 100)}%`
                }"
              />
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Inbound Support Emails Table Card -->
    <div class="bg-white border border-slate-200/90 rounded-2xl shadow-xs overflow-hidden">
      <div class="p-4 border-b border-slate-200/90 flex flex-wrap items-center justify-between gap-3 bg-slate-50/90">
        <div class="flex items-center gap-2.5">
          <div class="flex size-7 items-center justify-center rounded-lg bg-orange-50 text-[#d9531e] border border-orange-200">
            <LucideMail class="size-3.5" />
          </div>
          <span class="font-bold text-sm text-slate-900">
            {{ __('Inbound Support Emails & Tickets') }}
          </span>
          <span class="px-2.5 py-0.5 rounded-full text-xs font-bold bg-white text-slate-700 border border-slate-300 shadow-2xs">
            {{ emailsData.total_count || 0 }} {{ __('total') }}
          </span>
        </div>
        <div class="flex items-center gap-2 text-xs">
          <Button
            variant="outline"
            size="sm"
            class="rounded-xl !bg-white !border-slate-300 hover:!border-slate-400 text-slate-700 shadow-2xs font-semibold"
            :label="__('Previous')"
            :disabled="currentPage <= 1"
            @click="prevPage"
          />
          <span class="text-slate-700 font-bold px-1.5">{{ __('Page') }} {{ currentPage }}</span>
          <Button
            variant="outline"
            size="sm"
            class="rounded-xl !bg-white !border-slate-300 hover:!border-slate-400 text-slate-700 shadow-2xs font-semibold"
            :label="__('Next')"
            :disabled="!emailsData.has_more"
            @click="nextPage"
          />
        </div>
      </div>

      <!-- Loading Indicator -->
      <div v-if="emailsResource.loading" class="flex justify-center py-14">
        <LoadingIndicator class="size-7 text-[#d9531e]" />
      </div>

      <!-- Empty State -->
      <div
        v-else-if="!emailsData.emails?.length"
        class="text-center py-14 text-sm text-slate-500"
      >
        <LucideMail class="size-9 text-slate-300 mx-auto mb-2" />
        {{ __('No support emails found matching the current filters.') }}
      </div>

      <!-- Table Rows -->
      <div v-else class="overflow-x-auto">
        <table class="w-full text-xs text-left">
          <thead class="bg-slate-100/90 text-slate-700 uppercase tracking-wider font-extrabold border-b border-slate-300 text-[11px]">
            <tr>
              <th class="py-3 px-4">{{ __('Ticket / Subject') }}</th>
              <th class="py-3 px-4">{{ __('Sender') }}</th>
              <th class="py-3 px-4">{{ __('CGD Organization') }}</th>
              <th class="py-3 px-4">{{ __('Assigned Team') }}</th>
              <th class="py-3 px-4">{{ __('Assignee') }}</th>
              <th class="py-3 px-4">{{ __('Received Time') }}</th>
              <th class="py-3 px-4 text-center">{{ __('Status') }}</th>
              <th class="py-3 px-4 text-right">{{ __('Action') }}</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr
              v-for="em in emailsData.emails"
              :key="em.ticket_id"
              class="hover:bg-orange-50/25 transition-colors group"
            >
              <td class="py-3 px-4 max-w-xs">
                <div class="flex items-center gap-2 min-w-0">
                  <span
                    v-if="em.is_unread"
                    class="size-2 shrink-0 rounded-full bg-[#d9531e] ring-4 ring-orange-100"
                    :title="__('Unread')"
                  />
                  <span v-if="em.is_unread" class="sr-only">{{ __('Unread') }}</span>
                  <router-link
                    v-if="!authStore.isEmailUserOnly"
                    :to="`/tickets/${em.ticket_id}`"
                    class="text-slate-900 group-hover:text-[#d9531e] hover:underline truncate block font-bold"
                  >
                    {{ em.subject }}
                  </router-link>
                  <button
                    v-else
                    type="button"
                    class="text-left text-slate-900 group-hover:text-[#d9531e] hover:underline truncate block focus:outline-none font-bold"
                    :title="em.subject"
                    @click="openEmailDetail(em.ticket_id)"
                  >
                    {{ em.subject }}
                  </button>
                  <LucidePaperclip
                    v-if="em.has_attachments"
                    class="size-3.5 shrink-0 text-slate-400"
                    :aria-label="__('Has attachments')"
                  />
                </div>
                <span class="text-[11px] text-slate-400 truncate block font-mono mt-0.5">
                  #{{ em.ticket_id }} &bull; {{ em.original_message_id }}
                </span>
              </td>
              <td class="py-3 px-4 whitespace-nowrap text-slate-800">
                <div class="font-bold text-slate-900">{{ em.sender_name }}</div>
                <div class="text-[11px] text-slate-500 font-medium">{{ em.sender_email }}</div>
              </td>
              <td class="py-3 px-4 whitespace-nowrap">
                <div class="flex items-center gap-1.5">
                  <span
                    v-if="em.is_vip"
                    class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-amber-50 text-amber-900 border border-amber-300"
                  >
                    <LucideCrown class="size-3 text-amber-600" />
                    {{ em.cgd_name }}
                  </span>
                  <span
                    v-else
                    class="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-slate-100 text-slate-800 border border-slate-200"
                  >
                    {{ em.cgd_name }}
                  </span>
                </div>
              </td>
              <td class="py-3 px-4 whitespace-nowrap text-slate-800 font-semibold">
                {{ em.team_name }}
              </td>
              <td class="py-3 px-4 whitespace-nowrap text-slate-600 font-medium">
                {{ em.assignee_label }}
              </td>
              <td class="py-3 px-4 whitespace-nowrap text-slate-600">
                <div class="font-semibold text-slate-900">{{ em.received_date }}</div>
                <div class="text-[11px] text-slate-400">{{ em.received_time }}</div>
              </td>
              <td class="py-3 px-4 text-center whitespace-nowrap">
                <span
                  class="px-3 py-1 rounded-full text-[11px] font-bold border inline-flex items-center gap-1.5 shadow-2xs"
                  :class="getStatusBadgeClass(em.status)"
                >
                  <span class="size-1.5 rounded-full" :class="getStatusDotClass(em.status)" />
                  {{ em.status }}
                </span>
              </td>
              <td class="py-3 px-4 text-right whitespace-nowrap space-x-1.5">
                <Button
                  variant="outline"
                  size="sm"
                  class="rounded-xl !bg-white !border-slate-300 hover:!border-slate-400 text-slate-700 shadow-2xs font-semibold"
                  :label="__('View')"
                  @click="openEmailDetail(em.ticket_id)"
                />
                <Button
                  v-if="!authStore.isEmailUserOnly"
                  variant="subtle"
                  size="sm"
                  class="rounded-xl font-semibold"
                  :label="__('Reassign')"
                  @click="openReassignModal(em)"
                />
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Modals -->
    <SupportEmailDetail
      v-model="showEmailDetail"
      :ticket-id="selectedEmailTicket"
      @changed="emailsResource.reload()"
    />

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
import LucideAlertCircle from "~icons/lucide/alert-circle";
import LucideBuilding2 from "~icons/lucide/building-2";
import LucideCheckCircle2 from "~icons/lucide/check-circle-2";
import LucideChevronDown from "~icons/lucide/chevron-down";
import LucideClock from "~icons/lucide/clock";
import LucideCrown from "~icons/lucide/crown";
import LucideDownload from "~icons/lucide/download";
import LucideFileSpreadsheet from "~icons/lucide/file-spreadsheet";
import LucideInbox from "~icons/lucide/inbox";
import LucideMail from "~icons/lucide/mail";
import LucidePaperclip from "~icons/lucide/paperclip";
import LucideRefreshCw from "~icons/lucide/refresh-cw";
import LucideTrendingDown from "~icons/lucide/trending-down";
import LucideTrendingUp from "~icons/lucide/trending-up";
import LucideUserCheck from "~icons/lucide/user-check";
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

function getEmailPct(val?: number) {
  const total = summary.value.total_received?.value || 0;
  if (!total || !val) return "0.0";
  return ((val / total) * 100).toFixed(1);
}

function onEmailKpiClick(filterType: string) {
  if (filterType === "all") {
    filters.status = "";
    filters.readState = "";
  } else if (filterType === "unassigned") {
    filters.status = "Open";
  } else if (filterType === "assigned") {
    filters.status = "Pending";
  } else if (filterType === "in_progress") {
    filters.status = "Replied";
  } else if (filterType === "resolved") {
    filters.status = "Resolved";
  }
  reloadAnalytics();
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
      return "bg-gray-100 text-gray-700 border-gray-200";
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
      return "bg-gray-400";
  }
}
</script>
