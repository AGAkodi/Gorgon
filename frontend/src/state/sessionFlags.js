// In-memory session state — intentionally NOT localStorage/sessionStorage.
// Module-level so it survives client-side route changes but resets
// naturally on a full page reload (a reload is effectively a new session).
export const sessionFlags = {
  ribbonMorphed: false,
}
