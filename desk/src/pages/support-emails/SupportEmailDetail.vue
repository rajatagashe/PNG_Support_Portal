<template>
  <Dialog v-model="isOpen" :options="{ title: dialogTitle, size: '4xl' }">
    <template #body-content>
      <div v-if="detail.loading && !detail.data" class="flex justify-center py-10">
        <LoadingIndicator class="size-6 text-ink-gray-6" />
      </div>
      <div v-else-if="detail.error" class="py-6 text-sm text-ink-gray-7" role="alert">
        {{ detail.error.messages?.[0] || __("Could not load this email.") }}
      </div>

      <div v-else-if="email" class="space-y-4 text-sm">
        <!-- Ticket summary & actions -->
        <div class="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-outline-gray-2 bg-surface-gray-1/70 p-3 text-xs text-ink-gray-7 shadow-2xs">
          <div class="flex flex-wrap items-center gap-2">
            <span class="font-mono font-semibold px-2 py-0.5 rounded bg-surface-white border border-outline-gray-2 text-ink-gray-9">
              #{{ email.ticket.name }}
            </span>
            <span
              class="px-2.5 py-0.5 rounded-full font-semibold border inline-flex items-center gap-1.5"
              :class="getStatusBadgeClass(email.ticket.status)"
            >
              <span class="size-1.5 rounded-full" :class="getStatusDotClass(email.ticket.status)" />
              {{ email.ticket.status }}
            </span>
            <span v-if="email.ticket.customer" class="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-blue-50 text-primary border border-blue-200 font-medium">
              <LucideBuilding2 class="size-3" />
              {{ email.ticket.customer }}
            </span>
            <span v-if="email.ticket.agent_group" class="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-surface-white border border-outline-gray-2 text-ink-gray-8">
              {{ __("Team") }}: <b class="text-ink-gray-9">{{ email.ticket.agent_group }}</b>
            </span>
          </div>
          <div class="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              :label="hasUnread ? __('Mark as read') : __('Mark as unread')"
              :loading="seen.loading"
              @click="setSeen(hasUnread ? 1 : 0)"
            >
              <template #prefix>
                <LucideMailOpen v-if="hasUnread" class="size-3.5 text-primary" />
                <LucideMail v-else class="size-3.5 text-ink-gray-6" />
              </template>
            </Button>
            <Button
              v-if="email.can_open_ticket"
              variant="subtle"
              size="sm"
              :label="__('Open ticket')"
              @click="openTicket"
            >
              <template #prefix>
                <LucideExternalLink class="size-3.5 text-primary" />
              </template>
            </Button>
          </div>
        </div>

        <!-- Thread -->
        <div class="space-y-3.5 max-h-[50vh] overflow-y-auto pr-1">
          <article
            v-for="msg in email.messages"
            :key="msg.name"
            class="rounded-xl border transition-all"
            :class="
              msg.sent_or_received === 'Received'
                ? 'border-blue-200 bg-surface-white shadow-xs'
                : 'border-outline-gray-2 bg-surface-gray-1/50'
            "
            :aria-label="__('Email from {0}', [msg.sender_full_name || msg.sender])"
          >
            <header class="flex flex-wrap items-start justify-between gap-2 border-b border-outline-gray-1 px-3.5 py-2.5 bg-surface-gray-1/30 rounded-t-xl">
              <div class="min-w-0">
                <div class="font-semibold text-ink-gray-9 truncate flex items-center gap-1.5">
                  <span class="size-2 rounded-full" :class="msg.sent_or_received === 'Received' ? 'bg-primary' : 'bg-emerald-500'" />
                  {{ msg.sender_full_name || msg.sender }}
                  <span class="font-normal text-xs text-ink-gray-5">&lt;{{ msg.sender }}&gt;</span>
                </div>
                <div v-if="msg.recipients" class="text-xs text-ink-gray-6 truncate mt-0.5">
                  <span class="font-medium text-ink-gray-7">{{ __("To") }}:</span> {{ msg.recipients }}
                </div>
                <div v-if="msg.cc" class="text-xs text-ink-gray-6 truncate">
                  <span class="font-medium text-ink-gray-7">{{ __("Cc") }}:</span> {{ msg.cc }}
                </div>
              </div>
              <div class="flex items-center gap-2 text-xs text-ink-gray-6 shrink-0">
                <span
                  class="px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wider border"
                  :class="
                    msg.sent_or_received === 'Received'
                      ? 'bg-blue-50 text-primary border-blue-200'
                      : 'bg-emerald-50 text-emerald-700 border-emerald-200'
                  "
                >
                  {{ msg.sent_or_received === "Received" ? __("Received") : __("Sent") }}
                </span>
                <time :datetime="msg.communication_date" class="font-medium text-ink-gray-6">{{ dateFormat(msg.communication_date) }}</time>
              </div>
            </header>
            <!-- content is sanitized on the server -->
            <div class="prose prose-sm max-w-none px-4 py-3 text-ink-gray-9 break-words" v-html="msg.content" />
            <AttachmentList v-if="msg.attachments?.length" :files="msg.attachments" class="px-4 pb-3.5" />
          </article>
        </div>

        <div v-if="email.attachments?.length" class="bg-surface-gray-1/50 border border-outline-gray-2 rounded-xl p-3">
          <div class="mb-2 text-xs font-semibold text-ink-gray-8 flex items-center gap-1.5">
            <LucidePaperclip class="size-3.5 text-primary" />
            <span>{{ __("Ticket attachments") }}</span>
          </div>
          <AttachmentList :files="email.attachments" />
        </div>

        <!-- Reply -->
        <form class="space-y-3 border-t border-outline-gray-2 pt-4 bg-surface-white" @submit.prevent="sendReply">
          <div class="text-xs font-medium text-ink-gray-7 flex items-center gap-1.5">
            <LucideSend class="size-3.5 text-primary" />
            <span>{{ __("Reply to {0}", [email.ticket.raised_by]) }}</span>
          </div>
          <FormControl
            v-model="reply.cc"
            type="text"
            :label="__('Cc (optional)')"
            :placeholder="__('name@example.com, other@example.com')"
          />
          <FormControl
            v-model="reply.message"
            type="textarea"
            :label="__('Message')"
            :rows="4"
            :placeholder="__('Write your professional reply...')"
          />
          <div class="flex justify-end pt-1">
            <Button
              type="submit"
              variant="solid"
              :label="__('Send reply')"
              :loading="sendResource.loading"
              :disabled="!reply.message.trim()"
            >
              <template #prefix>
                <LucideSend class="size-3.5" />
              </template>
            </Button>
          </div>
        </form>
      </div>
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { __ } from "@/translation";
import { dateFormat } from "@/utils";
import {
  Button,
  Dialog,
  FormControl,
  LoadingIndicator,
  createResource,
  toast,
} from "frappe-ui";
import { computed, defineComponent, h, reactive, watch } from "vue";
import { useRouter } from "vue-router";
import LucideBuilding2 from "~icons/lucide/building-2";
import LucideExternalLink from "~icons/lucide/external-link";
import LucideMail from "~icons/lucide/mail";
import LucideMailOpen from "~icons/lucide/mail-open";
import LucidePaperclip from "~icons/lucide/paperclip";
import LucideSend from "~icons/lucide/send";

