export interface CurrentUser {
  id: number;
  email: string;
  full_name: string;
  role: "super_admin" | "org_admin" | "manager" | "employee";
  department: string | null;
  organization_id: number | null;
}

export interface ModuleStatus {
  key: string;
  name: string;
  description: string;
  maturity: "production" | "prototype";
  enabled: boolean;
}
