// Mirrors backend CurrentAffairsCategory (app/models/content.py) — keep in sync.
export const CATEGORIES: { value: string; label: string }[] = [
  { value: "polity_governance", label: "Polity & Governance" },
  { value: "economy", label: "Economy" },
  { value: "international_relations", label: "International Relations" },
  { value: "environment", label: "Environment" },
  { value: "science_tech", label: "Science & Technology" },
  { value: "history_culture", label: "History & Culture" },
  { value: "geography", label: "Geography" },
  { value: "social_issues", label: "Social Issues" },
  { value: "government_schemes", label: "Government Schemes" },
  { value: "defence", label: "Defence" },
  { value: "reports_indices", label: "Reports & Indices" },
  { value: "awards_appointments", label: "Awards & Appointments" },
  { value: "other", label: "Other" },
];

export const CATEGORY_LABEL: Record<string, string> = Object.fromEntries(
  CATEGORIES.map((c) => [c.value, c.label])
);
