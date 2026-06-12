// Mirror of the backend Pydantic contracts (src/backend/app/models/order_models.py).
// The accented keys (CANTIDAD/ARTÍCULO/DESCRIPCIÓN, Descripción, Artículo) are part of
// the wire contract ported from the original system — do not rename.

export interface InitialOrderItem {
  CANTIDAD: number;
  'ARTÍCULO': string;
  'DESCRIPCIÓN': string;
}

export interface ProcessAudioResponse {
  transcription: string;
  num_order: string | null;
  planta_name: string | null;
  planta_name_source: 'llm' | 'erp';
  observaciones: string | null;
  warnings: string[];
  articles_list_original_text: string[];
  df_order_json: InitialOrderItem[];
  message?: string | null;
}

export interface SearchArticlesRequest {
  articles_list_original_text: string[];
  description_list_for_search: string[];
  num_opciones_busqueda?: number;
  historical_threshold?: number;
  catalog_threshold?: number;
}

export interface SearchedArticleItem {
  Article: string;
  Ids: string;
  Description: string;
  Score: number;
  Date_score: number;
  Fecha_ultima_compra: string | null;
  Historical_match: boolean;
}

export interface SearchArticlesResponse {
  searched_articles: SearchedArticleItem[];
  message?: string | null;
}

export interface UserSelectedItem {
  original_article_text: string;
  selected_catalog_description: string;
  selected_catalog_id: string;
  quantity: number;
}

export interface FinalizeOrderRequest {
  selected_items: UserSelectedItem[];
  num_order: string | null;
  planta_name: string | null;
  plazo: string | null;
}

export interface FinalOrderLineItem {
  Uds: number;
  Ids: string;
  'Descripción': string;
}

export interface FinalizeOrderResponse {
  final_order_items: FinalOrderLineItem[];
  has_duplicates_or_issues: boolean;
  warnings: string[];
  message?: string | null;
}

export interface ItemForHistory {
  Ids: string;
  'Artículo': string;
  'Descripción': string;
}

export interface PDFDownloadData {
  b64_pdf: string;
  filename: string;
  content_type: string;
}

export interface SendOrderRequest {
  final_order_items: FinalOrderLineItem[];
  items_for_history: ItemForHistory[];
  num_order: string | null;
  planta_name: string | null;
  plazo: string | null;
  observaciones: string | null;
  enviar_a_obra?: boolean;
  solo_imputar?: boolean;
}

export interface SendOrderResponse {
  order_sent_status: string;
  historical_update_status: string | null;
  historical_update_message: string | null;
  erp_update_status?: string | null;
  erp_update_message?: string | null;
  pdf_download_data: PDFDownloadData | null;
  message: string;
  error_details: string | null;
}

export interface CatalogItem {
  id_articulo: string;
  articulo: string;
}

export interface DemoRecording {
  recording_id: number;
  transcription: string;
  n_items: number;
}
