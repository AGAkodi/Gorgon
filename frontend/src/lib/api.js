// Single source of truth for the backend's base URL. Defaults to local dev;
// set VITE_API_BASE_URL at build time (Vercel/Netlify/Cloudflare Pages env
// var) to point a deployed frontend at a deployed backend instead. Every
// fetch() to the auth gateway should import this rather than hardcode
// localhost — that hardcoding is exactly what silently breaks the moment
// either side is deployed somewhere that isn't your own laptop.
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:4023'
