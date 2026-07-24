import { NAVIGATION_ITEMS } from "./navigation-model";

export interface SidebarProps {
  activePage: string;
}

export function Sidebar({ activePage }: SidebarProps) {
  return (
    <aside className="sidebar">
      <button className="brand" data-page="home" type="button">
        <img id="brandLogo" src="/assets/images/logo%20(2).png" alt="职途AI" />
        <span>职途<br /><strong>AI</strong></span>
      </button>
      <nav className="nav" aria-label="主导航">
        {NAVIGATION_ITEMS.map(({ page, label, icon: Icon }) => (
          <button
            className={`nav-item${activePage === page ? " active" : ""}`}
            data-page={page}
            type="button"
            aria-current={activePage === page ? "page" : undefined}
            key={page}
          >
            <Icon aria-hidden="true" />
            <span>{label}</span>
          </button>
        ))}
      </nav>
      <div className="provider-mini">
        <span id="providerDot" />
        <div>
          <b id="providerName">本地兜底</b>
          <small id="providerModel">规则引擎可用</small>
        </div>
      </div>
    </aside>
  );
}
