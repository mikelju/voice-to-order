// Root component: manual wizard state machine + shared business state (ported design).
// Replica: no auth layer; new DEMO_PICKER input path; demo banner.
import React, { useCallback, useState } from 'react';
import {
  FinalizeOrderResponse,
  ProcessAudioResponse,
  SendOrderResponse,
  UserSelectedItem,
} from './types/api_models';
import { ArticleSelector } from './components/ArticleSelector';
import { AudioRecorderHandler } from './components/AudioRecorderHandler';
import { AudioUploader } from './components/AudioUploader';
import { DemoRecordingPicker } from './components/DemoRecordingPicker';
import { FinalizeOrderForm, SendOrderDraft } from './components/FinalizeOrderForm';
import { InitialOrderDetails } from './components/InitialOrderDetails';
import { OrderSummaryAndSend } from './components/OrderSummaryAndSend';

type AppStep =
  | 'CHOOSE_INPUT'
  | 'DEMO_PICKER'
  | 'RECORD_AUDIO'
  | 'UPLOAD_AUDIO'
  | 'VIEW_INITIAL_ORDER'
  | 'SELECT_ARTICLES'
  | 'FINALIZE_ORDER'
  | 'SEND_ORDER'
  | 'ORDER_CONFIRMATION';

// Per-channel status light (ported).
const StatusCard: React.FC<{
  title: string;
  status: string | undefined | null;
  message?: string | null;
  isCritical?: boolean;
}> = ({ title, status, message, isCritical = false }) => {
  let bgColor = 'bg-gray-50';
  let borderColor = 'border-gray-300';
  let textColor = 'text-gray-700';
  let icon = '·';
  const normalizedStatus = status?.toLowerCase() || 'desconocido';
  if (normalizedStatus === 'exito' || normalizedStatus === 'enviado' || normalizedStatus === 'success') {
    bgColor = 'bg-green-50'; borderColor = 'border-green-500'; textColor = 'text-green-800'; icon = '✓';
  } else if (normalizedStatus === 'omitido' || normalizedStatus === 'skipped') {
    bgColor = 'bg-gray-100'; borderColor = 'border-gray-400'; textColor = 'text-gray-600'; icon = '—';
  } else if (normalizedStatus === 'fallido' || normalizedStatus === 'error' || normalizedStatus === 'partial_error') {
    if (isCritical) {
      bgColor = 'bg-red-50'; borderColor = 'border-red-500'; textColor = 'text-red-800'; icon = '✕';
    } else {
      bgColor = 'bg-yellow-50'; borderColor = 'border-yellow-500'; textColor = 'text-yellow-800'; icon = '⚠';
    }
  }
  return (
    <div className={`p-4 rounded-lg border-l-4 ${borderColor} ${bgColor} shadow-sm transition-all`}>
      <div className="flex items-start">
        <div className={`flex-shrink-0 mt-0.5 font-bold ${textColor}`}>{icon}</div>
        <div className="ml-3 w-full">
          <h3 className={`text-sm font-bold ${textColor} uppercase tracking-wide`}>{title}</h3>
          <p className={`mt-1 text-sm ${textColor} opacity-90`}>{message || 'Sin detalles'}</p>
        </div>
      </div>
    </div>
  );
};

// ported heuristic: the email channel has no dedicated field; it is inferred from
// error_details containing the literal "Email:" prefix.
const getEmailStatus = (result: SendOrderResponse | null) => {
  if (!result) return 'desconocido';
  if (result.error_details && result.error_details.includes('Email:')) return 'fallido';
  return 'exito';
};

const getEmailMessage = (result: SendOrderResponse | null) => {
  if (!result?.error_details) return 'PDF enviado por email (simulado).';
  const emailPart = result.error_details
    .split(' | ')
    .find((part) => part.startsWith('Email:'));
  return emailPart || 'PDF enviado por email (simulado).';
};

