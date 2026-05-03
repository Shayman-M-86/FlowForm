export const GITHUB_URL = "https://github.com/Shayman-M-86/FlowForm";

export const BRAND = {
  name: "FlowForm",
  logoSrc: "/FlowForm_logo.png",
} as const;

export const PUBLIC_NAV_LINKS = [
  { href: "/#features", label: "Features" },
  { href: "/#security", label: "Security" },
  { href: "/#pricing", label: "Pricing" },
  { href: "/docs/introduction", label: "Docs" },
] as const;

export const STUDIO_NAV_LINKS = [
  { to: "/", label: "Dashboard" },
  { to: "/surveys", label: "Surveys" },
] as const;

export const THEME_STORAGE_KEY = "flowform.theme";
