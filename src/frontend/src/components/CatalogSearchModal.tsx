// Manual-add modal: full-catalog search with 500ms debounce (ported, minus stray code).
import React, { useEffect, useState } from 'react';
import { searchFullCatalog } from '../api/apiService';
import { useDebounce } from '../hooks/useDebounce';
import type { CatalogItem } from '../types/api_models';

interface CatalogSearchModalProps {
  isOpen: boolean;
  onClose: () => void;
  onArticleSelect: (article: CatalogItem, quantity: number) => void;
}

export const CatalogSearchModal: React.FC<CatalogSearchModalProps> = ({
  isOpen,
  onClose,
  onArticleSelect,
}) => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<CatalogItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedArticle, setSelectedArticle] = useState<CatalogItem | null>(null);
  const [quantity, setQuantity] = useState('1');
  const debouncedQuery = useDebounce(query, 500);

  useEffect(() => {
    if (!isOpen) return;
    let cancelled = false;
    const run = async () => {
      if (debouncedQuery.trim().length < 3) {
        setResults([]);
        return;
      }
      setIsLoading(true);
      try {
        const items = await searchFullCatalog(debouncedQuery);
        if (!cancelled) setResults(items);
      } catch (err) {
        console.error('Catalog search failed:', err);
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    };
    run();
    return () => {
      cancelled = true;
    };
  }, [debouncedQuery, isOpen]);

  const handleClose = () => {
    setQuery('');
    setResults([]);
    setSelectedArticle(null);
    setQuantity('1');
    onClose();
  };

  const handleConfirm = () => {
    if (!selectedArticle) return;
    const qty = parseFloat(quantity.replace(',', '.'));
    if (isNaN(qty) || qty <= 0) return;
    onArticleSelect(selectedArticle, qty);
    handleClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-gray-900/70 p-4">
      <div className="bg-white rounded-lg shadow-2xl w-full max-w-2xl max-h-[85vh] flex flex-col">
        <div className="flex items-center justify-between px-5 py-3 border-b">
          <h3 className="text-lg font-semibold text-gray-800">Buscar en el catálogo</h3>
          <button onClick={handleClose} className="text-gray-400 hover:text-gray-600 text-2xl leading-none">×</button>
        </div>
        <div className="p-5 space-y-3 overflow-y-auto custom-scrollbar">
          <input
            type="search"
            autoFocus
            placeholder="Escribe al menos 3 caracteres..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-indigo-500 focus:border-indigo-500"
          />
          {isLoading && <p className="text-sm text-gray-500">Buscando...</p>}
          <ul className="divide-y divide-gray-100 border border-gray-100 rounded-md max-h-64 overflow-y-auto custom-scrollbar">
            {results.map((item) => (
              <li
                key={item.id_articulo}
                onClick={() => setSelectedArticle(item)}
                className={`px-3 py-2 text-sm cursor-pointer ${
                  selectedArticle?.id_articulo === item.id_articulo
                    ? 'bg-indigo-50 text-indigo-700 font-medium'
                    : 'hover:bg-gray-50 text-gray-700'
                }`}
              >
                {item.articulo}
                <span className="block text-xs text-gray-400">{item.id_articulo}</span>
              </li>
            ))}
            {!isLoading && results.length === 0 && debouncedQuery.trim().length >= 3 && (
              <li className="px-3 py-3 text-sm text-gray-400">Sin resultados.</li>
            )}
          </ul>
          {selectedArticle && (
            <div className="flex items-center gap-3 pt-2">
              <label className="text-sm text-gray-600">Cantidad:</label>
              <input
                type="text"
                inputMode="decimal"
                value={quantity}
                onChange={(e) => {
                  if (/^[0-9.,]*$/.test(e.target.value)) setQuantity(e.target.value);
                }}
                className="w-24 px-2 py-1 border border-gray-300 rounded-md text-sm text-center"
              />
              <button
                onClick={handleConfirm}
                className="ml-auto px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-md hover:bg-indigo-700"
              >
                Añadir al pedido
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
