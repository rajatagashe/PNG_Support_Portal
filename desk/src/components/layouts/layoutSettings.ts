import { ref } from "vue";
import LucideBookOpen from "~icons/lucide/book-open";
import LucideUsers from "~icons/lucide/users";
import LucideTicket from "~icons/lucide/ticket";
import LucideLayoutDashboard from "~icons/lucide/layout-dashboard";
import LucideMail from "~icons/lucide/mail";
import { OrganizationsIcon } from "../icons";
import PhoneIcon from "../icons/PhoneIcon.vue";
import LucideHome from "~icons/lucide/home";
import { __ } from "@/translation";

/**
 * Shared rather than local to Sidebar.vue: the command palette opens it too, and
 * the palette is the discovery surface for the shortcut system.
 */
export const showShortcutsModal = ref(false);

export const supportEmailUserSidebarOptions = [
  {
    label: __("Support Emails"),
    icon: LucideMail,
    to: "SupportEmails",
  },
];

export const agentPortalSidebarOptions = [
  {
    label: __("Home"),
    icon: LucideHome,
    to: "Home",
  },
  {
    label: __("Dashboard"),
    icon: LucideLayoutDashboard,
    to: "Dashboard"
  },
  {
    label: __("Support Emails"),
    icon: LucideMail,
    to: "SupportEmails",
  },
  {
    label: __("Tickets"),
    icon: LucideTicket,
    to: "TicketsAgent",
  },
  {
    label: __("Knowledge Base"),
    icon: LucideBookOpen,
    to: "AgentKnowledgeBase",
  },
  {
    label: "Customers",
    icon: OrganizationsIcon,
    to: "CustomerList",
  },
  {
    label: __("Contacts"),
    icon: LucideUsers,
    to: "ContactList",
  },
  {
    label: __("Call Logs"),
    icon: PhoneIcon,
    to: "CallLogs",
  },
];

export const customerPortalSidebarOptions = [
  {
    label: __("Dashboard"),
    icon: LucideLayoutDashboard,
    to: "CustomerDashboard",
  },
  {
    label: __("Tickets"),
    icon: LucideTicket,
    to: "TicketsCustomer",
  },
  {
    label: __("Knowledge Base"),
    icon: LucideBookOpen,
    to: "CustomerKnowledgeBase",
  },
];