interface Attachment {
  name: string;
  file_name: string;
  file_size: number;
  download_url: string;
}

const props = defineProps<{ modelValue: boolean; ticketId: string | null }>();
const emit = defineEmits<{
  (e: "update:modelValue", value: boolean): void;
  (e: "changed"): void;
}>();

const router = useRouter();
const isOpen = computed({
  get: () => props.modelValue,
  set: (val) => emit("update:modelValue", val),
});

const detail = createResource({ url: "helpdesk.api.support_mailbox.get_support_email" });
const seen = createResource({ url: "helpdesk.api.support_mailbox.set_support_email_seen" });
const sendResource = createResource({ url: "helpdesk.api.support_mailbox.reply_to_support_email" });

const email = computed(() => detail.data);
const dialogTitle = computed(() => email.value?.ticket?.subject || __("Support Email"));
const hasUnread = computed(() =>
  (email.value?.messages || []).some((m) => m.sent_or_received === "Received" && !m.seen)
);
const reply = reactive({ message: "", cc: "" });

watch(
  () => [props.modelValue, props.ticketId],
  async ([open, ticketId]) => {
    if (!open || !ticketId) return;
    reply.message = "";
    reply.cc = "";
    await detail.fetch({ ticket_id: ticketId });
    // opening an email reads it, like any inbox
    if (hasUnread.value) await setSeen(1);
  },
  { immediate: true }
);

async function setSeen(value: 0 | 1) {
  try {
    await seen.submit({ ticket_id: props.ticketId, seen: value });
    await detail.reload();
    emit("changed");
  } catch (err: any) {
    toast.error(err.messages?.[0] || __("Could not update the read state."));
  }
}

async function sendReply() {
  if (!reply.message.trim()) return;
  try {
    await sendResource.submit({
      ticket_id: props.ticketId,
      message: reply.message,
      cc: reply.cc.trim() || null,
    });
    toast.success(__("Reply sent from the support mailbox."));
    reply.message = "";
    reply.cc = "";
    await detail.reload();
    emit("changed");
  } catch (err: any) {
    toast.error(err.messages?.[0] || __("Could not send the reply."));
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
      return "bg-surface-gray-2 text-ink-gray-7 border-outline-gray-2";
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
      return "bg-surface-gray-4";
  }
}

function openTicket() {
  router.push({ name: "TicketAgent", params: { ticketId: props.ticketId } });
}

function formatSize(bytes: number) {
  if (!bytes) return "";
  const units = ["B", "KB", "MB", "GB"];
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${(bytes / 1024 ** i).toFixed(i ? 1 : 0)} ${units[i]}`;
}

const AttachmentList = defineComponent({
  props: { files: { type: Array as () => Attachment[], required: true } },
  setup(p) {
    return () =>
      h(
        "ul",
        { class: "flex flex-wrap gap-2", "aria-label": __("Attachments") },
        p.files.map((f) =>
          h("li", { key: f.name }, [
            h(
              "a",
              {
                href: f.download_url,
                class:
                  "inline-flex items-center gap-1.5 rounded border border-outline-gray-2 bg-surface-gray-1 px-2 py-1 text-xs text-ink-gray-8 hover:bg-surface-gray-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3",
              },
              [
                h(LucidePaperclip, { class: "size-3.5 text-ink-gray-6" }),
                h("span", { class: "max-w-[14rem] truncate" }, f.file_name),
                h("span", { class: "text-ink-gray-5" }, formatSize(f.file_size)),
              ]
            ),
          ])
        )
      );
  },
});
</script>
