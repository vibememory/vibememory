"use client";

import { useEffect } from "react";

declare global {
  interface Window {
    vmMountLanguageSwitcher?: () => void;
    vmTheme?: {
      current: () => string;
      set: (theme: string, persist?: boolean) => boolean;
      mount?: () => void;
      useSystem: () => string;
    };
  }
}

export function PublicHeaderControls() {
  useEffect(() => {
    window.vmMountLanguageSwitcher?.();
    window.vmTheme?.mount?.();
  }, []);
  return null;
}
