export type View = "dashboard" | "new" | "results" | "related" | "campaign" | "details";

const views: View[] = ["dashboard", "new", "results", "related", "campaign", "details"];

export function viewFromHash(hash: string): View {
  const value = hash.replace(/^#/, "");
  return views.includes(value as View) ? (value as View) : "dashboard";
}
