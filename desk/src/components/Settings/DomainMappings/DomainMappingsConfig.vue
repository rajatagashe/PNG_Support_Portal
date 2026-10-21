<template>
  <SettingsLayoutBase>
    <template #title>
      <div class="flex items-center gap-2">
        <h1 class="text-md-semibold text-ink-gray-8">
          {{ __("Domain Mappings") }}
        </h1>
      </div>
    </template>
    <template #description>
      <p class="text-p-sm max-w-md text-ink-gray-6">
        {{
          __(
            "Automatically map incoming tickets to customer entities and triage teams based on sender email domain."
          )
        }}
      </p>
    </template>
    <template #header-actions>
      <Button
        :label="__('New Mapping')"
        theme="gray"
        variant="solid"
        @click="openNewDialog"
        class="rtl:flex-row-reverse"
      >
        <template #prefix>
          <LucidePlus class="size-4" />
        </template>
      </Button>
    </template>
    <template #content>
      <div class="grow">
        <!-- Loading State -->
        <div
          v-if="mappingsResource.loading"
          class="flex items-center justify-center py-8"
        >
          <LoadingIndicator class="size-6 text-ink-gray-6" />
        </div>

        <!-- Empty State -->
        <div
          v-else-if="!mappingsResource.data?.length"
          class="flex flex-col items-center justify-center py-16 text-center"
        >
          <div
            class="flex size-12 items-center justify-center rounded-full bg-surface-gray-2 text-ink-gray-6 mb-3"
          >
            <LucideGlobe class="size-6" />
          </div>
          <p class="text-base-semibold text-ink-gray-8">
            {{ __("No domain mappings found") }}
          </p>
          <p class="text-p-sm text-ink-gray-6 max-w-sm mt-1">
            {{
              __(
                "Add email domains (e.g. bpcl.in) to automatically associate incoming emails with corresponding customer entities."
              )
            }}
          </p>
          <Button
            :label="__('Add Domain Mapping')"
            variant="outline"
            class="mt-4"
            @click="openNewDialog"
          />
        </div>

        <!-- Mappings Table -->
        <div v-else class="w-full">
          <div
            class="grid grid-cols-12 items-center gap-3 text-sm text-ink-gray-5 px-3 py-2 border-b border-outline-gray-2 font-medium"
          >
            <div class="col-span-3">{{ __("Domain") }}</div>
            <div class="col-span-4">{{ __("Customer") }}</div>
            <div class="col-span-3">{{ __("Default Team") }}</div>
            <div class="col-span-1 text-center">{{ __("Active") }}</div>
            <div class="col-span-1 text-right">{{ __("Actions") }}</div>
          </div>
          <div
            v-for="row in mappingsResource.data"
            :key="row.name"
            class="grid grid-cols-12 items-center gap-3 px-3 py-3 border-b border-outline-gray-1 hover:bg-surface-gray-1 transition-colors"
          >
            <div class="col-span-3 font-medium text-ink-gray-9 truncate">
              @{{ row.domain }}
            </div>
            <div class="col-span-4 text-ink-gray-7 truncate">
              {{ row.customer }}
            </div>
            <div class="col-span-3 text-ink-gray-6 truncate">
              {{ row.default_team || "-" }}
            </div>
            <div class="col-span-1 flex justify-center">
              <Switch
                :model-value="Boolean(row.is_active)"
                @update:modelValue="(val) => toggleActive(row, val)"
              />
            </div>
            <div class="col-span-1 flex justify-end">
              <Button
                variant="ghost"
                @click="deleteMapping(row)"
                class="hover:text-ink-red-3"
              >
                <template #icon>
                  <LucideTrash2 class="size-4 text-ink-gray-5" />
                </template>
              </Button>
            </div>
          </div>
        </div>
      </div>
    </template>
  </SettingsLayoutBase>

  <!-- Add Domain Mapping Dialog -->
  <Dialog
    v-model:open="showDialog"
    :title="__('Add Domain Mapping')"
  >
    <template #default>
      <div class="flex flex-col gap-4 py-2">
        <FormControl
          type="text"
          v-model="form.domain"
          :label="__('Domain Name')"
          :placeholder="__('e.g. bpcl.in')"
          :description="__('Sender email domain (without @).')"
          required
        />
        <FormControl
          type="select"
          v-model="form.customer"
          :label="__('Target Customer')"
          :options="customerOptions"
          :placeholder="__('Select Customer')"
          required
        />
        <FormControl
          type="select"
          v-model="form.default_team"
          :label="__('Default Team (Optional)')"
          :options="teamOptions"
          :placeholder="__('Select Team')"
        />
        <div class="flex items-center justify-between pt-2">
          <span class="text-sm text-ink-gray-7">{{ __("Enable Mapping") }}</span>
          <Switch v-model="form.is_active" />
        </div>
      </div>
    </template>
    <template #actions>
      <div class="flex justify-end gap-2">
        <Button
          variant="subtle"
          :label="__('Cancel')"
          @click="showDialog = false"
        />
        <Button
          variant="solid"
          :label="__('Save')"
          :loading="isSaving"
          :disabled="!form.domain || !form.customer"
          @click="saveMapping"
        />
      </div>
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import SettingsLayoutBase from "@/components/layouts/SettingsLayoutBase.vue";
import { __ } from "@/translation";
import {
  Button,
  Dialog,
  FormControl,
  LoadingIndicator,
  Switch,
  createListResource,
  toast,
} from "frappe-ui";
import { computed, reactive, ref } from "vue";
import LucideGlobe from "~icons/lucide/globe";
import LucidePlus from "~icons/lucide/plus";
import LucideTrash2 from "~icons/lucide/trash-2";

