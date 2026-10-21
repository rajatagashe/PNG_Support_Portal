<template>
  <SettingsLayoutBase>
    <template #title>
      <div class="flex items-center gap-2">
        <h1 class="text-md-semibold text-ink-gray-8">
          {{ __("Customer Approvals") }}
        </h1>
        <Badge
          v-if="pendingRequests.length"
          variant="solid"
          theme="gray"
          size="sm"
        >
          {{ pendingRequests.length }}
        </Badge>
      </div>
    </template>
    <template #description>
      <p class="text-p-sm max-w-md text-ink-gray-6">
        {{
          __(
            "Review, approve, and activate self-registration requests from customer organization representatives."
          )
        }}
      </p>
    </template>
    <template #header-actions>
      <Button
        :label="__('Refresh')"
        variant="ghost"
        @click="requestsResource.reload"
      >
        <template #prefix>
          <LucideRotateCcw class="size-4" />
        </template>
      </Button>
    </template>
    <template #content>
      <div class="grow">
        <!-- Loading State -->
        <div
          v-if="requestsResource.loading"
          class="flex items-center justify-center py-8"
        >
          <LoadingIndicator class="size-6 text-ink-gray-6" />
        </div>

        <!-- Empty State -->
        <div
          v-else-if="!pendingRequests.length"
          class="flex flex-col items-center justify-center py-16 text-center"
        >
          <div
            class="flex size-12 items-center justify-center rounded-full bg-surface-gray-2 text-ink-gray-6 mb-3"
          >
            <LucideUserCheck class="size-6" />
          </div>
          <p class="text-base-semibold text-ink-gray-8">
            {{ __("No pending signup requests") }}
          </p>
          <p class="text-p-sm text-ink-gray-6 max-w-sm mt-1">
            {{
              __(
                "All customer portal registration requests have been reviewed and processed."
              )
            }}
          </p>
        </div>

        <!-- Requests Table -->
        <div v-else class="w-full">
          <div
            class="grid grid-cols-12 items-center gap-3 text-sm text-ink-gray-5 px-3 py-2 border-b border-outline-gray-2 font-medium"
          >
            <div class="col-span-3">{{ __("Applicant") }}</div>
            <div class="col-span-3">{{ __("Email") }}</div>
            <div class="col-span-3">{{ __("Requested Entity") }}</div>
            <div class="col-span-3 text-right">{{ __("Actions") }}</div>
          </div>
          <div
            v-for="row in pendingRequests"
            :key="row.name"
            class="grid grid-cols-12 items-center gap-3 px-3 py-3 border-b border-outline-gray-1 hover:bg-surface-gray-1 transition-colors"
          >
            <div class="col-span-3 min-w-0">
              <p class="font-medium text-ink-gray-9 truncate">{{ row.full_name }}</p>
              <p class="text-xs text-ink-gray-5 truncate">{{ row.designation || "-" }}</p>
            </div>
            <div class="col-span-3 text-ink-gray-7 truncate">
              {{ row.email }}
            </div>
            <div class="col-span-3 text-ink-gray-7 truncate">
              {{ row.requested_cgd || "-" }}
            </div>
            <div class="col-span-3 flex justify-end gap-2">
              <Button
                variant="outline"
                size="sm"
                :label="__('Reject')"
                @click="openRejectDialog(row)"
              />
              <Button
                variant="solid"
                size="sm"
                :label="__('Approve')"
                @click="openApproveDialog(row)"
              />
            </div>
          </div>
        </div>
      </div>
    </template>
  </SettingsLayoutBase>

  <!-- Approve Request Dialog -->
  <Dialog
    v-model:open="showApproveDialog"
    :title="__('Approve Registration Request')"
  >
    <template #default>
      <div v-if="selectedRequest" class="flex flex-col gap-4 py-2">
        <div class="bg-surface-gray-2 p-3 rounded-lg text-sm flex flex-col gap-1">
          <div>
            <span class="font-medium text-ink-gray-8">{{ __('Applicant') }}:</span>
            <span class="text-ink-gray-7 ml-1">{{ selectedRequest.full_name }} ({{ selectedRequest.email }})</span>
          </div>
          <div v-if="selectedRequest.designation">
            <span class="font-medium text-ink-gray-8">{{ __('Designation') }}:</span>
            <span class="text-ink-gray-7 ml-1">{{ selectedRequest.designation }}</span>
          </div>
        </div>

        <FormControl
          type="select"
          v-model="approveForm.customer"
          :label="__('Assign to Customer Entity')"
          :options="customerOptions"
          :placeholder="__('Select Customer')"
          required
        />

        <FormControl
          type="select"
          v-model="approveForm.role"
          :label="__('Portal Permission Role')"
          :options="roleOptions"
          required
        />
      </div>
    </template>
    <template #actions>
      <div class="flex justify-end gap-2">
        <Button
          variant="subtle"
          :label="__('Cancel')"
          @click="showApproveDialog = false"
        />
        <Button
          variant="solid"
          :label="__('Confirm Approval')"
          :loading="approveResource.loading"
          :disabled="!approveForm.customer"
          @click="submitApproval"
        />
      </div>
    </template>
  </Dialog>

  <!-- Reject Request Dialog -->
  <Dialog
    v-model:open="showRejectDialog"
    :title="__('Reject Registration Request')"
  >
    <template #default>
      <div v-if="selectedRequest" class="flex flex-col gap-4 py-2">
        <p class="text-p-sm text-ink-gray-7">
          {{
            __(
              "Are you sure you want to decline registration for {0}? You can optionally specify a reason for records.",
              [selectedRequest.full_name]
            )
          }}
        </p>
        <FormControl
          type="textarea"
          v-model="rejectReason"
          :label="__('Reason for Rejection')"
          :placeholder="__('e.g. Not an authorized representative')"
        />
      </div>
    </template>
    <template #actions>
      <div class="flex justify-end gap-2">
        <Button
          variant="subtle"
          :label="__('Cancel')"
          @click="showRejectDialog = false"
        />
        <Button
          theme="red"
          variant="solid"
          :label="__('Reject Request')"
          :loading="rejectResource.loading"
          @click="submitRejection"
        />
      </div>
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import SettingsLayoutBase from "@/components/layouts/SettingsLayoutBase.vue";
import { __ } from "@/translation";
import {
  Badge,
  Button,
  Dialog,
  FormControl,
  LoadingIndicator,
  createListResource,
  createResource,
  toast,
} from "frappe-ui";
import { computed, reactive, ref } from "vue";
import LucideRotateCcw from "~icons/lucide/rotate-ccw";
import LucideUserCheck from "~icons/lucide/user-check";

