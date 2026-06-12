// Step 2: review the transcription + extracted lines (read-only, ported).
import React from 'react';
import type { ProcessAudioResponse } from '../types/api_models';

interface InitialOrderDetailsProps {
  data: ProcessAudioResponse;
  onNextStep: () => void;
  onGoBack: () => void;
}

export const InitialOrderDetails: React.FC<InitialOrderDetailsProps> = ({
  data,
  onNextStep,
  onGoBack,
}) => {
  return (
    <div className="bg-white rounded-lg shadow-xl p-6 space-y-4">
      <h2 className="text-xl font-bold text-gray-800">Revisar pedido extraído</h2>

      {data.warnings.length > 0 && (
        <div className="bg-yellow-50 border-l-4 border-yellow-400 p-3 rounded">
          {data.warnings.map((w, i) => (
            <p key={i} className="text-sm text-yellow-800">{w}</p>
          ))}
        </div>
      )}

      <div>
        <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Transcripción</label>
        <textarea
          readOnly
          value={data.transcription}
          rows={3}
          className="w-full px-3 py-2 border border-gray-200 rounded-md text-sm bg-gray-50 text-gray-700"
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Nº de parte</label>
          <input
            readOnly
            value={data.num_order || 'S/N'}
            className="w-full px-3 py-2 border border-gray-200 rounded-md text-sm bg-gray-50 text-gray-700"
          />
        </div>
        <div>
          <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">
            Planta{' '}
            {data.planta_name_source === 'erp' && (
              <span title="Planta verificada con el ERP (simulado)">✅</span>
            )}
          </label>
          <input
            readOnly
            value={data.planta_name || 'Desconocido'}
            className="w-full px-3 py-2 border border-gray-200 rounded-md text-sm bg-gray-50 text-gray-700"
          />
        </div>
      </div>

      {data.observaciones && (
        <div>
          <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">Observaciones</label>
          <p className="text-sm text-gray-700 bg-gray-50 border border-gray-200 rounded-md px-3 py-2">
            {data.observaciones}
          </p>
        </div>
      )}

      <div className="overflow-x-auto border border-gray-100 rounded-md">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-100">
            <tr>
              <th className="px-3 py-2 text-left text-xs font-semibold text-gray-600 uppercase">Cantidad</th>
              <th className="px-3 py-2 text-left text-xs font-semibold text-gray-600 uppercase">Artículo</th>
              <th className="px-3 py-2 text-left text-xs font-semibold text-gray-600 uppercase">Descripción</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {data.df_order_json.map((item, i) => (
              <tr key={i}>
                <td className="px-3 py-2 text-sm text-gray-700">{item.CANTIDAD}</td>
                <td className="px-3 py-2 text-sm text-gray-700">{item['ARTÍCULO']}</td>
                <td className="px-3 py-2 text-sm text-gray-700">{item['DESCRIPCIÓN']}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex justify-between pt-2">
        <button onClick={onGoBack} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800">
          ← Volver
        </button>
        <button
          onClick={onNextStep}
          className="px-5 py-2 bg-indigo-600 text-white text-sm font-medium rounded-md hover:bg-indigo-700"
        >
          Buscar artículos en catálogo →
        </button>
      </div>
    </div>
  );
};
