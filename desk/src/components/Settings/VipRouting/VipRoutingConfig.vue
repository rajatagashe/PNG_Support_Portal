<template>
  <SettingsLayoutBase>
    <template #title>
      <div class="flex items-center gap-2">
        <h1 class="text-md-semibold text-ink-gray-8">
          {{ __("VIP & CGD Priority Routing") }}
        </h1>
      </div>
    </template>
    <template #description>
      <p class="text-p-sm max-w-md text-ink-gray-6">
        {{
          __(
            "Configure automatic priority escalation, dedicated escalation teams, fast-track SLAs, and senior agent assignment for key CGD entities."
          )
        }}
      </p>
    </template>
    <template #header-actions>
      <Button
        :label="__('New VIP Rule')"
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
          v-if="rulesResource.loading"
          class="flex items-center justify-center py-8"
        >
          <LoadingIndicator class="size-6 text-ink-gray-6" />
        </div>

        <!-- Empty State -->
        <div
          v-else-if="!rulesResource.data?.length"
          class="flex flex-col items-center justify-center py-16 text-center"
        >
          <div
            class="flex size-12 items-center justify-center rounded-full bg-surface-gray-2 text-ink-gray-6 mb-3"
          >
            <LucideCrown class="size-6 text-ink-gray-7" />
          </div>
          <p class="text-base-semibold text-ink-gray-8">
            {{ __("No VIP routing rules configured") }}
          </p>
          <p class="text-p-sm text-ink-gray-6 max-w-sm mt-1">
            {{
              __(
                "Add rules to automatically escalate tickets from high-priority accounts (such as GAIL, BPCL, or IGL) to Urgent priority and senior agents."
              )
            }}
          </p>
          <Button
            :label="__('Add VIP Rule')"
            variant="outline"
            class="mt-4"
            @click="openNewDialog"
          />
        </div>

        <!-- Rules Table -->
        <div v-else class="w-full">
          <div
            class="grid grid-cols-12 items-center gap-3 text-sm text-ink-gray-5 px-3 py-2 border-b border-outline-gray-2 font-medium"
          >
            <div class="col-span-3">{{ __("Rule Name") }}</div>
            <div class="col-span-3">{{ __("Target Entity / Domain") }}</div>
            <div class="col-span-2">{{ __("Priority") }}</div>
            <div class="col-span-2">{{ __("Escalation Team") }}</div>
            <div class="col-span-1 text-center">{{ __("Active") }}</div>
            <div class="col-span-1 text-right">{{ __("Actions") }}</div>
          </div>
          <div
            v-for="row in rulesResource.data"
            :key="row.name"
            class="grid grid-cols-12 items-center gap-3 px-3 py-3 border-b border-outline-gray-1 hover:bg-surface-gray-1 transition-colors"
          >
            <div class="col-span-3 font-medium text-ink-gray-9 truncate">
              {{ row.rule_name }}
              <span
                v-if="row.vip_tag"
                class="ml-1 inline-flex items-center px-1.5 py-0.5 rounded text-xs bg-surface-gray-2 text-ink-gray-8"
              >
                #{{ row.vip_tag }}
              </span>
            </div>
            <div class="col-span-3 text-ink-gray-7 truncate text-xs">
              <span v-if="row.customer" class="font-medium">{{ row.customer }}</span>
              <span v-if="row.customer && row.domain" class="text-ink-gray-4"> | </span>
              <span v-if="row.domain" class="font-mono text-ink-gray-6">@{{ row.domain }}</span>
            </div>
            <div class="col-span-2">
              <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-surface-gray-2 text-ink-gray-9">
                {{ row.escalate_priority || "Urgent" }}
              </span>
            </div>
            <div class="col-span-2 text-ink-gray-6 truncate text-xs">
              {{ row.escalate_team || __("Default Queue") }}
            </div>
            <div class="col-span-1 flex justify-center">
              <Switch
                :model-value="Boolean(row.is_active)"
                @update:modelValue="(val) => toggleActive(row, val)"
              />
            </div>
            <div class="col-span-1 flex items-center justify-end">
              <Button
                variant="ghost"
                size="sm"
                @click="deleteRule(row)"
              >
                <LucideTrash2 class="size-4 text-ink-gray-5 hover:text-ink-gray-9" />
              </Button>
            </div>
          </div>
        </div>
      </div>
    </template>
  </SettingsLayoutBase>

  <!-- Create VIP Rule Modal -->
  <Dialog
    v-model="showDialog"
    :options="{
      title: __('New VIP / CGD Priority Routing Rule'),
      size: 'md',
    }"
  >
    <template #body-content>
      <div class="space-y-4 py-2">
        <FormControl
          v-model="form.rule_name"
          :label="__('Rule Name')"
          :placeholder="__('e.g. GAIL Critical Operations')"
          required
        />
        <FormControl
          v-model="form.customer"
          type="select"
          :label="__('Target Customer / CGD Entity (Optional)')"
          :options="customerOptions"
        />
        <FormControl
          v-model="form.domain"
          :label="__('Email Domain Match (Optional)')"
          :placeholder="__('e.g. gail.co.in')"
        />
        <div class="grid grid-cols-2 gap-3">
          <FormControl
            v-model="form.escalate_priority"
            type="select"
            :label="__('Escalate Priority')"
            :options="[
              { label: __('Urgent'), value: 'Urgent' },
              { label: __('High'), value: 'High' },
              { label: __('Medium'), value: 'Medium' },
            ]"
          />
          <FormControl
            v-model="form.escalate_team"
            type="select"
            :label="__('Dedicated Team')"
            :options="teamOptions"
          />
        </div>
        <div class="grid grid-cols-2 gap-3">
          <FormControl
            v-model="form.escalate_sla"
            type="select"
            :label="__('Fast-Track SLA')"
            :options="slaOptions"
          />
          <FormControl
            v-model="form.vip_tag"
            :label="__('VIP Tag Badge')"
            :placeholder="__('vip-cgd')"
          />
        </div>
        <div class="flex items-center justify-between pt-2">
          <span class="text-sm text-ink-gray-7">{{ __("Require Senior Agent Assignment (Tier 2 / Lead)") }}</span>
          <Switch v-model="form.require_senior_agent" />
        </div>
        <div class="flex items-center justify-between pt-1">
          <span class="text-sm text-ink-gray-7">{{ __("Rule Active") }}</span>
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
          :disabled="!form.rule_name || (!form.customer && !form.domain)"
          @click="saveRule"
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
import LucideCrown from "~icons/lucide/crown";
import LucidePlus from "~icons/lucide/plus";
import LucideTrash2 from "~icons/lucide/trash-2";

