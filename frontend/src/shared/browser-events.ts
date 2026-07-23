export const PAGE_RENDERED_EVENT = "jobhunter:page-rendered";

export interface PageRenderedDetail {
  page: string;
}

export function notifyPageRendered(windowObject: Window, page: string): void {
  windowObject.dispatchEvent(
    new CustomEvent<PageRenderedDetail>(PAGE_RENDERED_EVENT, {
      detail: { page },
    }),
  );
}

export function subscribeToRenderedPage(
  windowObject: Window,
  listener: (page: string) => void,
): () => void {
  const handlePageRendered = (event: Event) => {
    const page = (event as CustomEvent<PageRenderedDetail>).detail?.page;
    if (page) listener(page);
  };
  windowObject.addEventListener(PAGE_RENDERED_EVENT, handlePageRendered);
  return () => windowObject.removeEventListener(PAGE_RENDERED_EVENT, handlePageRendered);
}
