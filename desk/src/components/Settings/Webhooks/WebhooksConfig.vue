<template>
  <SettingsLayoutBase>
    <template #title>
      <div class="flex items-center gap-2">
        <h1 class="text-md-semibold text-ink-gray-8">
          {{ __("Outgoing Webhooks") }}
        </h1>
      </div>
    </template>
    <template #description>
      <p class="text-p-sm max-w-md text-ink-gray-6">
        {{
          __(
            "Broadcast real-time ticket events to external endpoints, SIEMs, or Slack/Teams with HMAC SHA-256 verification."
          )
        }}
      </p>
    </template>
    <template #header-actions>
      <Button
        :label="__('New Webhook')"
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
          v-if="webhooksResource.loading"
          class="flex items-center justify-center py-8"
        >
          <LoadingIndicator class="size-6 text-ink-gray-6" />
        </div>

        <!-- Empty State -->
        <div
          v-else-if="!webhooksResource.data?.length"
          class="flex flex-col items-center justify-center py-16 text-center"
        >
          <div
            class="flex size-12 items-center justify-center rounded-full bg-surface-gray-2 text-ink-gray-6 mb-3"
          >
            <LucideWebhook class="size-6" />
          </div>
          <p class="text-base-semibold text-ink-gray-8">
            {{ __("No outgoing webhooks configured") }}
          </p>
          <p class="text-p-sm text-ink-gray-6 max-w-sm mt-1">
            {{
              __(
                "Configure webhooks to dispatch ticket events to Slack, Microsoft Teams, incident management, or custom HTTP endpoints."
              )
            }}
          </p>
          <Button
            :label="__('Add Webhook')"
            variant="outline"
            class="mt-4"
            @click="openNewDialog"
          />
        </div>

        <!-- Webhooks Table -->
        <div v-else class="w-full">
          <div
            class="grid grid-cols-12 items-center gap-3 text-sm text-ink-gray-5 px-3 py-2 border-b border-outline-gray-2 font-medium"
          >
            <div class="col-span-3">{{ __("Webhook Name") }}</div>
            <div class="col-span-4">{{ __("Target URL") }}</div>
            <div class="col-span-2">{{ __("Event Trigger") }}</div>
            <div class="col-span-1 text-center">{{ __("Active") }}</div>
            <div class="col-span-2 text-right">{{ __("Actions") }}</div>
          </div>
          <div
            v-for="row in webhooksResource.data"
            :key="row.name"
            class="grid grid-cols-12 items-center gap-3 px-3 py-3 border-b border-outline-gray-1 hover:bg-surface-gray-1 transition-colors"
          >
            <div class="col-span-3 font-medium text-ink-gray-9 truncate">
              {{ row.webhook_name }}
              <span
                v-if="row.cgd_filter"
                class="ml-1 inline-flex items-center px-1.5 py-0.5 rounded text-xs bg-surface-gray-2 text-ink-gray-7"
              >
                {{ row.cgd_filter }}
              </span>
            </div>
            <div
              class="col-span-4 text-ink-gray-7 truncate text-xs font-mono"
              :title="row.target_url"
            >
              {{ row.target_url }}
            </div>
            <div class="col-span-2 text-ink-gray-6 truncate text-xs">
              {{ row.events || "All" }}
            </div>
            <div class="col-span-1 flex justify-center">
              <Switch
                :model-value="Boolean(row.is_active)"
                @update:modelValue="(val) => toggleActive(row, val)"
              />
            </div>
            <div class="col-span-2 flex items-center justify-end gap-2">
              <Button
                variant="ghost"
                size="sm"
                :label="__('Logs')"
                @click="openLogs(row)"
              >
                <template #prefix>
                  <LucideActivity class="size-3.5 text-ink-gray-6" />
                </template>
              </Button>
              <Button
                variant="ghost"
                size="sm"
                @click="deleteWebhook(row)"
              >
                <LucideTrash2 class="size-4 text-ink-gray-5 hover:text-ink-gray-9" />
              </Button>
            </div>
          </div>
        </div>
      </div>
    </template>
  </SettingsLayoutBase>

  <!-- Create Webhook Modal -->
  <Dialog
    v-model="showDialog"
    :options="{
      title: __('New Outgoing Webhook'),
      size: 'md',
    }"
  >
    <template #body-content>
      <div class="space-y-4 py-2">
        <FormControl
          v-model="form.webhook_name"
          :label="__('Webhook Name')"
          :placeholder="__('e.g. Incident Escalation Slack')"
          required
        />
        <FormControl
          v-model="form.target_url"
          :label="__('Target URL')"
          :placeholder="__('https://hooks.slack.com/services/...')"
          required
        />
        <FormControl
          v-model="form.events"
          type="select"
          :label="__('Event Trigger')"
          :options="[
            { label: __('All Ticket Events'), value: 'All' },
            { label: __('On Ticket Creation'), value: 'On Ticket Creation' },
            { label: __('On Ticket Update'), value: 'On Ticket Update' },
            { label: __('On Ticket Resolution'), value: 'On Ticket Resolution' },
          ]"
        />
        <FormControl
          v-model="form.cgd_filter"
          type="select"
          :label="__('CGD / Customer Isolation Filter (Optional)')"
          :options="customerOptions"
        />
        <FormControl
          v-model="form.secret_key"
          :label="__('HMAC SHA-256 Secret Key (Optional)')"
          :placeholder="__('Enter shared secret for signature verification')"
        />
        <div class="flex items-center justify-between pt-2">
          <span class="text-sm text-ink-gray-7">{{ __("Enable Immediately") }}</span>
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
          :disabled="!form.webhook_name || !form.target_url"
          @click="saveWebhook"
        />
      </div>
    </template>
  </Dialog>

  <!-- Webhook Delivery Logs Modal -->
  <Dialog
    v-model="showLogsDialog"
    :options="{
      title: `${__('Delivery Logs')}: ${selectedWebhook?.webhook_name || ''}`,
      size: 'xl',
    }"
  >
    <template #body-content>
      <div class="py-2">
        <div v-if="logsResource.loading" class="flex justify-center py-6">
          <LoadingIndicator class="size-6 text-ink-gray-6" />
        </div>
        <div
          v-else-if="!logsResource.data?.length"
          class="text-center py-8 text-sm text-ink-gray-5"
        >
          {{ __("No delivery logs recorded for this webhook yet.") }}
        </div>
        <div v-else class="space-y-2 max-h-96 overflow-y-auto">
          <div
            v-for="log in logsResource.data"
            :key="log.name"
            class="p-3 rounded-lg border border-outline-gray-2 text-xs font-mono space-y-1 bg-surface-gray-1"
          >
            <div class="flex items-center justify-between">
              <span class="font-semibold text-ink-gray-8">
                {{ log.event }} | {{ log.ticket || "N/A" }}
              </span>
              <span
                :class="
                  log.status_code >= 200 && log.status_code < 300
                    ? 'text-ink-gray-9 font-bold bg-surface-gray-2 px-1.5 py-0.5 rounded'
                    : 'text-ink-gray-7 font-bold bg-surface-gray-3 px-1.5 py-0.5 rounded'
                "
              >
                HTTP {{ log.status_code }} ({{ log.execution_time_ms }}ms)
              </span>
            </div>
            <div class="text-ink-gray-6 truncate">
              {{ log.created_at || log.creation }}
            </div>
            <div
              v-if="log.response_body"
              class="text-ink-gray-7 truncate bg-surface-white p-1 rounded border border-outline-gray-1"
            >
              {{ log.response_body }}
            </div>
          </div>
        </div>
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
import LucideActivity from "~icons/lucide/activity";
import LucidePlus from "~icons/lucide/plus";
import LucideTrash2 from "~icons/lucide/trash-2";
import LucideWebhook from "~icons/lucide/webhook";

