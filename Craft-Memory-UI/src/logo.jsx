// Cleaned-up "A" mark inspired by the reference image:
// stencil A (with horizontal break) inside concentric circular arcs.
// Everything is geometric primitives — no hand-drawn imagery.
const LogoMark = ({ size = 28, glow = true }) => {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" fill="none" aria-label="Craft Memory">
      <defs>
        <linearGradient id="cm-grad" x1="0" y1="0" x2="64" y2="64" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="oklch(0.95 0.05 var(--accent-h))" />
          <stop offset="1" stopColor="oklch(0.78 0.18 var(--accent-h))" />
        </linearGradient>
        <filter id="cm-glow" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="1.4" />
        </filter>
      </defs>
      {/* outer dotted arc */}
      <circle cx="32" cy="32" r="28" stroke="var(--accent)" strokeWidth="1" strokeDasharray="1 4" opacity="0.55" />
      {/* mid arc, broken */}
      <path d="M 8 32 A 24 24 0 0 1 56 32" stroke="var(--accent)" strokeWidth="1.4" strokeLinecap="round" opacity="0.7" />
      <path d="M 12 38 A 22 22 0 0 0 52 38" stroke="var(--accent-2)" strokeWidth="1" strokeLinecap="round" opacity="0.5" />
      {/* node dots on arcs */}
      <circle cx="6" cy="32" r="1.6" fill="var(--accent)" />
      <circle cx="58" cy="32" r="1.6" fill="var(--accent-2)" />
      <circle cx="32" cy="4.5" r="1.4" fill="var(--accent)" opacity="0.7" />
      {/* the A — stencil */}
      <g filter={glow ? "url(#cm-glow)" : undefined} opacity={glow ? 0.45 : 0}>
        <path d="M 18 48 L 32 16 L 46 48 M 23 38 L 41 38" stroke="url(#cm-grad)" strokeWidth="5" strokeLinecap="round" strokeLinejoin="round" fill="none" />
      </g>
      <path d="M 18 48 L 32 16 L 46 48 M 23 38 L 41 38" stroke="url(#cm-grad)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" fill="none" />
      {/* horizontal stencil cut on right leg */}
      <line x1="38" y1="32" x2="42" y2="32" stroke="var(--bg-0)" strokeWidth="3.5" />
      {/* center dot */}
      <circle cx="32" cy="44" r="1.4" fill="var(--accent)" />
    </svg>
  );
};

// Big hero version — for home screen
const LogoHero = ({ size = 320 }) => {
  return (
    <svg width={size} height={size} viewBox="0 0 320 320" fill="none">
      <defs>
        <linearGradient id="cm-hero-grad" x1="0" y1="0" x2="320" y2="320" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="oklch(0.97 0.04 var(--accent-h))" />
          <stop offset="0.5" stopColor="oklch(0.85 0.16 var(--accent-h))" />
          <stop offset="1" stopColor="oklch(0.7 0.20 calc(var(--accent-h) + 20))" />
        </linearGradient>
        <radialGradient id="cm-hero-glow" cx="50%" cy="50%" r="50%">
          <stop offset="0" stopColor="oklch(0.78 0.18 var(--accent-h))" stopOpacity="0.6" />
          <stop offset="1" stopColor="oklch(0.78 0.18 var(--accent-h))" stopOpacity="0" />
        </radialGradient>
        <filter id="cm-hero-blur" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="6" />
        </filter>
      </defs>
      {/* glow pool */}
      <circle cx="160" cy="160" r="140" fill="url(#cm-hero-glow)" />
      {/* outer rings */}
      <circle cx="160" cy="160" r="148" stroke="var(--accent)" strokeWidth="1" strokeDasharray="1 6" opacity="0.45" />
      <circle cx="160" cy="160" r="135" stroke="var(--accent)" strokeWidth="1" strokeDasharray="2 10" opacity="0.5" />
      {/* main arcs */}
      <path d="M 30 160 A 130 130 0 0 1 290 160" stroke="var(--accent)" strokeWidth="1.5" strokeLinecap="round" opacity="0.65" />
      <path d="M 50 188 A 116 116 0 0 0 270 188" stroke="var(--accent-2)" strokeWidth="1" strokeLinecap="round" opacity="0.45" />
      <path d="M 70 132 A 98 98 0 0 1 250 132" stroke="var(--accent)" strokeWidth="0.8" strokeLinecap="round" opacity="0.35" />
      {/* node dots */}
      <circle cx="26" cy="160" r="3.5" fill="var(--accent)" />
      <circle cx="294" cy="160" r="3.5" fill="var(--accent-2)" />
      <circle cx="160" cy="22" r="3" fill="var(--accent)" opacity="0.7" />
      <circle cx="80" cy="60" r="2" fill="var(--accent-2)" opacity="0.6" />
      <circle cx="240" cy="60" r="2" fill="var(--accent)" opacity="0.6" />
      <circle cx="80" cy="260" r="2" fill="var(--accent-2)" opacity="0.5" />
      <circle cx="240" cy="260" r="2" fill="var(--accent)" opacity="0.5" />
      {/* tick marks */}
      {Array.from({length: 24}).map((_, i) => {
        const a = (i / 24) * Math.PI * 2 - Math.PI/2;
        const r1 = 154, r2 = 158;
        return <line key={i}
          x1={160 + Math.cos(a)*r1} y1={160 + Math.sin(a)*r1}
          x2={160 + Math.cos(a)*r2} y2={160 + Math.sin(a)*r2}
          stroke="var(--accent)" strokeWidth="1" opacity="0.4" />;
      })}
      {/* glow A */}
      <g filter="url(#cm-hero-blur)" opacity="0.55">
        <path d="M 90 240 L 160 80 L 230 240 M 115 190 L 205 190" stroke="url(#cm-hero-grad)" strokeWidth="22" strokeLinecap="round" strokeLinejoin="round" fill="none" />
      </g>
      {/* solid A */}
      <path d="M 90 240 L 160 80 L 230 240 M 115 190 L 205 190" stroke="url(#cm-hero-grad)" strokeWidth="14" strokeLinecap="round" strokeLinejoin="round" fill="none" />
      {/* stencil cuts */}
      <line x1="184" y1="160" x2="200" y2="160" stroke="var(--bg-0)" strokeWidth="14" />
      <line x1="120" y1="160" x2="136" y2="160" stroke="var(--bg-0)" strokeWidth="14" />
      {/* center dot */}
      <circle cx="160" cy="220" r="3" fill="var(--accent)" />
      <circle cx="160" cy="220" r="6" fill="none" stroke="var(--accent)" opacity="0.4" />
    </svg>
  );
};

window.LogoMark = LogoMark;
window.LogoHero = LogoHero;
