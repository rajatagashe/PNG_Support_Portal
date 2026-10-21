<template>
  <div class="flex w-[382px] flex-col border-s gap-4">
    <!-- Ticket Header -->
    <div class="flex items-center justify-between border-b px-5 py-3">
      <span class="cursor-copy text-md-semibold">{{ __("Ticket Details") }}</span>
      <span
        v-if="ticket.data.customer"
        class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-surface-gray-2 text-ink-gray-8"
      >
        {{ ticket.data.customer }}
      </span>
    </div>

    <!-- User info and SLA info -->
    <div class="flex flex-col gap-4 pt-0 px-5 py-3 border-b">
      <!-- User info -->
      <div class="flex gap-2">
        <Avatar
          size="2xl"
          :image="ticket.data.contact?.image"
          :label="ticket.data.contact?.name || ticket.data.raised_by"
        />
        <div class="flex items-center justify-between flex-1 min-w-0">
          <Tooltip :text="ticket.data.contact?.name || ticket.data.raised_by">
            <div class="truncate text-xl font-semibold text-ink-gray-9">
              {{ ticket.data.contact?.name || ticket.data.raised_by }}
            </div>
          </Tooltip>
          <div
            class="flex gap-1.5 shrink-0"
            v-if="
              !ticket.data.feedback_rating && ticket.data.status !== 'Closed'
            "
          >
            <Tooltip :text="ticket.data.contact?.email_id || ticket.data.raised_by">
              <Button class="h-7 w-7" @click="emit('open')">
                <template #icon>
                  <EmailIcon class="h-4 w-4" />
                </template>
              </Button>
            </Tooltip>
          </div>
        </div>
      </div>

      <!-- Ticket Basic Info -->
      <div
        class="flex items-center text-sm leading-5"
        v-for="field in ticketBasicInfo"
        :key="field.label"
      >
        <span class="w-[126px] text-xs text-ink-gray-5">{{
          __(field.label)
        }}</span>
        <span
          class="text-sm text-ink-gray-8 flex-1 truncate"
          :class="field.bold && 'font-semibold text-ink-gray-9'"
        >
          {{ field.value || "—" }}
        </span>
      </div>

      <!-- Real-Time SLA Countdown Badges -->
      <div v-if="slaMetrics?.data" class="flex flex-col gap-2 pt-2 border-t border-outline-gray-1">
        <div class="text-xs font-semibold text-ink-gray-6 uppercase tracking-wider">
          {{ __("SLA Targets") }}
        </div>
        <div class="flex items-center justify-between text-xs">
          <span class="text-ink-gray-6">{{ __("First Response") }}</span>
          <span
            class="px-2 py-0.5 rounded font-medium"
            :class="getSlaBadgeClass(slaMetrics.data.response?.status)"
          >
            {{ slaMetrics.data.response?.human || slaMetrics.data.response?.status }}
          </span>
        </div>
        <div class="flex items-center justify-between text-xs">
          <span class="text-ink-gray-6">{{ __("Resolution Target") }}</span>
          <span
            class="px-2 py-0.5 rounded font-medium"
            :class="getSlaBadgeClass(slaMetrics.data.resolution?.status)"
          >
            {{ slaMetrics.data.resolution?.human || slaMetrics.data.resolution?.status }}
          </span>
        </div>
      </div>
    </div>

    <!-- Resolution Details (Requirement 1 & 5) -->
    <div
      v-if="(ticket.data.status === 'Resolved' || ticket.data.status === 'Closed') && ticket.data.resolution_details"
      class="p-4 border-b bg-surface-gray-1 rounded-md mx-4 space-y-1.5"
    >
      <div class="flex items-center gap-1.5 text-xs font-semibold text-ink-gray-8 uppercase tracking-wider">
        <LucideCheckCircle2 class="size-4 text-ink-gray-7" />
        <span>{{ __("Resolution Details") }}</span>
      </div>
      <div
        class="text-xs text-ink-gray-8 prose prose-xs max-w-none pt-1"
        v-html="ticket.data.resolution_details"
      />
      <div v-if="ticket.data.resolution_date" class="text-[11px] text-ink-gray-5 pt-1 border-t border-outline-gray-1">
        {{ __("Resolved on:") }} {{ ticket.data.resolution_date }}
      </div>
    </div>

    <!-- Satisfaction Feedback: Already submitted -->
    <div
      v-if="ticket.data.feedback_rating"
      class="p-4 border-b bg-surface-gray-1 rounded-md mx-4 space-y-1"
    >
      <div class="text-xs font-semibold text-ink-gray-6 uppercase tracking-wider">
        {{ __("Customer Satisfaction Rating") }}
      </div>
      <div class="flex items-center gap-1 font-bold text-ink-gray-9 text-sm">
        <span>{{ ticket.data.feedback_rating }} / 5</span>
        <LucideStar class="size-4 fill-ink-gray-8 text-ink-gray-8" />
      </div>
      <p
        v-if="ticket.data.feedback_extra || ticket.data.feedback"
        class="text-xs text-ink-gray-7 italic pt-0.5"
      >
        "{{ ticket.data.feedback_extra || ticket.data.feedback }}"
      </p>
    </div>

    <!-- Satisfaction Feedback: Resolved/Closed but not rated yet -->
    <div
      v-else-if="ticket.data.status === 'Resolved' || ticket.data.status === 'Closed'"
      class="p-4 border-b bg-surface-gray-1 rounded-md mx-4 space-y-2.5"
    >
      <div class="text-xs font-semibold text-ink-gray-8 uppercase tracking-wider">
        {{ __("Rate Our Resolution Service") }}
      </div>
      <p class="text-xs text-ink-gray-6">
        {{ __("How satisfied are you with the resolution of this ticket?") }}
      </p>
      <div class="flex items-center gap-1.5 py-1">
        <button
          v-for="star in 5"
          :key="star"
          type="button"
          class="p-1 rounded hover:bg-surface-gray-2 transition-colors"
          @click="selectedRating = star"
        >
          <LucideStar
            class="size-5 transition-colors"
            :class="
              star <= selectedRating
                ? 'fill-ink-gray-9 text-ink-gray-9'
                : 'text-ink-gray-4'
            "
          />
        </button>
      </div>
      <FormControl
        v-if="selectedRating > 0"
        v-model="feedbackText"
        type="textarea"
        size="sm"
        :placeholder="__('Share any comments or feedback (optional)')"
      />
      <Button
        v-if="selectedRating > 0"
        variant="solid"
        size="sm"
        class="w-full"
        :label="__('Submit Rating')"
        :loading="isSubmittingRating"
        @click="submitRating"
      />
    </div>

    <!-- Additional Ticket Fields -->
    <div class="flex flex-col gap-3 pt-0 px-5 py-3 overflow-y-scroll">
      <div
        class="flex items-center text-sm leading-5"
        v-for="field in ticketAdditionalInfo"
        :key="field.fieldname"
      >
        <span class="w-[126px] text-xs text-ink-gray-5">{{
          __(field.label)
        }}</span>
        <Tooltip :disabled="!storedStamp(field)" :text="storedStamp(field)">
          <span class="text-sm text-ink-gray-8 flex-1 truncate">{{
            field.value
          }}</span>
        </Tooltip>
      </div>
    </div>

    <!-- Attachments & Diagnostic Logs (Requirement 3) -->
    <div class="px-5 py-3 border-t flex flex-col gap-2">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-1.5 text-xs font-semibold text-ink-gray-6 uppercase tracking-wider">
          <LucidePaperclip class="size-3.5 text-ink-gray-6" />
          <span>{{ __("Attachments & Logs") }}</span>
        </div>
        <span v-if="attachmentsResource.data?.length" class="text-xs text-ink-gray-5">
          {{ attachmentsResource.data.length }}
        </span>
      </div>

      <div v-if="attachmentsResource.loading" class="py-2 flex justify-center">
        <LoadingIndicator class="size-4 text-ink-gray-6" />
      </div>

      <div
        v-else-if="!attachmentsResource.data?.length"
        class="text-xs text-ink-gray-5 py-1 italic"
      >
        {{ __("No diagnostic logs or attachments.") }}
      </div>

      <div v-else class="space-y-1.5 max-h-36 overflow-y-auto">
        <a
          v-for="file in attachmentsResource.data"
          :key="file.name"
          :href="file.file_url"
          target="_blank"
          download
          class="flex items-center justify-between p-1.5 rounded hover:bg-surface-gray-2 text-xs transition-colors group"
        >
          <div class="flex items-center gap-2 truncate">
            <LucideFileText v-if="file.is_log" class="size-3.5 text-ink-gray-6 shrink-0" />
            <LucideImage v-else-if="file.is_image" class="size-3.5 text-ink-gray-6 shrink-0" />
            <LucideFile v-else class="size-3.5 text-ink-gray-6 shrink-0" />
            <span class="truncate text-ink-gray-8 group-hover:text-ink-gray-9 font-medium">
              {{ file.file_name }}
            </span>
          </div>
          <LucideDownload class="size-3.5 text-ink-gray-5 group-hover:text-ink-gray-8 shrink-0 ml-1" />
        </a>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { EmailIcon } from "@/components/icons";