const showDialog = ref(false);
const isSaving = ref(false);

const form = reactive({
  domain: "",
  customer: "",
  default_team: "",
  is_active: true,
});

const mappingsResource = createListResource({
  doctype: "HD Domain Mapping",
  fields: ["name", "domain", "customer", "default_team", "is_active"],
  orderBy: "modified desc",
  limit: 100,
  auto: true,
});

const customersResource = createListResource({
  doctype: "HD Customer",
  fields: ["name", "customer_name"],
  limit: 200,
  auto: true,
});

const teamsResource = createListResource({
  doctype: "HD Team",
  fields: ["name", "team_name"],
  limit: 200,
  auto: true,
});

const customerOptions = computed(() => {
  if (!customersResource.data) return [];
  return customersResource.data.map((c: any) => ({
    label: c.customer_name || c.name,
    value: c.name,
  }));
});

const teamOptions = computed(() => {
  if (!teamsResource.data) return [{ label: __("None"), value: "" }];
  return [
    { label: __("None"), value: "" },
    ...teamsResource.data.map((t: any) => ({
      label: t.team_name || t.name,
      value: t.name,
    })),
  ];
});

function openNewDialog() {
  form.domain = "";
  form.customer = customerOptions.value[0]?.value || "";
  form.default_team = "";
  form.is_active = true;
  showDialog.value = true;
}

async function saveMapping() {
  if (!form.domain || !form.customer) return;
  isSaving.value = true;
  try {
    await mappingsResource.insert.submit({
      domain: form.domain.trim().toLowerCase().replace(/^@/, ""),
      customer: form.customer,
      default_team: form.default_team || undefined,
      is_active: form.is_active ? 1 : 0,
    });
    toast({
      title: __("Domain mapping saved"),
      appearance: "success",
    });
    showDialog.value = false;
    mappingsResource.reload();
  } catch (error: any) {
    toast({
      title: error.message || __("Failed to save domain mapping"),
      appearance: "error",
    });
  } finally {
    isSaving.value = false;
  }
}

async function toggleActive(row: any, val: boolean) {
  try {
    await mappingsResource.setValue.submit({
      name: row.name,
      is_active: val ? 1 : 0,
    });
    row.is_active = val ? 1 : 0;
  } catch (err: any) {
    toast({
      title: err.message || __("Error toggling active status"),
      appearance: "error",
    });
  }
}

async function deleteMapping(row: any) {
  if (!confirm(__("Are you sure you want to remove domain mapping for {0}?", [`@${row.domain}`]))) {
    return;
  }
  try {
    await mappingsResource.delete.submit(row.name);
    toast({
      title: __("Domain mapping removed"),
      appearance: "success",
    });
    mappingsResource.reload();
  } catch (err: any) {
    toast({
      title: err.message || __("Error deleting domain mapping"),
      appearance: "error",
    });
  }
}
</script>
