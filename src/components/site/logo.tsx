/**
 * DeYoung brand mark - bold D with a play-triangle counter.
 * Cinematic red gradient (#FF6A5E → #E11D2E → #8F0E1E) with a top bevel.
 * Matches public/logo.svg and the app icon set.
 */
export function LogoMark({ className = "h-6 w-6" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 1024 1024"
      className={className}
      aria-hidden="true"
      focusable="false"
    >
      <defs>
        <linearGradient id="dy-dg" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#FF6A5E" />
          <stop offset="0.45" stopColor="#E11D2E" />
          <stop offset="1" stopColor="#8F0E1E" />
        </linearGradient>
      </defs>
      <path
        fill="url(#dy-dg)"
        fillRule="evenodd"
        d="M300 90 H520 C758 90 900 268 900 512 C900 756 758 934 520 934 H300 Z M462 296 L772 512 L462 728 Z"
      />
      <path
        fill="#FFFFFF"
        opacity="0.16"
        d="M300 90 H520 C636 90 731 124 806 196 C716 148 618 132 520 132 H300 Z"
      />
    </svg>
  );
}

/** Mark + wordmark lockup for headers and footers. */
export function Logo({
  name = "DeYoung",
  markClass = "h-7 w-7",
  textClass = "text-xl",
}: {
  name?: string;
  markClass?: string;
  textClass?: string;
}) {
  return (
    <span className="inline-flex items-center gap-2">
      <LogoMark className={markClass} />
      <span className={`font-black uppercase tracking-tight ${textClass}`}>{name}</span>
    </span>
  );
}
