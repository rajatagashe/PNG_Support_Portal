<template>
  <div
    class="bg-white border border-gray-200/90 rounded-2xl p-4 shadow-xs space-y-3"
    role="status"
    aria-live="polite"
  >
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-2">
        <div class="flex size-8 items-center justify-center rounded-lg bg-orange-50 border border-orange-200 text-[#d9531e]">
          <LucidePlugZap class="size-4" />
        </div>
        <div>
          <span class="text-sm font-bold text-gray-900">
            {{ __("Support Mailbox Connection") }}
          </span>
          <span class="text-xs text-gray-500 font-medium block">
            {{ __("Microsoft 365 OAuth Inbound Sync") }}
          </span>
        </div>
        <LoadingIndicator v-if="status.loading" class="size-3.5 text-gray-400 ml-1" />
      </div>
    </div>

    <div v-if="!accounts.length && !status.loading" class="text-xs text-ink-gray-6 bg-surface-gray-1 p-3 rounded-lg border border-outline-gray-1">
      {{
        __(
          "No support mailbox is set up yet. An administrator can provision it with the setup script."
        )
      }}
    </div>

    <div
      v-for="acc in accounts"
      :key="acc.account"
      class="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-slate-50/90 p-3.5 transition-all hover:bg-slate-100/90"
    >
      <div class="flex items-center gap-3 min-w-0">
        <!-- Live status pulse indicator -->
        <div class="relative flex items-center justify-center size-5 shrink-0">
          <span
            v-if="acc.state === 'connected'"
            class="absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75 animate-ping"
          />
          <component
            :is="stateIcon(acc.state)"
            class="size-5 shrink-0"
            :class="{
              'text-emerald-600': acc.state === 'connected',
              'text-rose-600': acc.state === 'error',
              'text-amber-600': acc.state === 'disabled' || acc.state === 'not_synced'
            }"
          />
        </div>

        <div class="min-w-0">
          <div class="flex items-center gap-2 flex-wrap">
            <span class="text-sm font-bold text-slate-900 truncate">
              {{ acc.email_id }}
            </span>
            <span
              class="px-2.5 py-0.5 rounded-full text-[10px] font-bold tracking-wide border inline-flex items-center gap-1 shadow-2xs"
              :class="{
                'bg-emerald-100 text-emerald-800 border-emerald-300': acc.state === 'connected',
                'bg-rose-100 text-rose-800 border-rose-300': acc.state === 'error',
                'bg-slate-200 text-slate-800 border-slate-300': acc.state === 'disabled',
                'bg-amber-100 text-amber-800 border-amber-300': acc.state === 'not_synced'
              }"
            >
              <span
                class="size-1.5 rounded-full"
                :class="{
                  'bg-emerald-600': acc.state === 'connected',
                  'bg-rose-600': acc.state === 'error',
                  'bg-slate-600': acc.state === 'disabled',
                  'bg-amber-600': acc.state === 'not_synced'
                }"
              />
              {{ stateLabel(acc.state) }}
            </span>
          </div>
          <div class="text-xs text-slate-600 mt-0.5 flex items-center gap-3 flex-wrap">
            <span v-if="acc.message" class="text-rose-700 font-bold">{{ acc.message }}</span>
            <span v-else-if="acc.last_success_at" class="flex items-center gap-1 font-medium">
              {{ __("Last checked {0}", [timeAgo(acc.last_success_at)]) }}
            </span>
            <span v-if="acc.last_email_at" class="text-slate-500 font-medium">
              &bull; {{ __("Latest email {0}", [timeAgo(acc.last_email_at)]) }}
            </span>
          </div>
        </div>
      </div>

      <div class="flex items-center gap-2 shrink-0">
        <Button
          v-if="status.data?.can_reconnect && acc.uses_app_access && needsActivation(acc)"
          variant="solid"
          size="sm"
          :label="acc.state === 'disabled' ? __('Activate') : __('Retry')"
          :loading="activate.loading"
          @click="activateMailbox(acc.account)"
        >
          <template #prefix>
            <LucidePower class="size-3.5" />
          </template>
        </Button>
        <Button
          v-else-if="status.data?.can_reconnect && acc.auth_method === 'OAuth' && needsSignIn(acc)"
          variant="solid"
          size="sm"
          :label="acc.last_success_at ? __('Reconnect') : __('Connect')"
          :loading="authorize.loading"
          @click="startSignIn(acc.account)"
        >
          <template #prefix>
            <LucideLogIn class="size-3.5" />
          </template>
        </Button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { globalStore } from "@/stores/globalStore";
