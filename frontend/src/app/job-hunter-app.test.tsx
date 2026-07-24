import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { notifyPageRendered } from "../shared/browser-events";
import { JobHunterApp } from "./job-hunter-app";

describe("React composition root", () => {
  let root: Root;
  let host: HTMLElement;

  beforeEach(() => {
    (globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;
    window.history.replaceState({}, "", "/");
    host = document.createElement("div");
    document.body.append(host);
    root = createRoot(host);
  });

  afterEach(() => {
    act(() => root.unmount());
    document.body.innerHTML = "";
  });

  it("renders the existing navigation semantics and Chinese product labels", () => {
    act(() => root.render(<JobHunterApp />));

    expect(host.querySelector("nav")?.getAttribute("aria-label")).toBe("主导航");
    expect(host.querySelectorAll("[data-page]")).toHaveLength(6);
    expect(host.textContent).toContain("简历实验室");
    expect(host.textContent).toContain("面试训练场");
    expect(host.textContent).toContain("求职指挥台");
    expect(
      host.querySelector(".nav-item[data-page='home']")?.getAttribute("aria-current"),
    ).toBe("page");
  });

  it("tracks the route rendered by the legacy history adapter during migration", () => {
    act(() => root.render(<JobHunterApp />));

    act(() => notifyPageRendered(window, "tracker"));

    expect(host.querySelector(".nav-item[data-page='tracker']")?.classList).toContain("active");
    expect(
      host.querySelector(".nav-item[data-page='tracker']")?.getAttribute("aria-current"),
    ).toBe("page");
    expect(
      host.querySelector(".nav-item[data-page='home']")?.hasAttribute("aria-current"),
    ).toBe(false);
  });
});