const showDialog = ref(false);
const showLogsDialog = ref(false);
const isSaving = ref(false);
const selectedWebhook = ref<any>(null);

const form = reactive({
  webhook_name: "",
  target_url: "",
  events: "All",
  cgd_filter: "",
  secret_key: "",
  is_active: true,
});

const webhooksResource = createListResource({
  doctype: "HD Webhook",
  fields: ["name", "webhook_name", "target_url", "events", "cgd_filter", "is_active"],
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

const logsResource = createListResource({
  doctype: "HD Webhook Log",
  fields: ["name", "webhook", "ticket", "event", "status_code", "execution_time_ms", "response_body", "creation"],
  orderBy: "creation desc",
  limit: 30,
  auto: false,
});

const customerOptions = computed(() => {
  const options = [{ label: __("All CGD Entities (Global)"), value: "" }];
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

function openNewDialog() {
  form.webhook_name = "";
  form.target_url = "";
  form.events = "All";
  form.cgd_filter = "";
  form.secret_key = "";
  form.is_active = true;
  showDialog.value = true;
}

function openLogs(row: any) {
  selectedWebhook.value = row;
  logsResource.update({
    filters: { webhook: row.name },
  });
  logsResource.reload();
  showLogsDialog.value = true;
}

async function saveWebhook() {
  if (!form.webhook_name || !form.target_url) return;
  isSaving.value = true;
  try {
    await webhooksResource.insert.submit({
      webhook_name: form.webhook_name.trim(),
      target_url: form.target_url.trim(),
      events: form.events,
      cgd_filter: form.cgd_filter || null,
      secret_key: form.secret_key.trim() || null,
      is_active: form.is_active ? 1 : 0,
    });
    toast({
      title: __("Success"),
      text: __("Outgoing webhook created successfully"),
      icon: "check",
    });
    showDialog.value = false;
    webhooksResource.reload();
  } catch (error: any) {
    toast({
      title: __("Error"),
      text: error.message || __("Failed to save webhook"),
      icon: "alert-circle",
    });
  } finally {
    isSaving.value = false;
  }
}

async function toggleActive(row: any, val: boolean) {
  try {
    await webhooksResource.setValue.submit({
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

async function deleteWebhook(row: any) {
  if (!confirm(__("Are you sure you want to delete this webhook?"))) return;
  try {
    await webhooksResource.delete.submit(row.name);
    toast({
      title: __("Deleted"),
      text: __("Webhook removed"),
      icon: "check",
    });
    webhooksResource.reload();
  } catch (error: any) {
    toast({
      title: __("Error"),
      text: error.message || __("Failed to delete webhook"),
      icon: "alert-circle",
    });
  }
}
</script>
