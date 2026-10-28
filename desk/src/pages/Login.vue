<template>
  <div class="min-h-screen w-screen flex flex-col justify-center items-center bg-surface-gray-2 px-4 py-8">
    <div class="w-full max-w-md bg-surface-white border border-outline-gray-2 rounded-2xl shadow-xl p-6 sm:p-8 space-y-6">
      <!-- Header -->
      <div class="text-center space-y-2">
        <div class="inline-flex size-16 items-center justify-center rounded-2xl bg-surface-white border border-outline-gray-2 p-1.5 mb-1 shadow-sm">
          <img v-if="configStore.brandLogo" :src="configStore.brandLogo" alt="Brand Logo" class="size-full object-contain rounded-xl" />
          <HDLogo v-else class="size-full object-contain" />
        </div>
        <h1 class="text-2xl font-bold text-ink-gray-9 tracking-tight">
          {{ configStore.brandName || __("PNG Support Desk") }}
        </h1>
        <p class="text-xs text-ink-gray-6">
          {{ __("City Gas Distribution (CGD) Support Hub & Ticketing System") }}
        </p>
      </div>

      <!-- Quick Role Profile Selection -->
      <div class="p-3.5 rounded-xl bg-surface-gray-1 border border-outline-gray-2 space-y-2.5">
        <div class="text-[11px] font-semibold text-ink-gray-6 uppercase tracking-wider text-center">
          {{ __("Select Role Profile") }}
        </div>
        <div class="grid grid-cols-2 gap-2.5">
          <button
            type="button"
            class="flex items-center justify-center gap-2 px-3 py-2.5 rounded-lg border text-xs font-semibold transition-all shadow-xs cursor-pointer focus:outline-none"
            :class="
              username === 'Administrator'
                ? 'bg-blue-50 border-blue-500 text-blue-900 ring-2 ring-blue-500/20'
                : 'bg-surface-white border-outline-gray-2 text-ink-gray-8 hover:bg-surface-gray-2 hover:border-outline-gray-3'
            "
            @click="selectRole('Administrator')"
          >
            <LucideShield class="size-4 shrink-0 text-blue-600" />
            <span>{{ __("Admin Role") }}</span>
          </button>
          <button
            type="button"
            class="flex items-center justify-center gap-2 px-3 py-2.5 rounded-lg border text-xs font-semibold transition-all shadow-xs cursor-pointer focus:outline-none"
            :class="
              username === 'support.png@amantyatech.com' || username === 'user@example.com'
                ? 'bg-emerald-50 border-emerald-500 text-emerald-900 ring-2 ring-emerald-500/20'
                : 'bg-surface-white border-outline-gray-2 text-ink-gray-8 hover:bg-surface-gray-2 hover:border-outline-gray-3'
            "
            @click="selectRole('support.png@amantyatech.com')"
          >
            <LucideMail class="size-4 shrink-0 text-emerald-600" />
            <div class="text-left leading-tight">
              <div>{{ __("User Role") }}</div>
              <div class="text-[9px] font-normal text-emerald-700">support.png</div>
            </div>
          </button>
        </div>
        <div class="text-[11px] text-ink-gray-5 text-center flex items-center justify-center gap-2">
          <span><strong class="text-ink-gray-7">{{ __("Admin") }}:</strong> {{ __("Full portal access") }}</span>
          <span class="text-ink-gray-4">•</span>
          <span><strong class="text-ink-gray-7">{{ __("User") }}:</strong> support.png@amantyatech.com</span>
        </div>
      </div>

      <!-- Error message banner -->
      <div
        v-if="errorMessage"
        class="flex items-center gap-2 p-3 rounded-lg bg-surface-red-2 text-ink-red-6 border border-outline-red-2 text-xs"
      >
        <LucideAlertCircle class="size-4 shrink-0" />
        <span>{{ errorMessage }}</span>
      </div>

      <!-- Login Form -->
      <form @submit.prevent="handleLogin" class="space-y-4">
        <div class="space-y-1.5">
          <label class="block text-xs font-medium text-ink-gray-7">
            {{ __("Username or Email") }}
          </label>
          <div class="relative flex items-center">
            <div class="absolute inset-y-0 start-0 flex items-center ps-3 pointer-events-none text-ink-gray-5">
              <LucideUser class="size-4" />
            </div>
            <input
              v-model="username"
              type="text"
              required
              autocomplete="username"
              :placeholder="__('Administrator or support.png@amantyatech.com')"
              :disabled="isLoading"
              class="w-full ps-9.5 pe-3 py-2 text-sm bg-surface-white border border-outline-gray-3 rounded-lg text-ink-gray-9 placeholder-ink-gray-4 transition-colors hover:border-outline-gray-4 focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-500/20 disabled:bg-surface-gray-2 disabled:text-ink-gray-4"
            />
          </div>
        </div>

        <div class="space-y-1.5">
          <label class="block text-xs font-medium text-ink-gray-7">
            {{ __("Password") }}
          </label>
          <div class="relative flex items-center">
            <div class="absolute inset-y-0 start-0 flex items-center ps-3 pointer-events-none text-ink-gray-5">
              <LucideLock class="size-4" />
            </div>
            <input
              v-model="password"
              :type="showPassword ? 'text' : 'password'"
              required
              autocomplete="current-password"
              placeholder="••••••••"
              :disabled="isLoading"
              class="w-full ps-9.5 pe-10 py-2 text-sm bg-surface-white border border-outline-gray-3 rounded-lg text-ink-gray-9 placeholder-ink-gray-4 transition-colors hover:border-outline-gray-4 focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-500/20 disabled:bg-surface-gray-2 disabled:text-ink-gray-4"
            />
            <button
              type="button"
              class="absolute inset-y-0 end-0 flex items-center pe-3 text-ink-gray-5 hover:text-ink-gray-8 cursor-pointer focus:outline-none"
              @click="showPassword = !showPassword"
              :title="showPassword ? __('Hide password') : __('Show password')"
            >
              <LucideEyeOff v-if="showPassword" class="size-4" />
              <LucideEye v-else class="size-4" />
            </button>
          </div>
        </div>

        <Button
          type="submit"
          variant="solid"
          class="w-full justify-center py-2.5 text-sm font-semibold shadow-sm"
          :loading="isLoading"
          :label="isLoading ? __('Authenticating...') : __('Sign In to Portal')"
        >
          <template #prefix>
            <LucideLogIn v-if="!isLoading" class="size-4" />
          </template>
        </Button>
      </form>

      <!-- Standard Desk Login Link -->
      <div class="text-center pt-2 border-t border-outline-gray-1">
        <a
          href="/login"
          class="text-xs text-ink-gray-6 hover:text-ink-gray-9 transition-colors underline"
        >
          {{ __("Switch to Standard Frappe Desk Login") }}
        </a>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import HDLogo from "@/assets/logos/HDLogo.vue";
