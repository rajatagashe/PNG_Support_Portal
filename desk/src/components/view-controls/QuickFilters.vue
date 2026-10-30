<template>
  <div class="flex items-center gap-2 flex-1 min-w-0" v-if="!quickFilters.loading && quickFilters.data?.length">
    <div class="flex items-center gap-1.5 text-xs font-semibold text-slate-500 uppercase tracking-wider shrink-0 ps-1">
      <LucideListFilter class="size-4 text-slate-400" />
      <span>{{ __('Filters') }}:</span>
    </div>
    <FadedScrollableDiv
      class="quick-filters flex flex-1 items-center overflow-x-auto py-1 gap-2 pe-2 ps-0.5"
      orientation="horizontal"
    >
      <div
        v-for="filter in quickFilters.data"
        :key="filter.name"
        class="min-w-36 shrink-0"
      >
        <QuickFilterField
          :filter="filter"
          :value="getValue(filter, list.params?.filters)"
          @applyQuickFilter="(f, v) => applyQuickFilter(f, v)"
        />
      </div>
    </FadedScrollableDiv>
  </div>
</template>

<script setup>
import { FadedScrollableDiv } from "@/components";
import { __ } from "@/translation";
import { inject } from "vue";
import LucideListFilter from "~icons/lucide/list-filter";
import { normalizeFilters } from "./filter";
import QuickFilterField from "./QuickFilterField.vue";

const listViewData = inject("listViewData");
const listViewActions = inject("listViewActions");
const { list, quickFilters } = listViewData;

const directValueFilterTypes = ["Check", "Select", "Link", "Date", "Datetime"];

function applyQuickFilter(filter, value) {
  const conditions = normalizeFilters(list.params?.filters).filter(
    (condition) => condition[0] !== filter.name
  );
  if (value) {
    if (directValueFilterTypes.includes(filter.type)) {
      conditions.push([filter.name, "=", value]);
    } else {
      conditions.push([filter.name, "LIKE", `%${value}%`]);
    }
  }
  listViewActions.applyFilters(conditions);
}

function getDefaultValue(quickFilter) {
  return quickFilter.type === "Check" ? false : "";
}

function getValue(quickFilter, filters) {
  if (!(quickFilter && quickFilter.name)) {
    return getDefaultValue(quickFilter);
  }
  const condition = normalizeFilters(filters).find(
    (c) => c[0] === quickFilter.name
  );
  if (!condition) {
    return getDefaultValue(quickFilter);
  }
  const [, operator, value] = condition;
  if (directValueFilterTypes.includes(quickFilter.type)) {
    return operator === "=" ? value : getDefaultValue(quickFilter);
  }
  if (String(operator).toLowerCase() !== "like" || typeof value !== "string") {
    return getDefaultValue(quickFilter);
  }
  return value.replaceAll("%", "");
}
</script>

<style scoped>
.quick-filters {
  scrollbar-width: none; /* Firefox */
  -ms-overflow-style: none; /* IE/Edge */
}
.quick-filters::-webkit-scrollbar {
  display: none; /* Chrome/Safari */
}
</style>