const App: React.FC = () => {
  const [currentStep, setCurrentStep] = useState<AppStep>('CHOOSE_INPUT');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [step1Data, setStep1Data] = useState<ProcessAudioResponse | null>(null);
  const [userSelections, setUserSelections] = useState<UserSelectedItem[]>([]);
  const [step3Data, setStep3Data] = useState<FinalizeOrderResponse | null>(null);
  const [sendDraft, setSendDraft] = useState<SendOrderDraft | null>(null);
  const [sendOrderResult, setSendOrderResult] = useState<SendOrderResponse | null>(null);
  const [observaciones, setObservaciones] = useState('');
  const [pdfDownloaded, setPdfDownloaded] = useState(false);

  const resetApp = useCallback(() => {
    setCurrentStep('CHOOSE_INPUT');
    setIsLoading(false);
    setError(null);
    setStep1Data(null);
    setUserSelections([]);
    setStep3Data(null);
    setSendDraft(null);
    setSendOrderResult(null);
    setObservaciones('');
    setPdfDownloaded(false);
  }, []);

  const handleAudioProcessed = (data: ProcessAudioResponse) => {
    setStep1Data(data);
    setObservaciones(data.observaciones || '');
    setCurrentStep('VIEW_INITIAL_ORDER');
  };

  return (
    <div className="min-h-screen bg-gray-100">
      <header className="bg-gradient-to-r from-indigo-700 to-purple-700 text-white shadow-md">
        <div className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold">Voice-to-Order</h1>
            <p className="text-xs text-indigo-200">
              Pedidos dictados → catálogo de 31k artículos · réplica local del sistema en producción
            </p>
          </div>
          <span className="text-xs bg-white/15 rounded-full px-3 py-1">modo demo · sin claves API</span>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-6">
        {error && (
          <div className="mb-4 bg-red-50 border-l-4 border-red-500 px-4 py-3 rounded flex items-start justify-between">
            <p className="text-sm text-red-700">{error}</p>
            <button onClick={() => setError(null)} className="text-red-400 hover:text-red-600 ml-3">×</button>
          </div>
        )}

        {currentStep === 'CHOOSE_INPUT' && (
          <div className="bg-white rounded-lg shadow-xl p-8">
            <h2 className="text-xl font-bold text-gray-800 mb-1">Nuevo pedido</h2>
            <p className="text-sm text-gray-500 mb-6">
              Elige cómo dictar el pedido. Todo el flujo corre en local: transcripción y
              extracción por replay de pedidos reales, búsqueda vectorial real (pgvector).
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <button
                onClick={() => setCurrentStep('DEMO_PICKER')}
                className="p-5 rounded-lg border-2 border-indigo-200 bg-indigo-50 hover:border-indigo-400 text-left"
              >
                <span className="block text-2xl mb-2">▶</span>
                <span className="block font-semibold text-indigo-800">Pedido grabado</span>
                <span className="block text-xs text-gray-500 mt-1">
                  Elige uno de los 47 pedidos reales anonimizados
                </span>
              </button>
              <button
                onClick={() => setCurrentStep('RECORD_AUDIO')}
                className="p-5 rounded-lg border-2 border-gray-200 hover:border-indigo-400 text-left"
              >
                <span className="block text-2xl mb-2">🎙</span>
                <span className="block font-semibold text-gray-800">Grabar micrófono</span>
                <span className="block text-xs text-gray-500 mt-1">webm desde el navegador</span>
              </button>
              <button
                onClick={() => setCurrentStep('UPLOAD_AUDIO')}
                className="p-5 rounded-lg border-2 border-gray-200 hover:border-indigo-400 text-left"
              >
                <span className="block text-2xl mb-2">📁</span>
                <span className="block font-semibold text-gray-800">Subir fichero</span>
                <span className="block text-xs text-gray-500 mt-1">mp3 / wav / m4a / ogg</span>
              </button>
            </div>
          </div>
        )}

        {currentStep === 'DEMO_PICKER' && (
          <DemoRecordingPicker
            onAudioProcessed={handleAudioProcessed}
            setIsLoading={setIsLoading}
            setError={setError}
            onGoBack={() => setCurrentStep('CHOOSE_INPUT')}
          />
        )}
        {currentStep === 'RECORD_AUDIO' && (
          <AudioRecorderHandler
            onAudioProcessed={handleAudioProcessed}
            setIsLoading={setIsLoading}
            setError={setError}
            onGoBack={() => setCurrentStep('CHOOSE_INPUT')}
          />
        )}
        {currentStep === 'UPLOAD_AUDIO' && (
          <AudioUploader
            onAudioProcessed={handleAudioProcessed}
            setIsLoading={setIsLoading}
            setError={setError}
            onGoBack={() => setCurrentStep('CHOOSE_INPUT')}
          />
        )}
        {currentStep === 'VIEW_INITIAL_ORDER' && step1Data && (
          <InitialOrderDetails
            data={step1Data}
            onNextStep={() => setCurrentStep('SELECT_ARTICLES')}
            onGoBack={() => setCurrentStep('CHOOSE_INPUT')}
          />
        )}
        {currentStep === 'SELECT_ARTICLES' && step1Data && (
          <ArticleSelector
            initialOrderData={step1Data}
            onSelectionsConfirmed={(selections) => {
              setUserSelections(selections);
              setCurrentStep('FINALIZE_ORDER');
            }}
            onGoBack={() => setCurrentStep('VIEW_INITIAL_ORDER')}
          />
        )}
        {currentStep === 'FINALIZE_ORDER' && step1Data && (
          <FinalizeOrderForm
            userSelections={userSelections}
            initialNumOrder={step1Data.num_order || ''}
            initialPlantaName={step1Data.planta_name || ''}
            observaciones={observaciones}
            onObservacionesChange={setObservaciones}
            onOrderFinalized={(data, draft) => {
              setStep3Data(data);
              setSendDraft(draft);
              setCurrentStep('SEND_ORDER');
            }}
            setIsLoading={setIsLoading}
            setError={setError}
            onGoBack={() => setCurrentStep('SELECT_ARTICLES')}
          />
        )}
        {currentStep === 'SEND_ORDER' && step3Data && sendDraft && (
          <OrderSummaryAndSend
            finalizedOrder={step3Data}
            userSelections={userSelections}
            draft={sendDraft}
            onOrderSent={(response) => {
              setSendOrderResult(response);
              setPdfDownloaded(false);
              setCurrentStep('ORDER_CONFIRMATION');
            }}
            setIsLoading={setIsLoading}
            setError={setError}
            onGoBack={() => setCurrentStep('FINALIZE_ORDER')}
          />
        )}
        {currentStep === 'ORDER_CONFIRMATION' && sendOrderResult && (
          <div className="space-y-4">
            <h2 className="text-xl font-bold text-gray-800">
              {sendOrderResult.order_sent_status === 'enviado'
                ? 'Pedido procesado'
                : 'Pedido con errores'}
            </h2>
            <p className="text-sm text-gray-600">{sendOrderResult.message}</p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <StatusCard
                title="Integración ERP (simulada)"
                status={sendOrderResult.erp_update_status}
                message={sendOrderResult.erp_update_message}
                isCritical={true}
              />
              <StatusCard
                title="Envío por Email (PDF)"
                status={getEmailStatus(sendOrderResult)}
                message={getEmailMessage(sendOrderResult)}
                isCritical={false}
              />
              <StatusCard
                title="Actualización Histórico"
                status={sendOrderResult.historical_update_status}
                message={sendOrderResult.historical_update_message || 'Datos guardados para aprendizaje.'}
                isCritical={false}
              />
            </div>

            <div className="flex gap-3 pt-2">
              {sendOrderResult.pdf_download_data && pdfDownloaded && (
                <a
                  // SEC-006: hardcode the MIME (never trust a server-sent content_type
                  // in a data: URL) + download attribute so the blob is never rendered inline
                  href={`data:application/pdf;base64,${sendOrderResult.pdf_download_data.b64_pdf}`}
                  download={sendOrderResult.pdf_download_data.filename}
                  className="px-4 py-2 bg-gray-100 text-gray-700 text-sm rounded-md hover:bg-gray-200"
                >
                  Volver a descargar PDF
                </a>
              )}
              {sendOrderResult.erp_update_status === 'fallido' && (
                <button
                  onClick={() => setCurrentStep('SEND_ORDER')}
                  className="px-4 py-2 bg-red-50 text-red-700 text-sm rounded-md hover:bg-red-100"
                >
                  Reintentar envío al ERP
                </button>
              )}
              <button
                onClick={resetApp}
                className="ml-auto px-5 py-2 bg-indigo-600 text-white text-sm font-medium rounded-md hover:bg-indigo-700"
              >
                Procesar nuevo pedido
              </button>
            </div>

            {/* forced PDF download modal (ported): no close button by design */}
            {!pdfDownloaded && sendOrderResult.pdf_download_data && (
              <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/90 p-4 backdrop-blur-sm">
                <div className="bg-white rounded-lg shadow-2xl p-8 max-w-md text-center">
                  <h3 className="text-lg font-bold text-gray-800 mb-2">Descarga el PDF del pedido</h3>
                  <p className="text-sm text-gray-500 mb-6">
                    El PDF es el registro del pedido. Descárgalo para continuar.
                  </p>
                  <a
                    href={`data:application/pdf;base64,${sendOrderResult.pdf_download_data.b64_pdf}`}
                    download={sendOrderResult.pdf_download_data.filename}
                    onClick={() => setPdfDownloaded(true)}
                    className="inline-block px-6 py-2.5 bg-indigo-600 text-white text-sm font-bold rounded-md hover:bg-indigo-700"
                  >
                    Descargar PDF
                  </a>
                </div>
              </div>
            )}
          </div>
        )}

        {isLoading && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/60 backdrop-blur-sm">
            <div className="bg-white rounded-lg shadow-2xl px-8 py-6 text-center">
              <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
              <p className="text-sm font-medium text-gray-700">Procesando...</p>
            </div>
          </div>
        )}
      </main>

      <footer className="max-w-5xl mx-auto px-4 py-6 text-center text-xs text-gray-400">
        Voice-to-Order — réplica pública y anonimizada de un sistema en producción ·
        Biar Technology
      </footer>
    </div>
  );
};

export default App;
