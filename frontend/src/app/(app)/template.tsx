// template.tsx re-mounts on every client navigation (unlike layout.tsx), so it's
// the right place to replay a per-page entrance animation. The wrapper fades the
// page content in (opacity only — no transform, to avoid disturbing the Leaflet
// map's rendering). Base opacity stays 1, so if the animation doesn't run
// (prefers-reduced-motion) the content is simply shown. See globals.css.
export default function Template({ children }: { children: React.ReactNode }) {
  return <div className="animate-page-in">{children}</div>;
}
