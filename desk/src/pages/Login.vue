<template>
  <div class="min-h-screen w-screen flex flex-col md:flex-row bg-white text-slate-900 font-sans antialiased overflow-x-hidden">
    <!-- LEFT PANEL: Warm Burnt-Orange Hero with Organic Scalloped Edge -->
    <div
      class="relative md:w-5/12 lg:w-1/2 bg-gradient-to-br from-[#ea580c] via-[#d9531e] to-[#b43e10] text-white flex flex-col justify-between p-6 sm:p-10 lg:p-14 overflow-hidden select-none"
    >
      <!-- Background Ambient Watermarks & Geometry -->
      <div class="absolute -bottom-20 -left-20 size-80 rounded-full bg-white/5 blur-2xl pointer-events-none" />
      <div class="absolute -top-20 -right-20 size-72 rounded-full bg-black/10 blur-xl pointer-events-none" />

      <!-- Subtle Swirl / Flame Watermark in Left Corner -->
      <svg
        class="absolute -bottom-16 -left-16 size-96 text-white/5 fill-current pointer-events-none transform -rotate-12"
        viewBox="0 0 24 24"
      >
        <path d="M12 2c.5 3 2.5 5 4.5 7 2.5 2.5 3.5 5.5 3.5 8.5a8 8 0 1 1-16 0c0-3.5 2-6.5 4.5-9 1-1 2-3 2.5-4.5.5-1.5 1-2 1-2z" />
      </svg>

      <!-- Desktop Organic Translucent Scalloped Curves dividing left and right -->
      <!-- Layer 1: Translucent peach shadow scallop -->
      <svg
        class="absolute top-0 -right-4 h-full w-14 text-orange-200/40 fill-current pointer-events-none hidden md:block"
        viewBox="0 0 50 1000"
        preserveAspectRatio="none"
      >
        <path d="M 0,0 C 25,50 50,75 50,125 C 50,175 25,200 0,250 C 25,300 50,325 50,375 C 50,425 25,450 0,500 C 25,550 50,575 50,625 C 50,675 25,700 0,750 C 25,800 50,825 50,875 C 50,925 25,950 0,1000 L 50,1000 L 50,0 Z" />
      </svg>

      <!-- Layer 2: Solid white crisp scallop contour matching right canvas -->
      <svg
        class="absolute top-0 -right-8 h-full w-16 text-white fill-current pointer-events-none hidden md:block"
        viewBox="0 0 50 1000"
        preserveAspectRatio="none"
      >
        <path d="M 0,0 C 25,50 50,75 50,125 C 50,175 25,200 0,250 C 25,300 50,325 50,375 C 50,425 25,450 0,500 C 25,550 50,575 50,625 C 50,675 25,700 0,750 C 25,800 50,825 50,875 C 50,925 25,950 0,1000 L 50,1000 L 50,0 Z" />
      </svg>

      <!-- Top Enterprise Badge -->
      <div class="relative z-10 flex items-center gap-2 text-white/90 text-xs font-semibold tracking-wide uppercase">
        <span class="inline-block size-2 rounded-full bg-emerald-300 animate-pulse" />
        <span>{{ __("Enterprise Support Desk") }}</span>
      </div>

      <!-- Center Hero Message & Brand Icon -->
      <div class="relative z-10 my-auto py-8 sm:py-12 max-w-lg space-y-6">
        <div class="space-y-1">
          <p class="text-white/80 text-base sm:text-lg font-medium tracking-wide">
            {{ __("Welcome to") }}
          </p>
          <h1 class="text-3xl sm:text-4xl lg:text-5xl font-black text-white tracking-tight leading-tight">
            {{ configStore.brandName || __("PNG Support Desk") }}
          </h1>
        </div>

        <!-- Stylized Central Brand Emblem with exact uploaded logo -->
        <div class="inline-flex items-center gap-3.5 bg-white/10 backdrop-blur-md border border-white/20 p-3 rounded-2xl shadow-inner">
          <div class="size-12 rounded-xl bg-white flex items-center justify-center p-1 shadow-md shrink-0">
            <img
              :src="logoSrc"
              alt="PNG Support Desk"
              class="size-full object-contain"
            />
          </div>
          <div class="flex flex-col text-start">
            <span class="text-base font-extrabold text-white leading-tight">Amantya Technologies</span>
            <span class="text-xs text-orange-100 font-medium leading-tight">
              Private Limited
            </span>
          </div>
        </div>

        <!-- Mission statement -->
        <p class="text-orange-100 text-xs sm:text-sm font-normal leading-relaxed max-w-md">
          {{ __("Enterprise ticketing, query management, and support desk for City Gas Distribution (CGD) entities, developed and managed by Amantya Technologies Private Limited.") }}
        </p>
      </div>

      <!-- Bottom Accreditation Footer -->
      <div class="relative z-10 pt-4 border-t border-white/15 flex items-center justify-between text-[11px] text-white/70">
        <span>Amantya Technologies Private Limited</span>
        <span>&copy; {{ new Date().getFullYear() }} All Rights Reserved</span>
      </div>
    </div>

    <!-- Mobile Scalloped Wave Divider (horizontal) -->
    <svg class="w-full h-7 text-white fill-current md:hidden -mt-1 z-10" viewBox="0 0 1000 40" preserveAspectRatio="none">
      <path d="M 0,0 Q 250,40 500,20 T 1000,40 L 1000,40 L 0,40 Z" />
    </svg>

    <!-- RIGHT PANEL: Clean Form Canvas with Modern Styled Inputs -->
    <div
      class="relative flex-1 bg-white flex flex-col justify-center items-center px-6 sm:px-10 lg:px-16 py-10 md:py-14 overflow-hidden"
    >
      <!-- Translucent Swirl Watermark in bottom right corner -->
      <svg
        class="absolute -bottom-16 -right-16 size-80 sm:size-96 text-orange-500/[0.04] fill-current pointer-events-none transform rotate-45 select-none"
        viewBox="0 0 24 24"
      >
        <path d="M12 2c.5 3 2.5 5 4.5 7 2.5 2.5 3.5 5.5 3.5 8.5a8 8 0 1 1-16 0c0-3.5 2-6.5 4.5-9 1-1 2-3 2.5-4.5.5-1.5 1-2 1-2z" />
      </svg>

      <!-- Form Container -->
      <div class="w-full max-w-md relative z-10 space-y-6">
        <!-- Exact Brand Logo on Login Form -->
        <div class="flex items-center gap-3 pb-3 border-b border-slate-100">
          <img
            :src="logoSrc"
            alt="PNG Support Desk"
            class="h-10 w-auto object-contain"
          />
          <div class="flex flex-col text-start">
            <span class="text-base font-extrabold text-slate-800 tracking-tight leading-tight">
              {{ configStore.brandName || __("PNG Support Desk") }}
            </span>
            <span class="text-[11px] text-slate-500 font-medium leading-none mt-0.5">
              Amantya Technologies Private Limited
            </span>
          </div>
        </div>

        <!-- Title & Subtitle matching reference screenshot styling -->
        <div class="space-y-1.5">
          <h2 class="text-3xl sm:text-4xl font-extrabold text-[#d9531e] tracking-tight">
            {{ __("Log in") }}
          </h2>
          <p class="text-sm font-medium text-slate-500">
            {{ __("Please fill in your credentials to login.") }}
          </p>
        </div>

        <!-- Quick Role Profile Selection (Admin vs User) -->
        <div class="p-3.5 rounded-2xl bg-slate-50/90 border border-slate-200/90 shadow-2xs space-y-2">
          <div class="flex items-center justify-between px-1">
            <span class="text-[11px] font-bold text-slate-600 uppercase tracking-wider">
              {{ __("Select Role Profile") }}
            </span>
            <span class="text-[10px] text-slate-400 font-semibold">{{ __("1-Click Profile") }}</span>
          </div>
          <div class="grid grid-cols-2 gap-2.5">
            <button
              type="button"
              class="flex items-center justify-center gap-2 px-3 py-2.5 rounded-xl border text-xs font-bold transition-all shadow-2xs cursor-pointer focus:outline-none"
              :class="
                username === 'Administrator'
                  ? 'bg-orange-50 border-[#d9531e] text-[#c2410c] ring-2 ring-[#d9531e]/20 shadow-xs'
                  : 'bg-white border-slate-300 text-slate-700 hover:bg-slate-100 hover:border-slate-400'
              "
              @click="selectRole('Administrator')"
            >
              <LucideShield class="size-4 shrink-0 text-[#d9531e]" />
              <span>{{ __("Admin Role") }}</span>
            </button>
            <button
              type="button"
              class="flex items-center justify-center gap-2 px-3 py-2.5 rounded-xl border text-xs font-bold transition-all shadow-2xs cursor-pointer focus:outline-none"
              :class="
                username === 'support.png@amantyatech.com' || username === 'user@example.com'
                  ? 'bg-emerald-50 border-emerald-500 text-emerald-900 ring-2 ring-emerald-500/20 shadow-xs'
                  : 'bg-white border-slate-300 text-slate-700 hover:bg-slate-100 hover:border-slate-400'
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
          <div class="text-[11px] text-slate-500 text-center flex items-center justify-center gap-2 pt-0.5">
            <span><strong class="text-slate-700">{{ __("Admin") }}:</strong> {{ __("Full portal access") }}</span>
            <span class="text-slate-300">&bull;</span>
            <span><strong class="text-slate-700">{{ __("User") }}:</strong> support.png</span>
          </div>
        </div>

        <!-- Error Message Banner -->
        <div
          v-if="errorMessage"
          class="flex items-center gap-2.5 p-3.5 rounded-xl bg-rose-50 text-rose-800 border border-rose-200 text-xs font-semibold shadow-2xs animate-shake"
          role="alert"
        >
          <LucideAlertCircle class="size-4 shrink-0 text-rose-600" />
          <span>{{ errorMessage }}</span>
        </div>

        <!-- Form Fields -->
        <form @submit.prevent="handleLogin" class="space-y-4">
          <!-- Username / Email Field -->
          <div class="space-y-1.5">
            <label class="block text-xs font-bold text-slate-700">
              {{ __("Username or Email") }}
            </label>
            <div class="relative flex items-center">
              <div class="absolute inset-y-0 start-0 flex items-center ps-3.5 pointer-events-none text-slate-400">
                <LucideUser class="size-4" />
              </div>
              <input
                v-model="username"
                type="text"
                required
                autocomplete="username"
                :placeholder="__('Administrator or support.png@amantyatech.com')"
                :disabled="isLoading"
                class="w-full ps-10 pe-3.5 py-2.5 text-sm bg-white border border-slate-300 rounded-xl text-slate-900 placeholder-slate-400 transition-all hover:border-slate-400 focus:outline-none focus:border-[#d9531e] focus:ring-4 focus:ring-[#d9531e]/15 disabled:bg-slate-100 disabled:text-slate-400 shadow-2xs font-medium"
              />
            </div>
          </div>

          <!-- Password Field -->
          <div class="space-y-1.5">
            <label class="block text-xs font-bold text-slate-700">
              {{ __("Password") }}
            </label>
            <div class="relative flex items-center">
              <div class="absolute inset-y-0 start-0 flex items-center ps-3.5 pointer-events-none text-slate-400">
                <LucideLock class="size-4" />
              </div>
              <input
                v-model="password"
                :type="showPassword ? 'text' : 'password'"
                required
                autocomplete="current-password"
                placeholder="••••••••"
                :disabled="isLoading"
                class="w-full ps-10 pe-11 py-2.5 text-sm bg-white border border-slate-300 rounded-xl text-slate-900 placeholder-slate-400 transition-all hover:border-slate-400 focus:outline-none focus:border-[#d9531e] focus:ring-4 focus:ring-[#d9531e]/15 disabled:bg-slate-100 disabled:text-slate-400 shadow-2xs font-medium"
              />
              <button
                type="button"
                class="absolute inset-y-0 end-0 flex items-center pe-3.5 text-slate-400 hover:text-slate-700 cursor-pointer focus:outline-none"
                @click="showPassword = !showPassword"
                :title="showPassword ? __('Hide password') : __('Show password')"
              >
                <LucideEyeOff v-if="showPassword" class="size-4" />
                <LucideEye v-else class="size-4" />
              </button>
            </div>
          </div>

          <!-- Remember Me Checkbox -->
          <div class="flex items-center justify-between pt-1">
            <label class="flex items-center gap-2 cursor-pointer select-none">
              <input
                v-model="rememberMe"
                type="checkbox"
                class="size-4 rounded border-slate-300 text-[#d9531e] focus:ring-[#d9531e]/20 accent-[#d9531e] cursor-pointer"
              />
              <span class="text-xs font-medium text-slate-600">
                {{ __("Remember Me") }}
              </span>
            </label>
          </div>

          <!-- Pill-shaped Action Button matching reference screenshot -->
          <div class="pt-2">
            <Button
              type="submit"
              variant="solid"
              class="w-full justify-center !py-3 !px-8 text-sm font-bold !bg-[#d9531e] hover:!bg-[#c2410c] text-white !rounded-full shadow-md hover:shadow-lg transition-all focus:ring-4 focus:ring-[#d9531e]/30"
              :loading="isLoading"
              :label="isLoading ? __('Authenticating...') : __('Log in')"
            >
              <template #prefix>
                <LucideLogIn v-if="!isLoading" class="size-4 me-1" />
              </template>
            </Button>
          </div>
        </form>

        <!-- Security Disclaimer matching reference screenshot -->
        <p class="text-xs text-slate-400 italic text-center pt-2">
          {{ __("*Do not share your login credentials with anyone.") }}
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import pngLogo from "@/assets/png_logo.png";
import { useAuthStore } from "@/stores/auth";
import { useConfigStore } from "@/stores/config";
import { __ } from "@/translation";
import { Button, call, toast, usePageMeta } from "frappe-ui";
import { computed, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import LucideAlertCircle from "~icons/lucide/alert-circle";
import LucideEye from "~icons/lucide/eye";
import LucideEyeOff from "~icons/lucide/eye-off";
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

const logoSrc = computed(() => configStore.brandLogo || pngLogo);

const username = ref("");
const password = ref("");
const showPassword = ref(false);
const rememberMe = ref(true);
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
