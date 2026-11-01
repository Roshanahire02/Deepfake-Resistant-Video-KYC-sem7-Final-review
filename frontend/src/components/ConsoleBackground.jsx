// Mounted once at the app root. Purely decorative, fixed-position,
// z-index behind all content -- never intercepts clicks or affects
// layout. Respects prefers-reduced-motion via CSS (see index.css).
export default function ConsoleBackground() {
  return (
    <>
      <div className="console-bg drift-slow" aria-hidden="true" />
      <div className="console-grid" aria-hidden="true" />
    </>
  )
}
