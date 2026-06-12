// Step 5: summary + send. Navigation gated on pdf_download_data (ported).
import React from 'react';
import { sendOrder } from '../api/apiService';
import type {
  FinalizeOrderResponse,
  ItemForHistory,
  SendOrderResponse,
  UserSelectedItem,
} from '../types/api_models';
import type { SendOrderDraft } from './FinalizeOrderForm';

interface OrderSummaryAndSendProps {
  finalizedOrder: FinalizeOrderResponse;
  userSelections: UserSelectedItem[];
  draft: SendOrderDraft;
  onOrderSent: (response: SendOrderResponse) => void;
  setIsLoading: (v: boolean) => void;
  setError: (msg: string | null) => void;
  onGoBack: () => void;
}

export const OrderSummaryAndSend: React.FC<OrderSummaryAndSendProps> = ({
  finalizedOrder,
  userSelections,
  draft,
  onOrderSent,
  setIsLoading,
  setError,
  onGoBack,
}) => {
  const handleSendOrder = async () => {
    setIsLoading(true);
    setError(null);
    // el backend espera 'Artículo' y 'Descripción' (con tildes) — contrato portado
    const itemsForHistoryPayload: ItemForHistory[] = userSelections.map((sel) => ({
      Ids: sel.selected_catalog_id,
      'Artículo': sel.original_article_text,
      'Descripción': sel.selected_catalog_description,
    }));
    try {
      const responseData = await sendOrder({
        final_order_items: finalizedOrder.final_order_items,
        items_for_history: itemsForHistoryPayload,
        ...draft,
      });
      // si hay PDF avanzamos al semáforo AUNQUE ERP/email hayan fallado (ported)
      if (responseData.pdf_download_data) {
        onOrderSent(responseData);
      } else {
        setError(
          responseData.message ||
            responseData.error_details ||
            'Error crítico: No se generó el PDF del pedido.',
        );
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ocurrió un error desconocido al enviar.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-xl p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-gray-800">Resumen y envío</h2>
        <button onClick={onGoBack} className="text-sm text-indigo-600 hover:underline">← Volver</button>
      </div>

      {finalizedOrder.warnings.length > 0 && (
        <div className="bg-yellow-50 border-l-4 border-yellow-400 p-3 rounded">
          {finalizedOrder.warnings.map((w, i) => (
            <p key={i} className="text-sm text-yellow-800">{w}</p>
          ))}
        </div>
      )}

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
        <div><span className="text-gray-400">Nº parte:</span> {draft.num_order || 'S/N'}</div>
        <div><span className="text-gray-400">Planta:</span> {draft.planta_name || 'S/P'}</div>
        <div>
          <span className="text-gray-400">Plazo:</span>{' '}
          {draft.plazo ? new Date(draft.plazo + 'T00:00:00').toLocaleDateString('es-ES') : '-'}
        </div>
        <div>
          <span className="text-gray-400">Flags:</span>{' '}
          {[draft.enviar_a_obra && 'Enviar a Obra', draft.solo_imputar && 'Sólo imputar']
            .filter(Boolean)
            .join(', ') || '—'}
        </div>
      </div>

      <div className="overflow-x-auto border border-gray-100 rounded-md">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-100">
            <tr>
              <th className="px-3 py-2 text-left text-xs font-semibold text-gray-600 uppercase">Uds</th>
              <th className="px-3 py-2 text-left text-xs font-semibold text-gray-600 uppercase">Código</th>
              <th className="px-3 py-2 text-left text-xs font-semibold text-gray-600 uppercase">Descripción</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {finalizedOrder.final_order_items.map((item, i) => (
              <tr key={i}>
                <td className="px-3 py-2 text-sm text-gray-700">{item.Uds}</td>
                <td className="px-3 py-2 text-sm font-mono text-gray-500">{item.Ids}</td>
                <td className="px-3 py-2 text-sm text-gray-700">{item['Descripción']}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex justify-end">
        <button
          onClick={handleSendOrder}
          className="px-6 py-2.5 bg-green-600 text-white text-sm font-bold rounded-md hover:bg-green-700"
        >
          Enviar pedido (3 canales)
        </button>
      </div>
    </div>
  );
};