import { ITicket } from "@/pages/ticket/symbols";
import { Field } from "@/types";
import { dateFormat, dateTooltipFormat } from "@/utils";
import { __ } from "@/translation";
import {
  Avatar,
  Button,
  FormControl,
  LoadingIndicator,
  createResource,
  dayjs,
  toast,
  Tooltip,
} from "frappe-ui";
import { computed, inject, ref } from "vue";
import LucideStar from "~icons/lucide/star";
import LucideCheckCircle2 from "~icons/lucide/check-circle-2";
import LucidePaperclip from "~icons/lucide/paperclip";
import LucideFileText from "~icons/lucide/file-text";
import LucideImage from "~icons/lucide/image";
import LucideFile from "~icons/lucide/file";
import LucideDownload from "~icons/lucide/download";

const emit = defineEmits(["open"]);

const ticket = inject(ITicket);

const attachmentsResource = createResource({
  url: "helpdesk.api.cgd_portal.get_ticket_attachments",
  params: { ticket_id: ticket?.data?.name },
  auto: Boolean(ticket?.data?.name),
});

const selectedRating = ref(0);
const feedbackText = ref("");
const isSubmittingRating = ref(false);

const slaMetrics = createResource({
  url: "helpdesk.api.sla_metrics.get_ticket_sla_metrics",
  params: { ticket_id: ticket?.data?.name },
  auto: Boolean(ticket?.data?.name),
});

