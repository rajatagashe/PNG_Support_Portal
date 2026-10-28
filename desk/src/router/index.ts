import { useScreenSize } from "@/composables/screen";
import { canViewPersona, personaInterrupt } from "@/persona";
import { useAuthStore } from "@/stores/auth";
import { useUserStore } from "@/stores/user";
import { __ } from "@/translation";
import { isCustomerPortal } from "@/utils";
import { toast } from "frappe-ui";
import { createRouter, createWebHistory } from "vue-router";
const { isMobileView } = useScreenSize();

export const LOGIN_PAGE = "/helpdesk/login";

// type the meta fields
declare module "vue-router" {
  interface RouteMeta {
    auth?: boolean;
    agent?: boolean;
    admin?: boolean;
    public?: boolean;
    onSuccessRoute?: string;
    parent?: string;
  }
}

// Pages that render inside the portal chrome; PortalRoot picks the agent or
// customer shell from the session.
const portalRoutes = [
  // Agent Portal Routes
  {
    path: "",
    redirect: "/home",
  },
  {
    path: "/home",
    name: "Home",
    component: () => import("@/pages/home/Home.vue"),
  },

  {
    path: "/support-emails",
    name: "SupportEmails",
    component: () => import("@/pages/support-emails/SupportEmails.vue"),
  },
  {
    path: "/tickets",
    name: "TicketsAgent",
    component: () => import("@/pages/ticket/Tickets.vue"),
  },
  {
    path: "/tickets/:ticketId",
    name: "TicketAgent",
    component: () =>
      import(`@/pages/ticket/${handleMobileView("TicketAgent")}.vue`),
    props: true,
  },
  {
    path: "/tickets/new/:templateId?",
    name: "TicketAgentNew",
    component: () => import("@/pages/ticket/TicketNew.vue"),
    props: true,
    meta: {
      onSuccessRoute: "TicketAgent",
      parent: "TicketsAgent",
    },
  },
  {
    path: "/notifications",
    name: "Notifications",
    component: () => import("@/pages/MobileNotifications.vue"),
  },
  {
    path: "/kb",
    name: "AgentKnowledgeBase",
    component: () => import("@/pages/knowledge-base/KnowledgeBaseAgent.vue"),
  },
  {
    path: "/search",
    name: "SearchAgent",
    component: () => import("@/pages/SearchAgent.vue"),
    meta: { auth: true },
  },
  {
    path: "/kb/articles/:articleId",
    name: "Article",
    component: () => import("@/pages/knowledge-base/Article.vue"),
    props: true,
  },
  {
    path: "/articles/new/:id",
    name: "NewArticle",
    component: () => import("@/pages/knowledge-base/NewArticle.vue"),
    props: true,
  },
  {
    path: "/customers",
    name: "CustomerList",
    component: () => import("@/pages/customer/Customers.vue"),
  },
  {
    path: "/customers/:id",
    name: "Customer",
    component: () => import("@/pages/customer/Customer.vue"),
    props: true,
  },
  {
    path: "/contacts",
    name: "ContactList",
    component: () => import("@/pages/contact/Contacts.vue"),
  },
  {
    path: "/contacts/:id",
    name: "Contact",
    component: () => import("@/pages/contact/Contact.vue"),
    props: true,
  },
  {
    path: "/agents",
    name: "AgentList",
    redirect: "/tickets",
  },
  {
    path: "/teams",
    name: "Teams",
    redirect: "/tickets",
  },
  {
    path: "/teams/:teamId",
    name: "Team",
    redirect: "/tickets",
  },
  {
    path: "/dashboard",
    name: "Dashboard",
    component: () => import("@/pages/dashboard/Dashboard.vue"),
  },
  {
    path: "/call-logs",
    name: "CallLogs",
    component: () => import("@/pages/call-logs/CallLogs.vue"),
  },

  // Customer Portal Routes
  {
    path: "/cgd-dashboard",
    name: "CustomerDashboard",
    component: () => import("@/pages/dashboard/CustomerDashboard.vue"),
    meta: {
      public: true,
      auth: true,
    },
  },
  {
    path: "/my-tickets",
    name: "TicketsCustomer",
    component: () => import("@/pages/ticket/Tickets.vue"),
    meta: {
      public: true,
      auth: true,
    },
  },
  {
    path: "/my-tickets/:ticketId",
    name: "TicketCustomer",
    component: () => import("@/pages/ticket/TicketCustomer.vue"),
    meta: {
      public: true,
      auth: true,
    },
    props: true,
  },
  {
    path: "/my-tickets/new",
    name: "TicketNew",
    component: () => import("@/pages/ticket/TicketNew.vue"),
    props: true,
    meta: {
      onSuccessRoute: "TicketCustomer",
      parent: "TicketsCustomer",
      public: true,
      auth: true,
    },
  },
  {
    path: "/kb-public",
    name: "CustomerKnowledgeBase",
    component: () => import("@/pages/knowledge-base/KnowledgeBaseCustomer.vue"),
    meta: {
      public: true,
      auth: true,
    },
  },
  {
    path: "/kb-public/:categoryId",
    name: "Articles",
    component: () => import("@/pages/knowledge-base/Articles.vue"),
    props: true,
    meta: {
      public: true,
      auth: true,
    },
  },
  {
    path: "/kb-public/articles/:articleId",
    name: "ArticlePublic",
    component: () => import("@/pages/knowledge-base/Article.vue"),
    props: true,
    meta: {
      public: true,
      auth: true,
    },
  },

  // Additonal routes
  {
    path: "/:pathMatch(.*)*",
    name: "Invalid Page",
    component: () => import("@/pages/InvalidPage.vue"),
  },
];

