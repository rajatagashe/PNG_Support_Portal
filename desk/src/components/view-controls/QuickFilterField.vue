<template>
  <FormControl
    v-if="filter.type == 'Check'"
    :label="filter.label"
    type="checkbox"
    :checked="props.value"
    @change.stop="updateFilter(filter, $event.target.checked)"
    class="!min-w-36 max-w-44 text-slate-800 font-medium"
  />
  <FormControl
    v-else-if="filter.type === 'Select'"
    :class="[
      'form-control cursor-pointer [&_select]:cursor-pointer !min-w-36 max-w-44 text-sm font-medium rounded-lg shadow-2xs transition-all',
      isActive
        ? '[&_select]:!bg-orange-50/50 [&_select]:!border-2 [&_select]:!border-[#d9531e] [&_select]:!text-slate-900 [&_select]:!font-bold [&_select]:shadow-xs'
        : '[&_select]:bg-white [&_select]:border [&_select]:border-slate-300 [&_select]:text-slate-800 hover:[&_select]:border-slate-400 focus-within:[&_select]:border-[#d9531e] focus-within:[&_select]:ring-1 focus-within:[&_select]:ring-[#d9531e]',
    ]"
    type="select"
    :model-value="props.value || undefined"
    :options="filter.options"
    :placeholder="filter.label"
    @update:modelValue="(v) => updateFilter(filter, v || '')"
  />
  <Link
    v-else-if="filter.type === 'Link'"
    :model-value="props.value"
    :doctype="filter.options"
    :placeholder="filter.label"
    :title="props.value ? String(props.value) : undefined"
    variant="outline"
    :class="[
      '!min-w-36 max-w-44 text-sm font-medium rounded-lg shadow-2xs transition-all',
      isActive
        ? '!bg-orange-50/50 !border-2 !border-[#d9531e] !text-slate-900 !font-bold shadow-xs'
        : 'bg-white border border-slate-300 text-slate-800 hover:border-slate-400 focus-within:border-[#d9531e] focus-within:ring-1 focus-within:ring-[#d9531e]',
    ]"
    @update:model-value="(value) => updateFilter(filter, value ?? '')"
  />
  <component
    v-else-if="['Date', 'Datetime'].includes(filter.type)"
    :class="[
      '!min-w-36 max-w-44 text-sm font-medium rounded-lg shadow-2xs transition-all',
      isActive
        ? '!bg-orange-50/50 !border-2 !border-[#d9531e] !text-slate-900 !font-bold shadow-xs'
        : 'bg-white border border-slate-300 text-slate-800 hover:border-slate-400 focus-within:border-[#d9531e] focus-within:ring-1 focus-within:ring-[#d9531e]',
    ]"
    :is="filter.type === 'Date' ? DatePicker : DateTimePicker"
    variant="outline"
    :model-value="props.value"
    @change="(v) => updateFilter(filter, v)"
    :placeholder="filter.label"
  />
  <TextInput
    v-else
    :value="props.value"
    type="text"
    variant="outline"
    :placeholder="filter.label"
    @input.stop="debouncedFn(filter, $event.target.value)"
    :class="[
      '!min-w-36 max-w-44 text-sm font-medium rounded-lg shadow-2xs transition-all',
      isActive
        ? '!bg-orange-50/50 !border-2 !border-[#d9531e] !text-slate-900 !font-bold shadow-xs'
        : 'bg-white border border-slate-300 text-slate-800 hover:border-slate-400 focus-within:border-[#d9531e] focus-within:ring-1 focus-within:ring-[#d9531e]',
    ]"
  />
</template>
<script setup>
import { Link } from "@framework/ui";
import { useDebounceFn } from "@vueuse/core";
import { DatePicker, DateTimePicker, FormControl, TextInput } from "frappe-ui";
import { computed } from "vue";

const props = defineProps({
  filter: {
    type: Object,
    required: true,
  },
  value: {
    type: [String, Boolean],
    required: true,
  },
});

const isActive = computed(() => {
  if (typeof props.value === "boolean") return props.value;
  return Boolean(props.value && String(props.value).trim().length > 0);
});

const emit = defineEmits(["applyQuickFilter"]);

const debouncedFn = useDebounceFn((f, value) => {
  emit("applyQuickFilter", f, value);
}, 500);

function updateFilter(f, value) {
  emit("applyQuickFilter", f, value);
}
</script>
