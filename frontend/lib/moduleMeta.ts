import { LineChart, Package, ShieldAlert, Users, Wrench, type LucideIcon } from "lucide-react";

export const MODULE_ROUTES: Record<string, string> = {
  bi_forecasting: "/dashboard/bi",
  inventory: "/dashboard/inventory",
  fraud: "/dashboard/fraud",
  maintenance: "/dashboard/maintenance",
  workforce: "/dashboard/workforce",
};

export const MODULE_ICONS: Record<string, LucideIcon> = {
  bi_forecasting: LineChart,
  inventory: Package,
  fraud: ShieldAlert,
  maintenance: Wrench,
  workforce: Users,
};
