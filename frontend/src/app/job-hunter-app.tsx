import { useEffect, useState } from "react";

import { subscribeToRenderedPage } from "../shared/browser-events";
import { Sidebar } from "../shell/sidebar";

function initialPage(windowObject: Window): string {
  return new URL(windowObject.location.href).searchParams.get("page") || "home";
}

export interface JobHunterAppProps {
  windowObject?: Window;
}

export function JobHunterApp({ windowObject = window }: JobHunterAppProps) {
  const [activePage, setActivePage] = useState(() => initialPage(windowObject));

  useEffect(
    () => subscribeToRenderedPage(windowObject, setActivePage),
    [windowObject],
  );

  return <Sidebar activePage={activePage} />;
}
