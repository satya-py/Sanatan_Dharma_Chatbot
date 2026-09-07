/// <reference types="vite/client" />

interface ImportMetaEnv {
  /**
   * Backend origin, e.g. https://sanatan-dharma-chatbot-10.onrender.com
   * Exposed to client code by the API_ entry in envPrefix (vite.config.ts).
   */
  readonly API_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
