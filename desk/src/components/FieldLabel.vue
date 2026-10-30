<template>
  <div class="w-[106px] shrink-0 truncate text-sm font-semibold text-slate-700">
    <Tooltip :text="__(label)">
      <span>{{ __(label) }}</span>
    </Tooltip>
    <span v-if="required" class="text-rose-600 font-bold"> * </span>
  </div>
</template>

<script setup lang="ts">
import { Tooltip } from "frappe-ui";

defineProps<{
  label: string;
  // Frappe fields carry 1 / 0, not true / false
  required?: boolean | number;
}>();
</script>
