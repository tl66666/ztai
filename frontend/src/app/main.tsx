import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { flushSync } from "react-dom";

import { JobHunterApp } from "./job-hunter-app";

const rootNode = document.getElementById("reactAppRoot");
if (!rootNode) throw new Error("Missing React composition root: #reactAppRoot");

const root = createRoot(rootNode);
flushSync(() => {
  root.render(
    <StrictMode>
      <JobHunterApp />
    </StrictMode>,
  );
});
