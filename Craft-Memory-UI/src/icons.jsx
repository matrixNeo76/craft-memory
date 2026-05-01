// Tiny line-icon set, 14px stroke, currentColor
const Icon = ({ name, size = 14, ...rest }) => {
  const common = {
    width: size, height: size, viewBox: "0 0 24 24",
    fill: "none", stroke: "currentColor", strokeWidth: 1.6,
    strokeLinecap: "round", strokeLinejoin: "round",
    ...rest
  };
  switch (name) {
    case "home":
      return <svg {...common}><path d="M3 11l9-7 9 7v9a1 1 0 0 1-1 1h-5v-6h-6v6H4a1 1 0 0 1-1-1z"/></svg>;
    case "dashboard":
      return <svg {...common}><rect x="3" y="3" width="7" height="9" rx="1"/><rect x="14" y="3" width="7" height="5" rx="1"/><rect x="14" y="12" width="7" height="9" rx="1"/><rect x="3" y="16" width="7" height="5" rx="1"/></svg>;
    case "search":
      return <svg {...common}><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>;
    case "graph":
      return <svg {...common}><circle cx="6" cy="6" r="2.5"/><circle cx="18" cy="7" r="2.5"/><circle cx="12" cy="18" r="2.5"/><path d="M8 7l8 0M7.5 8l4 8M16.5 9l-3.5 8"/></svg>;
    case "loops":
      return <svg {...common}><rect x="3" y="4" width="6" height="16" rx="1"/><rect x="11" y="4" width="6" height="10" rx="1"/><rect x="19" y="4" width="2" height="6" rx="1"/></svg>;
    case "handoff":
      return <svg {...common}><path d="M3 6h13l-3-3M21 18H8l3 3"/></svg>;
    case "diff":
      return <svg {...common}><path d="M5 4v16M19 4v16M9 8h6M9 12h6M9 16h6"/></svg>;
    case "settings":
      return <svg {...common}><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 0 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 0 1 0-4h.1A1.7 1.7 0 0 0 4.6 9a1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 0 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 0 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/></svg>;
    case "spark":
      return <svg {...common}><path d="M12 3v4M12 17v4M3 12h4M17 12h4M5.6 5.6l2.8 2.8M15.6 15.6l2.8 2.8M5.6 18.4l2.8-2.8M15.6 8.4l2.8-2.8"/></svg>;
    case "fact":
      return <svg {...common}><path d="M4 5h16M4 12h16M4 19h10"/></svg>;
    case "loop":
      return <svg {...common}><path d="M21 12a9 9 0 0 1-9 9M3 12a9 9 0 0 1 9-9M21 12l-3-3M3 12l3 3"/></svg>;
    case "tag":
      return <svg {...common}><path d="M20 13l-7 7-9-9V4h7z"/><circle cx="8" cy="8" r="1.4"/></svg>;
    case "clock":
      return <svg {...common}><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>;
    case "decision":
      return <svg {...common}><path d="M3 12l4-4h10l4 4-4 4H7z"/></svg>;
    case "discovery":
      return <svg {...common}><circle cx="12" cy="12" r="9"/><path d="m9 9 6 1.5L13.5 16 7 14.5z"/></svg>;
    case "bugfix":
      return <svg {...common}><path d="M9 4l3 3 3-3M5 13a7 7 0 0 0 14 0v-1H5zM5 12V8M19 12V8M3 16l3-1M21 16l-3-1M3 20l4-2M21 20l-4-2"/></svg>;
    case "feature":
      return <svg {...common}><path d="M12 2l2.5 6.5L21 11l-6.5 2.5L12 20l-2.5-6.5L3 11l6.5-2.5z"/></svg>;
    case "refactor":
      return <svg {...common}><path d="M4 4l6 6-6 6M14 4l6 6-6 6"/></svg>;
    case "change":
      return <svg {...common}><path d="M4 7h11l-3-3M20 17H9l3 3"/></svg>;
    case "note":
      return <svg {...common}><rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 8h8M8 12h8M8 16h5"/></svg>;
    case "plus":
      return <svg {...common}><path d="M12 5v14M5 12h14"/></svg>;
    case "filter":
      return <svg {...common}><path d="M4 5h16l-6 8v6l-4-2v-4z"/></svg>;
    case "chevron":
      return <svg {...common}><path d="m9 6 6 6-6 6"/></svg>;
    case "arrow":
      return <svg {...common}><path d="M5 12h14M13 5l7 7-7 7"/></svg>;
    case "external":
      return <svg {...common}><path d="M14 4h6v6M20 4 10 14M19 13v6a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1h6"/></svg>;
    case "core":
      return <svg {...common}><circle cx="12" cy="12" r="3"/><circle cx="12" cy="12" r="8" strokeDasharray="2 3"/></svg>;
    case "link":
      return <svg {...common}><path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/></svg>;
    case "x":
      return <svg {...common}><path d="m6 6 12 12M18 6 6 18"/></svg>;
    case "play":
      return <svg {...common}><path d="M6 4l14 8-14 8z"/></svg>;
    case "github":
      return <svg {...common}><path d="M12 2a10 10 0 0 0-3.2 19.5c.5.1.7-.2.7-.5v-1.7c-2.8.6-3.4-1.2-3.4-1.2-.5-1.2-1.1-1.5-1.1-1.5-.9-.6.1-.6.1-.6 1 .1 1.5 1 1.5 1 .9 1.5 2.4 1.1 3 .8.1-.7.4-1.1.6-1.4-2.2-.3-4.5-1.1-4.5-5 0-1.1.4-2 1-2.7-.1-.3-.4-1.3.1-2.7 0 0 .8-.3 2.7 1a9.4 9.4 0 0 1 5 0c1.9-1.3 2.7-1 2.7-1 .5 1.4.2 2.4.1 2.7.6.7 1 1.6 1 2.7 0 3.9-2.4 4.7-4.6 5 .4.3.7.9.7 1.8v2.7c0 .3.2.6.7.5A10 10 0 0 0 12 2z"/></svg>;
    default:
      return <svg {...common}><circle cx="12" cy="12" r="9"/></svg>;
  }
};

window.Icon = Icon;
