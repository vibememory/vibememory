"use client";

import { useEffect } from "react";

declare global {
  interface Window {
    vmReactHydrated?: boolean;
    vmMountLanguageSwitcher?: () => void;
    vmApplyTranslations?: (root?: Node) => void;
  }
}

export function I18nHydrator() {
  useEffect(() => {
    window.vmReactHydrated = true;
    window.vmTheme?.mount?.();
    window.vmMountLanguageSwitcher?.();
    window.vmApplyTranslations?.();
    window.dispatchEvent(new Event("vm-react-hydrated"));
  }, []);
  return null;
}