import { useAuthStore } from "@/stores/auth";
import { useConfigStore } from "@/stores/config";
import { __ } from "@/translation";
import { Button, call, toast, usePageMeta } from "frappe-ui";
import { ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import LucideAlertCircle from "~icons/lucide/alert-circle";
import LucideEye from "~icons/lucide/eye";
import LucideEyeOff from "~icons/lucide/eye-off";
import LucideFlame from "~icons/lucide/flame";
import LucideLock from "~icons/lucide/lock";
import LucideLogIn from "~icons/lucide/log-in";
import LucideMail from "~icons/lucide/mail";
import LucideShield from "~icons/lucide/shield";
import LucideUser from "~icons/lucide/user";

usePageMeta(() => ({
  title: __("Sign In - PNG Support Desk"),
}));

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();
const configStore = useConfigStore();

const username = ref("");
const password = ref("");
const showPassword = ref(false);
const isLoading = ref(false);
const errorMessage = ref("");

function selectRole(user: string) {
  username.value = user;
  password.value = "";
  errorMessage.value = "";
}

async function handleLogin() {
  const trimmedUser = username.value.trim();
  if (!trimmedUser) {
    errorMessage.value = __("Please enter your username or support email.");
    return;
  }
  if (!password.value) {
    errorMessage.value = __("Please enter your password.");
    return;
  }

  isLoading.value = true;
  errorMessage.value = "";

  try {
    const res = await call("login", {
      usr: trimmedUser,
      pwd: password.value,
    });

    if (res === "Logged In" || res?.message === "Logged In") {
      try {
        const userInfo: any = await call("helpdesk.api.auth.get_user");
        let targetUrl = "/helpdesk/home";
        let welcomeMsg = __("Welcome back! Full portal access granted.");

        if (userInfo?.is_email_user_only) {
          targetUrl = "/helpdesk/support-emails";
          welcomeMsg = __("Welcome! Redirecting to Support Email Management.");
        } else if (!userInfo?.has_desk_access) {
          targetUrl = "/helpdesk/my-tickets";
          welcomeMsg = __("Welcome to Customer Support Portal.");
        } else if (userInfo?.is_admin) {
          welcomeMsg = __("Welcome back, Administrator. Full portal access granted.");
        }

        toast.success(welcomeMsg);
        window.location.href = targetUrl;
        return;
      } catch {
        const isUserAdmin =
          trimmedUser.toLowerCase() === "administrator" ||
          trimmedUser.toLowerCase() === "admin";
        window.location.href = isUserAdmin ? "/helpdesk/home" : "/helpdesk/support-emails";
      }
    } else {
      errorMessage.value = __("Invalid username or password. Please verify your credentials.");
      isLoading.value = false;
    }
  } catch (err: any) {
    const rawMsg = err?.messages?.[0] || err?.message || "";
    if (
      rawMsg.toLowerCase().includes("invalid login credentials") ||
      rawMsg.toLowerCase().includes("incorrect password")
    ) {
      errorMessage.value = __("Invalid username or password. Please check your credentials.");
    } else if (rawMsg.toLowerCase().includes("disabled")) {
      errorMessage.value = __("Your support account is disabled. Please contact the administrator.");
    } else if (rawMsg) {
      errorMessage.value = rawMsg;
    } else {
      errorMessage.value = __("Authentication failed. Please verify your connection and credentials.");
    }
  } finally {
    isLoading.value = false;
  }
}
</script>
