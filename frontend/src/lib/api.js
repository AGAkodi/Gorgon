// Single source of truth for the backend's base URL. Defaults to local dev;
// set VITE_API_BASE_URL at build time (Vercel/Netlify/Cloudflare Pages env
// var) to point a deployed frontend at a deployed backend instead. Every
// fetch() to the auth gateway should import this rather than hardcode
// localhost — that hardcoding is exactly what silently breaks the moment
// either side is deployed somewhere that isn't your own laptop.
// Resolution order:
//  1. VITE_API_BASE_URL if set at build time (Option 1 — frontend on
//     Vercel/Netlify pointed at a separately-hosted backend).
//  2. Otherwise, in a production build, '' (same-origin, relative URLs) —
//     this is Option 2, where the FastAPI auth server serves this built
//     frontend itself, so /api/* is same-origin and needs no base URL.
//  3. Otherwise (local `vite dev`), the local backend on :4023.
export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ??
  (import.meta.env.PROD ? '' : 'http://localhost:4023')