const showDialog = ref(false);
const isSaving = ref(false);

const form = reactive({
  rule_name: "",
  customer: "",
  domain: "",
  escalate_priority: "Urgent",
  escalate_team: "",
  escalate_sla: "",
  vip_tag: "vip-cgd",
  require_senior_agent: false,
  is_active: true,
});

const rulesResource = createListResource({
  doctype: "HD VIP Routing Rule",
  fields: [
    "name",
    "rule_name",
    "customer",
    "domain",
    "escalate_priority",
    "escalate_team",
    "escalate_sla",
    "vip_tag",
    "require_senior_agent",
    "is_active",
  ],
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

const slasResource = createListResource({
  doctype: "HD Service Level Agreement",
  fields: ["name", "policy_name"],
  limit: 100,
  auto: true,
});

const customerOptions = computed(() => {
  const options = [{ label: __("Select Customer (or match by domain)"), value: "" }];
  if (customersResource.data) {
    customersResource.data.forEach((c: any) => {
      options.push({
        label: c.customer_name || c.name,
        value: c.name,
      });
    });
  }
  return options;
});

const teamOptions = computed(() => {
  const options = [{ label: __("None / Keep Standard Queue"), value: "" }];
  if (teamsResource.data) {
    teamsResource.data.forEach((t: any) => {
      options.push({
        label: t.team_name || t.name,
        value: t.name,
      });
    });
  }
  return options;
});

const slaOptions = computed(() => {
  const options = [{ label: __("None / Standard SLA"), value: "" }];
  if (slasResource.data) {
    slasResource.data.forEach((s: any) => {
      options.push({
        label: s.policy_name || s.name,
        value: s.name,
      });
    });
  }
  return options;
});

function openNewDialog() {
  form.rule_name = "";
  form.customer = "";
  form.domain = "";
  form.escalate_priority = "Urgent";
  form.escalate_team = "";
  form.escalate_sla = "";
  form.vip_tag = "vip-cgd";
  form.require_senior_agent = false;
  form.is_active = true;
  showDialog.value = true;
}

async function saveRule() {
  if (!form.rule_name || (!form.customer && !form.domain)) return;
  isSaving.value = true;
  try {
    await rulesResource.insert.submit({
      rule_name: form.rule_name.trim(),
      customer: form.customer || null,
      domain: form.domain.trim() || null,
      escalate_priority: form.escalate_priority,
      escalate_team: form.escalate_team || null,
      escalate_sla: form.escalate_sla || null,
      vip_tag: form.vip_tag.trim() || "vip-cgd",
      require_senior_agent: form.require_senior_agent ? 1 : 0,
      is_active: form.is_active ? 1 : 0,
    });
    toast({
      title: __("Success"),
      text: __("VIP routing rule created successfully"),
      icon: "check",
    });
    showDialog.value = false;
    rulesResource.reload();
  } catch (error: any) {
    toast({
      title: __("Error"),
      text: error.message || __("Failed to save VIP rule"),
      icon: "alert-circle",
    });
  } finally {
    isSaving.value = false;
  }
}

async function toggleActive(row: any, val: boolean) {
  try {
    await rulesResource.setValue.submit({
      name: row.name,
      is_active: val ? 1 : 0,
    });
    row.is_active = val ? 1 : 0;
  } catch (error: any) {
    toast({
      title: __("Error"),
      text: error.message || __("Failed to update status"),
      icon: "alert-circle",
    });
  }
}

async function deleteRule(row: any) {
  if (!confirm(__("Are you sure you want to delete this VIP rule?"))) return;
  try {
    await rulesResource.delete.submit(row.name);
    toast({
      title: __("Deleted"),
      text: __("VIP rule removed"),
      icon: "check",
    });
    rulesResource.reload();
  } catch (error: any) {
    toast({
      title: __("Error"),
      text: error.message || __("Failed to delete VIP rule"),
      icon: "alert-circle",
    });
  }
}
</script>
