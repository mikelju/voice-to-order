// Step 4: order header form with debounced plant verification (ported).
import React, { useEffect, useState } from 'react';
import { finalizeOrder, getPlantaByOrderId } from '../api/apiService';
import type {
  FinalizeOrderResponse,
  SendOrderRequest,
  UserSelectedItem,
} from '../types/api_models';
import { useI18n } from '../i18n';

export interface SendOrderDraft {
  num_order: string | null;
  planta_name: string | null;
  plazo: string | null;
  observaciones: string | null;
  enviar_a_obra: boolean;
  solo_imputar: boolean;
}

interface FinalizeOrderFormProps {
  userSelections: UserSelectedItem[];
  initialNumOrder: string;
  initialPlantaName: string;
  observaciones: string;
  onObservacionesChange: (value: string) => void;
  onOrderFinalized: (data: FinalizeOrderResponse, draft: SendOrderDraft) => void;
  setIsLoading: (v: boolean) => void;
  setError: (msg: string | null) => void;
  onGoBack: () => void;
}

export const FinalizeOrderForm: React.FC<FinalizeOrderFormProps> = ({
  userSelections,
  initialNumOrder,
  initialPlantaName,
  observaciones,
  onObservacionesChange,
  onOrderFinalized,
  setIsLoading,
  setError,
  onGoBack,
}) => {
  const { t } = useI18n();
  const [numOrder, setNumOrder] = useState(initialNumOrder);
  const [plantaName, setPlantaName] = useState(initialPlantaName);
  const [plazo, setPlazo] = useState<string>(() => {
    const futureDate = new Date();
    futureDate.setDate(futureDate.getDate() + 3);   // ported default: today + 3 days
    return futureDate.toISOString().split('T')[0];
  });
  const [enviarAObra, setEnviarAObra] = useState(false);
  const [soloImputar, setSoloImputar] = useState(false);
  const [isPlantaLoading, setIsPlantaLoading] = useState(false);
  const [plantaError, setPlantaError] = useState<string | null>(null);

  // ported: debounced re-verification of the part number against the (simulated) ERP
  useEffect(() => {
    if (numOrder === initialNumOrder) {
      setPlantaError(null);
      setPlantaName(initialPlantaName);
      return;
    }
    const handler = setTimeout(async () => {
      if (!numOrder) {
        setPlantaError(null);
        setPlantaName('');
        return;
      }
      setIsPlantaLoading(true);
      setPlantaError(null);
      try {
        const response = await getPlantaByOrderId(numOrder);
        if (response.status === 'success') {
          setPlantaName(response.planta_name || '');
        } else if (response.status === 'not_found') {
          setPlantaName('');
          setPlantaError(t('finalize.err.partNotFound'));
        } else {
          setPlantaError(t('finalize.err.partVerify'));
        }
      } catch {
        setPlantaError(t('finalize.err.network'));
      } finally {
        setIsPlantaLoading(false);
      }
    }, 500);
    return () => clearTimeout(handler);
  }, [numOrder, initialNumOrder, initialPlantaName]);

  const handleSubmitFinalization = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const payload = {
        selected_items: userSelections,
        num_order: numOrder || null,
        planta_name: plantaName || null,
        plazo: plazo || null,
      };
      const data = await finalizeOrder(payload);
      onOrderFinalized(data, {
        num_order: numOrder || null,
        planta_name: plantaName || null,
        plazo: plazo || null,
        observaciones: observaciones || null,
        enviar_a_obra: enviarAObra,
        solo_imputar: soloImputar,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : t('finalize.err.finalize'));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-xl p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-gray-800">{t('finalize.title')}</h2>
        <button onClick={onGoBack} className="text-sm text-indigo-600 hover:underline">{t('common.back')}</button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div>
          <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">{t('field.partNumber')}</label>
          <input
            value={numOrder}
            onChange={(e) => setNumOrder(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-indigo-500 focus:border-indigo-500"
          />
          {isPlantaLoading && <p className="text-xs text-gray-400 mt-1">{t('finalize.verifying')}</p>}
          {plantaError && <p className="text-xs text-red-600 mt-1">{plantaError}</p>}
        </div>
        <div>
          <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">{t('field.plant')}</label>
          <input
            value={plantaName}
            onChange={(e) => setPlantaName(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-indigo-500 focus:border-indigo-500"
          />
        </div>
        <div>
          <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">{t('field.deadline')}</label>
          <input
            type="date"
            value={plazo}
            onChange={(e) => setPlazo(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-indigo-500 focus:border-indigo-500"
          />
        </div>
      </div>

      <div>
        <label className="block text-xs font-semibold text-gray-500 uppercase mb-1">{t('field.notes')}</label>
        <textarea
          value={observaciones}
          onChange={(e) => onObservacionesChange(e.target.value)}
          rows={2}
          className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-indigo-500 focus:border-indigo-500"
        />
      </div>

      <div className="flex gap-6">
        <label className="flex items-center gap-2 text-sm text-gray-700">
          <input type="checkbox" checked={enviarAObra} onChange={(e) => setEnviarAObra(e.target.checked)}
            className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500" />
          {t('finalize.toSite')}
        </label>
        <label className="flex items-center gap-2 text-sm text-gray-700">
          <input type="checkbox" checked={soloImputar} onChange={(e) => setSoloImputar(e.target.checked)}
            className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500" />
          {t('finalize.onlyImpute')}
        </label>
      </div>

      <div className="flex justify-end pt-2">
        <button
          onClick={handleSubmitFinalization}
          disabled={isPlantaLoading}
          className="px-5 py-2 bg-indigo-600 text-white text-sm font-medium rounded-md hover:bg-indigo-700 disabled:bg-gray-300"
        >
          {t('finalize.submit')}
        </button>
      </div>
    </div>
  );
};

export type { SendOrderRequest };
