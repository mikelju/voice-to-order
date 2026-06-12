/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_FASTAPI_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