import { __ } from "@/translation";
import { timeAgo } from "@/utils";
import { Button, LoadingIndicator, createResource, toast } from "frappe-ui";
import { computed, onMounted, onUnmounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import LucideCircleAlert from "~icons/lucide/circle-alert";
import LucideCircleCheck from "~icons/lucide/circle-check";
import LucideCircleDashed from "~icons/lucide/circle-dashed";
import LucideCirclePause from "~icons/lucide/circle-pause";
import LucideLogIn from "~icons/lucide/log-in";
import LucidePlugZap from "~icons/lucide/plug-zap";
import LucidePower from "~icons/lucide/power";

interface MailboxStatus {
  account: string;
  email_id: string;
  auth_method: string;
  uses_app_access: boolean;
  state: "connected" | "error" | "disabled" | "not_synced";
  error_type: string | null;
  message: string | null;
  last_success_at: string | null;
  last_email_at: string | null;
}

const emit = defineEmits<{ (e: "activated"): void }>();

const route = useRoute();
const router = useRouter();
const { $socket } = globalStore();

const status = createResource({
  url: "helpdesk.api.support_mailbox.get_mailbox_status",
  auto: true,
});
const accounts = computed<MailboxStatus[]>(() => status.data?.accounts || []);

const authorize = createResource({
  url: "helpdesk.api.support_mailbox.get_mailbox_authorization_url",
});
const activate = createResource({
  url: "helpdesk.api.support_mailbox.activate_support_mailbox",
});

function needsSignIn(acc: MailboxStatus) {
  return acc.state === "disabled" || acc.error_type === "authorization_required";
}

function needsActivation(acc: MailboxStatus) {
  return acc.state === "disabled" || acc.error_type === "app_access_denied";
}

function stateIcon(state: MailboxStatus["state"]) {
  return {
    connected: LucideCircleCheck,
    error: LucideCircleAlert,
    disabled: LucideCirclePause,
  }[state] || LucideCircleDashed;
}

function stateLabel(state: MailboxStatus["state"]) {
  return {
    connected: __("Connected"),
    error: __("Needs attention"),
    disabled: __("Not connected"),
  }[state] || __("Waiting for first sync");
}

async function startSignIn(account: string) {
  try {
    const url = await authorize.submit({ account });
    window.location.href = url;
  } catch (err: any) {
    toast.error(err.messages?.[0] || __("Could not start the mailbox sign-in."));
  }
}

// Microsoft sends the admin back here once; switch the mailbox on and sync it
async function finishSignIn(account: string) {
  router.replace({ query: { ...route.query, mailbox_authorized: undefined } });
  await activateMailbox(account);
}

async function activateMailbox(account: string) {
  try {
    const res = await activate.submit({ account });
    if (res?.status === "failed") toast.error(res.message);
    else toast.success(__("Support mailbox connected. New emails will sync automatically."));
    emit("activated");
  } catch (err: any) {
    toast.error(err.messages?.[0] || __("Could not connect the support mailbox."));
  }
  status.reload();
}

function reloadStatus() {
  status.reload();
}

onMounted(() => {
  const authorized = route.query.mailbox_authorized;
  if (typeof authorized === "string" && authorized) finishSignIn(authorized);
  $socket?.on("helpdesk:support-mailbox-status", reloadStatus);
  $socket?.on("helpdesk:support-email-synced", reloadStatus);
});

onUnmounted(() => {
  $socket?.off("helpdesk:support-mailbox-status", reloadStatus);
  $socket?.off("helpdesk:support-email-synced", reloadStatus);
});
</script>