const selectedRequest = ref<any>(null);
const showApproveDialog = ref(false);
const showRejectDialog = ref(false);
const rejectReason = ref("");

const approveForm = reactive({
  customer: "",
  role: "HD Customer",
});

const roleOptions = [
  { label: __("Customer Member (HD Customer)"), value: "HD Customer" },
  { label: __("Customer Manager (HD Customer Manager)"), value: "HD Customer Manager" },
];

const requestsResource = createListResource({
  doctype: "HD Customer Signup Request",
  fields: [
    "name",
    "email",
    "full_name",
    "phone",
    "requested_cgd",
    "designation",
    "status",
    "creation",
  ],
  filters: {
    status: "Pending",
  },
  orderBy: "creation asc",
  limit: 100,
  auto: true,
});

const customersResource = createListResource({
  doctype: "HD Customer",
  fields: ["name", "customer_name"],
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

const pendingRequests = computed(() => requestsResource.data || []);

const approveResource = createResource({
  url: "helpdesk.api.customer_signup.approve_signup_request",
  onSuccess() {
    toast({
      title: __("Customer registration approved and user activated"),
      appearance: "success",
    });
    showApproveDialog.value = false;
    requestsResource.reload();
  },
  onError(err: any) {
    toast({
      title: err.message || __("Failed to approve request"),
      appearance: "error",
    });
  },
});

const rejectResource = createResource({
  url: "helpdesk.api.customer_signup.reject_signup_request",
  onSuccess() {
    toast({
      title: __("Signup request declined"),
      appearance: "success",
    });
    showRejectDialog.value = false;
    requestsResource.reload();
  },
  onError(err: any) {
    toast({
      title: err.message || __("Failed to reject request"),
      appearance: "error",
    });
  },
});

function openApproveDialog(row: any) {
  selectedRequest.value = row;
  approveForm.customer = row.requested_cgd || customerOptions.value[0]?.value || "";
  approveForm.role = "HD Customer";
  showApproveDialog.value = true;
}

function openRejectDialog(row: any) {
  selectedRequest.value = row;
  rejectReason.value = "";
  showRejectDialog.value = true;
}

function submitApproval() {
  if (!selectedRequest.value) return;
  approveResource.submit({
    request_id: selectedRequest.value.name,
    customer: approveForm.customer,
    role: approveForm.role,
  });
}

function submitRejection() {
  if (!selectedRequest.value) return;
  rejectResource.submit({
    request_id: selectedRequest.value.name,
    reason: rejectReason.value || undefined,
  });
}
</script>
