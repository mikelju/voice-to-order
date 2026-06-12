// UI row model for the candidate table (ported).

export interface Option {
  id: string;
  label: string;
}

export interface TableRowData {
  id: string;
  originalArticleText: string;
  originalQuantitySuggestion: number | string;
  finalQuantity: number;
  selectedDescriptionId?: string;
  availableDescriptionOptions: Option[];
  selectedCatalogId?: string;
}
