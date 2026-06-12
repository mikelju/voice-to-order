// API layer ported from the original (fetch + FastAPI `detail` error pattern).
// Replica difference: no auth headers — the public replica has no login layer.
import type {
  CatalogItem,
  DemoRecording,
  FinalizeOrderRequest,
  FinalizeOrderResponse,
  ProcessAudioResponse,
  SearchArticlesRequest,
  SearchArticlesResponse,
  SendOrderRequest,
  SendOrderResponse,
} from '../types/api_models';

const API_BASE_URL = import.meta.env.VITE_FASTAPI_BASE_URL || 'http://127.0.0.1:8000/api/v1';

async function throwApiError(response: Response): Promise<never> {
  let errorData: { detail?: string };
  try {
    errorData = await response.json();
  } catch {
    errorData = { detail: `HTTP error! status: ${response.status}, ${response.statusText}` };
  }
  throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
}

export async function getDemoRecordings(): Promise<DemoRecording[]> {
  const response = await fetch(`${API_BASE_URL}/demo/recordings`);
  if (!response.ok) {
    if (response.status === 404) return []; // real mode: no demo picker
    await throwApiError(response);
  }
  return response.json();
}

export async function processAudio(
  audioFile: File,
  recordingId?: number,
): Promise<ProcessAudioResponse> {
  const formData = new FormData();
  formData.append('audio_file', audioFile);
  if (recordingId !== undefined) {
    formData.append('recording_id', String(recordingId));
  }
  // IMPORTANTE: no fijar Content-Type con FormData, lo hace el navegador.
  const response = await fetch(`${API_BASE_URL}/orders/process-audio`, {
    method: 'POST',
    body: formData,
  });
  if (!response.ok) await throwApiError(response);
  return response.json();
}

export async function searchArticles(
  payload: SearchArticlesRequest,
): Promise<SearchArticlesResponse> {
  const response = await fetch(`${API_BASE_URL}/orders/search-articles`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) await throwApiError(response);
  return response.json();
}

export async function finalizeOrder(
  payload: FinalizeOrderRequest,
): Promise<FinalizeOrderResponse> {
  const response = await fetch(`${API_BASE_URL}/orders/finalize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) await throwApiError(response);
  return response.json();
}

export async function sendOrder(payload: SendOrderRequest): Promise<SendOrderResponse> {
  const response = await fetch(`${API_BASE_URL}/orders/send`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) await throwApiError(response);
  return response.json();
}

export async function searchFullCatalog(query: string): Promise<CatalogItem[]> {
  if (!query || query.trim().length < 3) return [];
  const response = await fetch(
    `${API_BASE_URL}/catalog/search?query=${encodeURIComponent(query)}`,
  );
  if (!response.ok) await throwApiError(response);
  return response.json();
}

// 404 does NOT throw: the component decides by the `status` field (ported).
export async function getPlantaByOrderId(
  orderId: string,
): Promise<{ status: string; planta_name?: string | null; message?: string }> {
  const response = await fetch(`${API_BASE_URL}/orders/get-planta/${orderId}`);
  if (!response.ok && response.status !== 404) {
    await throwApiError(response);
  }
  return response.json();
}
