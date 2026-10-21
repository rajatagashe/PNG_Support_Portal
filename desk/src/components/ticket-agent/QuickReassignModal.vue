<template>
  <Dialog
    v-model="isOpen"
    :options="{
      title: __('Assign, Reassign or Escalate Ticket'),
      size: 'md',
    }"
  >
    <template #body-content>
      <div class="space-y-4 py-2 text-sm">
        <div class="text-xs text-ink-gray-6 bg-surface-gray-1 p-2.5 rounded border border-outline-gray-1">
          <div><span class="font-medium text-ink-gray-8">{{ __('Ticket:') }}</span> {{ ticketId }}</div>
          <div class="truncate mt-0.5"><span class="font-medium text-ink-gray-8">{{ __('Subject:') }}</span> {{ subject }}</div>
        </div>

        <!-- Action Type Selection -->
        <FormControl
          v-model="form.action_type"
          type="select"
          :label="__('Action Type')"
          :options="[
            { label: __('Assignment'), value: 'Assignment' },
            { label: __('Reassignment'), value: 'Reassignment' },
            { label: __('Escalation (Tier 2 / Technical)'), value: 'Escalation' },
            { label: __('De-escalation'), value: 'De-escalation' },
          ]"
        />

        <!-- Escalation Tier Selection when Escalating -->
        <div
          v-if="form.action_type === 'Escalation'"
          class="p-3 bg-surface-gray-1 rounded-md border border-outline-gray-2 space-y-2"
        >
          <div class="flex items-center gap-1.5 text-xs font-semibold text-ink-gray-8 uppercase tracking-wider">
            <LucideArrowUpRight class="size-3.5 text-ink-gray-7" />
            <span>{{ __('Escalation Tier') }}</span>
          </div>
          <FormControl
            v-model="form.escalation_level"
            type="select"
            :label="__('Target Escalation Level')"
            :options="[
              { label: __('L1 (Frontline Support)'), value: 'L1' },
              { label: __('L2 (Technical / Core Support)'), value: 'L2' },
              { label: __('L3 (Specialist / Engineering)'), value: 'L3' },
            ]"
          />
          <div class="flex gap-2 pt-1">
            <button
              type="button"
              class="px-2 py-1 text-xs rounded border border-outline-gray-2 bg-surface-white hover:bg-surface-gray-2 text-ink-gray-8"
              @click="setQuickTeam('L1 Support')"
            >
              {{ __('Preset: L1 Support') }}
            </button>
            <button
              type="button"
              class="px-2 py-1 text-xs rounded border border-outline-gray-2 bg-surface-white hover:bg-surface-gray-2 text-ink-gray-8 font-medium"
              @click="setQuickTeam('L2 Support')"
            >
              {{ __('Preset: L2 Support') }}
            </button>
          </div>
        </div>

        <Link
          class="w-full"
          doctype="HD Team"
          variant="outline"
          :placeholder="__('Select Support Team')"
          :label="__('Target Team')"
          v-model="form.team"
        />

        <Link
          class="w-full"
          doctype="User"
          variant="outline"
          :placeholder="__('Select Responsible Agent')"
          :label="__('Responsible Agent')"
          v-model="form.agent"
        />

        <FormControl
          v-model="form.status"
          type="select"
          :label="__('Ticket Status')"
          :options="[
            { label: __('Keep Current Status'), value: '' },
            { label: __('Open'), value: 'Open' },
            { label: __('Pending'), value: 'Pending' },
            { label: __('Replied'), value: 'Replied' },
            { label: __('Resolved'), value: 'Resolved' },
          ]"
        />

        <div>
          <label class="block text-xs font-medium text-ink-gray-7 mb-1">
            {{ form.action_type === 'Escalation' ? __('Escalation Reason & Technical Context') : __('Reassignment Reason / Audit Notes') }}
          </label>
          <textarea
            v-model="form.notes"
            rows="3"
            class="w-full rounded border border-outline-gray-2 p-2 text-xs text-ink-gray-9 focus:border-outline-gray-4 focus:outline-none"
            :placeholder="
              form.action_type === 'Escalation'
                ? __('State technical justification for escalation, logs reviewed, steps taken, or unresolved blockers...')
                : __('State reason for assignment/reassignment...')
            "
          />
        </div>
      </div>
    </template>
    <template #actions>
      <div class="flex justify-end gap-2">
        <Button
          variant="subtle"
          :label="__('Cancel')"
          @click="isOpen = false"
        />
        <Button
          variant="solid"
          :label="form.action_type === 'Escalation' ? __('Escalate Ticket') : __('Save Assignment')"
          :loading="assignResource.loading"
          @click="submitAssignment"
        />
      </div>
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { __ } from "@/translation";
import { Link } from "@framework/ui";
import { Button, Dialog, FormControl, createResource, toast } from "frappe-ui";
import { computed, reactive, watch } from "vue";
import LucideArrowUpRight from "~icons/lucide/arrow-up-right";

const props = defineProps<{
  modelValue: boolean;
  ticketId: string;
  subject?: string;
  currentTeam?: string;
  currentAgent?: string;
  currentStatus?: string;
}>();

const emit = defineEmits<{
  (e: "update:modelValue", value: boolean): void;
  (e: "assigned"): void;
}>();

const isOpen = computed({
  get: () => props.modelValue,
  set: (val) => emit("update:modelValue", val),
});

const form = reactive({
  action_type: "Assignment",
  escalation_level: "L2",
  team: props.currentTeam || "",
  agent: props.currentAgent || "",
  status: "",
  notes: "",
});

function setQuickTeam(teamName: string) {
  form.team = teamName;
  if (teamName.includes("L2")) {
    form.escalation_level = "L2";
  } else if (teamName.includes("L1")) {
    form.escalation_level = "L1";
  }
}

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      form.action_type = props.currentTeam ? "Reassignment" : "Assignment";
      form.escalation_level = "L2";
      form.team = props.currentTeam || "";
      form.agent = props.currentAgent || "";
      form.status = "";
      form.notes = "";
    }
  }
);

const assignResource = createResource({
  url: "helpdesk.api.cgd_portal.assign_or_escalate_ticket",
  auto: false,
});

async function submitAssignment() {
  if (!form.team && !form.agent) {
    toast.error(__("Please select a target team or responsible agent."));
    return;
  }

  try {
    const res = await assignResource.submit({
      ticket_id: props.ticketId,
      team: form.team || null,
      agent: form.agent || null,
      action_type: form.action_type,
      escalation_level: form.action_type === "Escalation" ? form.escalation_level : null,
      reason: form.notes || null,
      new_status: form.status || null,
    });

    if (res?.success) {
      toast.success(
        form.action_type === "Escalation"
          ? __("Ticket successfully escalated to Tier {0}.", [form.escalation_level])
          : __("Assignment updated and audit log recorded.")
      );
      isOpen.value = false;
      emit("assigned");
    }
  } catch (error: any) {
    toast.error(error.message || __("Failed to update assignment."));
  }
}
</script>