const routes = [
  // Standalone Portal Login Page
  {
    path: "/login",
    name: "Login",
    component: () => import("@/pages/Login.vue"),
    meta: { public: true },
  },
  // Renders bare — no portal chrome.
  {
    path: "/onboarding",
    name: "Persona",
    component: () => import("@/pages/PersonaForm.vue"),
    beforeEnter: () => canViewPersona(useAuthStore()) || { name: "Home" },
  },
  {
    path: "/",
    component: () => import("@/roots/PortalRoot.vue"),
    children: portalRoutes,
  },
];

const handleMobileView = (componentName: string) => {
  return isMobileView.value ? `Mobile${componentName}` : componentName;
};

export const router = createRouter({
  history: createWebHistory("/helpdesk/"),
  routes,
});

router.beforeEach(async (to, _, next) => {
  const authStore = useAuthStore();
  isCustomerPortal.value = to.meta.public || false;

  // Handle Login page navigation: allow viewing the login page directly
  if (to.name === "Login") {
    return next();
  }

  if (authStore.isLoggedIn) {
    await authStore.init();
  }

  const interrupt = personaInterrupt(to, authStore);
  if (interrupt) return next(interrupt);

  if (!authStore.isLoggedIn) {
    return next({
      name: "Login",
      query: to.fullPath !== "/" ? { "redirect-to": to.fullPath } : undefined,
    });
  }

  // Role-Based Access Control: User Role is strictly restricted to Support Email Management
  if (authStore.isEmailUserOnly) {
    if (to.name === "SupportEmails") {
      return next();
    }
    // Block unauthorized access and redirect to Support Email Management
    toast.error(
      __("Access Denied: Your account role is restricted to Support Email Management only.")
    );
    return next({ name: "SupportEmails" });
  }

  if (to.name === "TicketAgent" && !authStore.isAgent) {
    const ticketId = to.params.ticketId;
    next({
      name: "TicketCustomer",
      params: { ticketId },
    });
  } else if (!to.meta.public && !authStore.hasDeskAccess) {
    next({ name: "TicketsCustomer" });
  } else {
    next();
  }
});

router.afterEach(async (to) => {
  // the user list is agent-only, and the support email page doesn't need it
  if (to.meta.public || useAuthStore().isEmailUserOnly) return;
  const { users } = useUserStore();
  if (!users?.fetched) {
    await users.fetch();
  }
});
