import type { LucideIcon } from "lucide-react";
import FileUser from "lucide-react/dist/esm/icons/file-user.mjs";
import KanbanSquare from "lucide-react/dist/esm/icons/kanban-square.mjs";
import LayoutDashboard from "lucide-react/dist/esm/icons/layout-dashboard.mjs";
import MessagesSquare from "lucide-react/dist/esm/icons/messages-square.mjs";
import Sparkles from "lucide-react/dist/esm/icons/sparkles.mjs";

export interface NavigationItem {
  page: string;
  label: string;
  icon: LucideIcon;
}

export const NAVIGATION_ITEMS: readonly NavigationItem[] = [
  { page: "home", label: "项目总览", icon: Sparkles },
  { page: "resume", label: "简历实验室", icon: FileUser },
  { page: "interview", label: "面试训练场", icon: MessagesSquare },
  { page: "tracker", label: "投递看板", icon: KanbanSquare },
  { page: "agent", label: "求职指挥台", icon: LayoutDashboard },
];
