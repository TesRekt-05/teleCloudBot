
/// <reference types="vite/client" />

// Declare CSS module types
declare module '*.css' {
  const content: string;
  export default content;
}
