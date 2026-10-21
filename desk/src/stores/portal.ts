import { createResource } from "frappe-ui";
import { defineStore } from "pinia";
import { computed } from "vue";

export const usePortalStore = defineStore("portal", () => {
  const brandingResource = createResource({
    url: "helpdesk.api.portal.get_portal_branding",
    auto: true,
  });

  const branding = computed(() => brandingResource.data || {});

  const brandName = computed(
    () => branding.value.brand_name || "MyPNG Support Desk"
  );
  const brandLogo = computed(() => branding.value.brand_logo || "");
  const customerName = computed(() => branding.value.customer_name || "");
  const isVip = computed(() => Boolean(branding.value.is_vip));
  const bannerTitle = computed(
    () => branding.value.banner_title || "City Gas Distribution (CGD) Support Hub"
  );
  const bannerSubtitle = computed(
    () =>
      branding.value.banner_subtitle ||
      "Unified customer self-service, issue reporting, and knowledge repository."
  );
  const isCustomer = computed(() => Boolean(branding.value.is_customer));

  return {
    brandingResource,
    branding,
    brandName,
    brandLogo,
    customerName,
    isVip,
    bannerTitle,
    bannerSubtitle,
    isCustomer,
    reload: brandingResource.reload,
  };
});
