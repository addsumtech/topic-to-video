// The bundler emits font files as asset URLs; this declares the import so the type layer agrees.
declare module '*.ttf' {
  const src: string;
  export default src;
}
