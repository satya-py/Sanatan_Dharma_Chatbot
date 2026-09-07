/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Backend origin, e.g. https://sanatan-dharma-chatbot-10.onrender.com */
  readonly VITE_API_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
