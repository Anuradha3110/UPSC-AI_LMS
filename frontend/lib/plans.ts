export type Plan = {
  id: string;
  label: string;
  price: number;
  quota: number;
};

export const PLANS: Plan[] = [
  { id: "free_diagnostic", label: "Free Diagnostic", price: 0, quota: 3 },
  { id: "prelims_only", label: "Prelims Only", price: 499, quota: 10 },
  { id: "full_prep", label: "Full Prep (Prelims + Mains + Interview)", price: 999, quota: 100 },
];

export function getPlan(id: string): Plan | undefined {
  return PLANS.find((p) => p.id === id);
}