const submitCsat = createResource({
  url: "helpdesk.api.csat.submit_csat_survey",
  auto: false,
});

function getSlaBadgeClass(status?: string) {
  switch (status) {
    case "healthy":
      return "bg-surface-gray-2 text-ink-gray-8 font-medium";
    case "urgent":
      return "bg-surface-gray-3 text-ink-gray-9 font-bold";
    case "breached":
      return "bg-surface-gray-3 text-ink-gray-9 font-bold border border-outline-gray-3";
    case "fulfilled":
      return "bg-surface-gray-1 text-ink-gray-7";
    default:
      return "bg-surface-gray-1 text-ink-gray-5";
  }
}

async function submitRating() {
  if (!selectedRating.value) return;
  isSubmittingRating.value = true;
  try {
    await submitCsat.submit({
      ticket: ticket.data.name,
      rating: selectedRating.value,
      feedback: feedbackText.value || "",
    });
    toast({
      title: __("Thank you!"),
      text: __("Your feedback has been recorded successfully."),
      icon: "check",
    });
    ticket.reload();
  } catch (err: any) {
    toast({
      title: __("Error"),
      text: err.message || __("Failed to submit rating"),
      icon: "alert-circle",
    });
  } finally {
    isSubmittingRating.value = false;
  }
}

const ticketBasicInfo = computed(() => {
  const items = [
    {
      label: "Ticket ID",
      value: ticket.data.name,
    },
    {
      label: "Status",
      value: ticket.data.status,
      bold: true,
    },
  ];
  if (ticket.data.customer) {
    items.push({
      label: "CGD Entity",
      value: ticket.data.customer,
      bold: false,
    });
  }
  return items;
});

function storedStamp(field: any) {
  if (field.fieldtype === "Date")
    return dayjs(field.raw).format("ddd, MMM D, YYYY");
  if (field.fieldtype === "Datetime")
    return dayjs(field.raw).format(dateTooltipFormat);
  return "";
}

const ticketAdditionalInfo = computed(() => {
  const fields = [
    {
      fieldname: "subject",
      label: "Subject",
      value: ticket.data.subject,
    },
    {
      fieldname: "team",
      label: "Team",
      value: ticket.data.agent_group,
    },
    {
      fieldname: "priority",
      label: "Priority",
      value: ticket.data.priority,
    },
  ];
  const custom_fields = (ticket.data.template?.fields || [])
    .filter(
      (field: Field) =>
        ["subject", "team", "priority"].indexOf(field.fieldname) === -1 &&
        ticket.data[field.fieldname] != null &&
        ticket.data[field.fieldname] !== ""
    )
    .map((field: Field) => {
      const option = {
        fieldname: field.fieldname,
        fieldtype: field.fieldtype,
        label: field.label,
        value: ticket.data[field.fieldname],
        raw: ticket.data[field.fieldname],
      };
      if (field.fieldtype === "Date") {
        option.value = dayjs(option.value).format(
          (window as any).date_format?.toUpperCase() || "YYYY-MM-DD"
        );
      }
      if (field.fieldtype === "Datetime") {
        option.value = dayjs(option.value).format(
          `${(window as any).date_format?.toUpperCase() || "YYYY-MM-DD"} ${(window as any).time_format || "HH:mm:ss"}`
        );
      }
      return option;
    });

  return [...fields, ...custom_fields].filter(
    (field) => field.value != null && field.value !== ""
  );
});
</script>

<style scoped></style>
