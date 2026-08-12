// `server-only` throws unconditionally when imported outside Next.js's webpack RSC
// boundary — which is exactly what happens every time Vitest (a plain Vite runtime, not
// Next's build) loads a Route Handler or lib module that imports it transitively. Next's
// own bundler special-cases this import to enforce the client/server boundary at build
// time; Vitest has no equivalent concept, so unit tests alias it to a no-op instead.
export {};
