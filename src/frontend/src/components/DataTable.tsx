// Candidate table with per-row searchable dropdowns (ported as-is).
import React, { useEffect, useState } from 'react';
import type { TableRowData } from '../types';
import { DescriptiveDropdown } from './DescriptiveDropdown';

const QuantityInput: React.FC<{
  initialValue: number;
  onCommit: (newValue: number) => void;
}> = ({ initialValue, onCommit }) => {
  const [displayValue, setDisplayValue] = useState<string>(String(initialValue));

  useEffect(() => {
    const currentNumericValue = parseFloat(displayValue.replace(',', '.')) || 0;
    if (initialValue !== currentNumericValue) {
      setDisplayValue(String(initialValue));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialValue]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setDisplayValue(e.target.value.replace(/[^0-9.,]/g, ''));
  };

  const handleBlur = () => {
    const numericValue = parseFloat(displayValue.replace(',', '.'));
    const finalValue = isNaN(numericValue) || numericValue < 0 ? 0 : numericValue;
    setDisplayValue(String(finalValue));
    onCommit(finalValue);
  };

  return (
    <input
      type="text"
      inputMode="decimal"
      value={displayValue}
      onChange={handleChange}
      onBlur={handleBlur}
      className="w-16 p-1 border border-gray-300 rounded-md text-sm text-center focus:ring-indigo-500 focus:border-indigo-500"
      placeholder="0"
    />
  );
};

interface DataTableProps {
  data: TableRowData[];
  onDescriptionChange: (rowId: string, newOptionId: string) => void;
  onQuantityChange: (rowId: string, newQuantity: number) => void;
  onDeleteRow: (rowId: string) => void;
}

export const DataTable: React.FC<DataTableProps> = ({
  data,
  onDescriptionChange,
  onQuantityChange,
  onDeleteRow,
}) => {
  return (
    <div className="shadow-xl rounded-lg overflow-hidden bg-white">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-800">
            <tr>
              <th scope="col" className="px-2 py-2 text-center text-xs font-semibold text-gray-100 uppercase tracking-wider w-[60px]">Borrar</th>
              <th scope="col" className="px-2 py-2 text-left text-xs font-semibold text-gray-100 uppercase tracking-wider w-[80px]">Uds.</th>
              <th scope="col" className="px-2 py-2 text-left text-xs font-semibold text-gray-100 uppercase tracking-wider">Artículo (Original)</th>
              <th scope="col" className="px-2 py-2 text-left text-xs font-semibold text-gray-100 uppercase tracking-wider">Descripción Catálogo (Seleccionar)</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-100">
            {data.map((row) => (
              <tr key={row.id} className="hover:bg-gray-50 transition-colors duration-150">
                <td className="px-1 py-1 whitespace-nowrap text-center align-middle">
                  <button
                    onClick={() => onDeleteRow(row.id)}
                    className="text-red-500 hover:text-red-700 p-2 rounded-full transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-opacity-50"
                    aria-label={`Eliminar fila ${row.originalArticleText}`}
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                        d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </td>
                <td className="px-1 py-1 whitespace-nowrap text-sm font-medium text-gray-700">
                  <QuantityInput
                    initialValue={row.finalQuantity}
                    onCommit={(newQty) => onQuantityChange(row.id, newQty)}
                  />
                </td>
                <td className="px-2 py-2 text-sm text-gray-700 align-top">
                  {row.originalArticleText}
                  {row.selectedCatalogId && row.selectedCatalogId !== '-' && (
                    <div className="text-xs text-gray-500 mt-0.5">ID: {row.selectedCatalogId}</div>
                  )}
                </td>
                <td className="px-1 py-1 text-sm text-gray-700 relative">
                  <DescriptiveDropdown
                    options={row.availableDescriptionOptions}
                    selectedOptionId={row.selectedDescriptionId}
                    onSelect={(newOptionId) => onDescriptionChange(row.id, newOptionId)}
                  />
                </td>
              </tr>
            ))}
            {data.length === 0 && (
              <tr>
                <td colSpan={4} className="px-6 py-10 text-center text-sm text-gray-500">
                  No hay artículos para seleccionar.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
