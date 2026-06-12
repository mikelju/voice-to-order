// Step 3: orchestrates the candidate search and the editable table (ported).
// Replica fix (recorded in the spec): confirming selections excludes sentinel rows
// (id '-') — the original would send them.
import React, { useCallback, useEffect, useState } from 'react';
import { searchArticles } from '../api/apiService';
import type { CatalogItem, ProcessAudioResponse, UserSelectedItem } from '../types/api_models';
import type { Option, TableRowData } from '../types';
import { CatalogSearchModal } from './CatalogSearchModal';
import { DataTable } from './DataTable';

const SENTINEL: Option = { id: '-', label: '--- SIN OPCIONES ---' };

interface ArticleSelectorProps {
  initialOrderData: ProcessAudioResponse;
  onSelectionsConfirmed: (selections: UserSelectedItem[]) => void;
  onGoBack: () => void;
}

export const ArticleSelector: React.FC<ArticleSelectorProps> = ({
  initialOrderData,
  onSelectionsConfirmed,
  onGoBack,
}) => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tableDisplayData, setTableDisplayData] = useState<TableRowData[]>([]);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const fetchAndPrepareData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const payload = {
        articles_list_original_text: initialOrderData.articles_list_original_text,
        description_list_for_search: initialOrderData.df_order_json.map(
          (item) => item['DESCRIPCIÓN'],
        ),
      };
      const response = await searchArticles(payload);
      const newTableDisplayData: TableRowData[] = initialOrderData.df_order_json.map(
        (initialItem, index) => {
          const relevantSearches = response.searched_articles.filter(
            (searchItem) => searchItem.Article === initialItem['ARTÍCULO'],
          );
          const options: Option[] = relevantSearches.map((sr) => ({
            id: sr.Ids,
            label: sr.Description,
          }));
          const defaultSelectedOption = options.length > 0 ? options[0] : SENTINEL;
          if (options.length === 0) options.push(SENTINEL);
          const suggestedQty = parseFloat(String(initialItem.CANTIDAD)) || 1;
          return {
            id: `row_${initialItem['ARTÍCULO'].replace(/\s+/g, '_')}_${index}`,
            originalArticleText: initialItem['ARTÍCULO'],
            originalQuantitySuggestion: suggestedQty,
            finalQuantity: suggestedQty,
            availableDescriptionOptions: options,
            selectedDescriptionId: defaultSelectedOption.id,
            selectedCatalogId: defaultSelectedOption.id,
          };
        },
      );
      setTableDisplayData(newTableDisplayData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error buscando artículos');
    } finally {
      setIsLoading(false);
    }
  }, [initialOrderData]);

  useEffect(() => {
    fetchAndPrepareData();
  }, [fetchAndPrepareData]);

  const handleDescriptionChange = (rowId: string, newOptionId: string) => {
    setTableDisplayData((rows) =>
      rows.map((row) =>
        row.id === rowId
          ? { ...row, selectedDescriptionId: newOptionId, selectedCatalogId: newOptionId }
          : row,
      ),
    );
  };

  const handleQuantityChange = (rowId: string, newQuantity: number) => {
    setTableDisplayData((rows) =>
      rows.map((row) => (row.id === rowId ? { ...row, finalQuantity: newQuantity } : row)),
    );
  };

  const handleDeleteRow = (rowId: string) => {
    setTableDisplayData((rows) => rows.filter((row) => row.id !== rowId));
  };

  const handleAddManualArticle = (article: CatalogItem, quantity: number) => {
    setTableDisplayData((rows) => {
      if (rows.some((row) => row.selectedCatalogId === article.id_articulo)) {
        setError('Ese artículo ya está en el pedido.');
        setTimeout(() => setError(null), 3000);
        return rows;
      }
      const option: Option = { id: article.id_articulo, label: article.articulo };
      return [
        ...rows,
        {
          id: `manual_row_${article.id_articulo}_${Date.now()}`,
          originalArticleText: `(Manual) ${article.articulo.substring(0, 40)}...`,
          originalQuantitySuggestion: quantity,
          finalQuantity: quantity,
          availableDescriptionOptions: [option],
          selectedDescriptionId: option.id,
          selectedCatalogId: option.id,
        },
      ];
    });
  };

  const handleConfirmSelections = () => {
    const selections: UserSelectedItem[] = tableDisplayData
      // replica fix: exclude the '--- SIN OPCIONES ---' sentinel rows
      .filter(
        (row) => row.selectedCatalogId && row.selectedCatalogId !== '-' && row.finalQuantity > 0,
      )
      .map((row) => ({
        original_article_text: row.originalArticleText,
        selected_catalog_description:
          row.availableDescriptionOptions.find((opt) => opt.id === row.selectedDescriptionId)
            ?.label || 'N/A',
        selected_catalog_id: row.selectedCatalogId!,
        quantity: row.finalQuantity,
      }));
    if (selections.length === 0) {
      setError('No hay líneas válidas seleccionadas.');
      setTimeout(() => setError(null), 3000);
      return;
    }
    onSelectionsConfirmed(selections);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-gray-800">Seleccionar artículos del catálogo</h2>
        <button onClick={onGoBack} className="text-sm text-indigo-600 hover:underline">← Volver</button>
      </div>
      {error && (
        <div className="bg-red-50 border-l-4 border-red-400 px-3 py-2 rounded text-sm text-red-700">
          {error}
        </div>
      )}
      {isLoading ? (
        <p className="text-sm text-gray-500 py-8 text-center">
          Buscando candidatos (memoria aprendida + catálogo, búsqueda vectorial)...
        </p>
      ) : (
        <>
          <DataTable
            data={tableDisplayData}
            onDescriptionChange={handleDescriptionChange}
            onQuantityChange={handleQuantityChange}
            onDeleteRow={handleDeleteRow}
          />
          <div className="flex items-center justify-between">
            <button
              onClick={() => setIsModalOpen(true)}
              className="px-4 py-2 text-sm text-indigo-700 bg-indigo-50 rounded-md hover:bg-indigo-100"
            >
              + Añadir manualmente del catálogo
            </button>
            <button
              onClick={handleConfirmSelections}
              className="px-5 py-2 bg-indigo-600 text-white text-sm font-medium rounded-md hover:bg-indigo-700"
            >
              Confirmar selección →
            </button>
          </div>
        </>
      )}
      <CatalogSearchModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onArticleSelect={handleAddManualArticle}
      />
    </div>
  );
};
