// Lightweight i18n (no dependency): a Context + useI18n() hook + a flat ES/EN dictionary.
// Only the UI chrome is translated; data from the backend (catalog descriptions, dictated
// transcriptions, article text) is rendered verbatim because it IS the Spanish dataset.
import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';

export type Lang = 'es' | 'en';
type Dict = Record<string, string>;

const STORAGE_KEY = 'vto_lang';

const ES: Dict = {
  // header / shell
  'header.subtitle': 'Pedidos dictados → catálogo de 31k artículos · réplica local del sistema en producción',
  'header.demoBadge': 'modo demo · sin claves API',
  'footer': 'Voice-to-Order — réplica pública y anonimizada de un sistema en producción · Biar Technology',
  'common.back': '← Volver',
  'common.loading': 'Procesando...',

  // shared field labels / values
  'field.partNumber': 'Nº de parte',
  'field.plant': 'Planta',
  'field.deadline': 'Plazo',
  'field.notes': 'Observaciones',
  'value.noPartNumber': 'S/N',
  'value.noPlant': 'S/P',
  'value.unknownPlant': 'Desconocido',

  // step: choose input
  'choose.title': 'Nuevo pedido',
  'choose.subtitle': 'Elige cómo dictar el pedido. Todo el flujo corre en local: transcripción y extracción por replay de pedidos reales, búsqueda vectorial real (pgvector).',
  'choose.recorded.title': 'Pedido grabado',
  'choose.recorded.sub': 'Elige uno de los 47 pedidos reales anonimizados',
  'choose.mic.title': 'Grabar micrófono',
  'choose.mic.sub': 'webm desde el navegador',
  'choose.upload.title': 'Subir fichero',
  'choose.upload.sub': 'mp3 / wav / m4a / ogg',

  // demo picker
  'demo.title': 'Pedidos grabados (demo)',
  'demo.subtitle': '47 pedidos reales dictados por técnicos de campo (transcripciones anonimizadas). Elige uno para reproducir el flujo completo.',
  'demo.loading': 'Cargando grabaciones...',
  'demo.lines': '{n} líneas',
  'demo.err.load': 'Error cargando grabaciones',
  'demo.err.process': 'Error procesando la grabación',

  // mic recorder
  'rec.title': 'Grabar pedido',
  'rec.record': '● Grabar',
  'rec.stop': '■ Detener',
  'rec.recording': 'Grabando...',
  'rec.acquiring': 'Accediendo al micrófono...',
  'rec.stopped': 'Grabación lista.',
  'rec.process': 'Procesar grabación',
  'rec.discard': 'Descartar',
  'rec.hint': 'En modo demo la grabación se reproduce contra un pedido grabado (selección determinista).',
  'rec.err.permission': 'Por favor, permite el acceso al micrófono.',
  'rec.err.notFound': 'No se encontró un micrófono.',
  'rec.err.generic': 'Error del grabador: {e}',
  'rec.err.process': 'Error procesando la grabación',

  // uploader
  'upload.title': 'Subir audio',
  'upload.hint': 'En modo demo el contenido se reproduce contra un pedido grabado (selección determinista).',
  'upload.process': 'Procesar audio',
  'upload.err.process': 'Error procesando el audio',

  // review extracted order
  'review.title': 'Revisar pedido extraído',
  'review.transcription': 'Transcripción',
  'review.plantVerified': 'Planta verificada con el ERP (simulado)',
  'review.col.quantity': 'Cantidad',
  'review.col.article': 'Artículo',
  'review.col.description': 'Descripción',
  'review.next': 'Buscar artículos en catálogo →',

  // article selector + table
  'select.title': 'Seleccionar artículos del catálogo',
  'select.loading': 'Buscando candidatos (memoria aprendida + catálogo, búsqueda vectorial)...',
  'select.addManual': '+ Añadir manualmente del catálogo',
  'select.confirm': 'Confirmar selección →',
  'select.err.search': 'Error buscando artículos',
  'select.err.duplicate': 'Ese artículo ya está en el pedido.',
  'select.err.noLines': 'No hay líneas válidas seleccionadas.',
  'table.col.delete': 'Borrar',
  'table.col.units': 'Uds.',
  'table.col.article': 'Artículo (Original)',
  'table.col.catalogDesc': 'Descripción Catálogo (Seleccionar)',
  'table.empty': 'No hay artículos para seleccionar.',
  'table.aria.delete': 'Eliminar fila {a}',

  // catalog search modal
  'catalog.title': 'Buscar en el catálogo',
  'catalog.placeholder': 'Escribe al menos 3 caracteres...',
  'catalog.searching': 'Buscando...',
  'catalog.noResults': 'Sin resultados.',
  'catalog.quantity': 'Cantidad:',
  'catalog.add': 'Añadir al pedido',

  // dropdown
  'dropdown.select': 'Seleccionar opción',
  'dropdown.search': 'Buscar...',
  'dropdown.noMatch': 'Ninguna opción coincide.',

  // finalize form
  'finalize.title': 'Datos del pedido',
  'finalize.verifying': 'Verificando...',
  'finalize.err.partNotFound': 'Nº de Parte no encontrado.',
  'finalize.err.partVerify': 'No se pudo verificar el Nº de Parte.',
  'finalize.err.network': 'Error de red al verificar.',
  'finalize.toSite': 'Enviar a Obra',
  'finalize.onlyImpute': 'Sólo imputar al parte (no pedir)',
  'finalize.submit': 'Finalizar pedido →',
  'finalize.err.finalize': 'Error finalizando el pedido',

  // summary + send
  'summary.title': 'Resumen y envío',
  'summary.partNumber': 'Nº parte:',
  'summary.plant': 'Planta:',
  'summary.deadline': 'Plazo:',
  'summary.flags': 'Flags:',
  'summary.flag.toSite': 'Enviar a Obra',
  'summary.flag.onlyImpute': 'Sólo imputar',
  'summary.col.units': 'Uds',
  'summary.col.code': 'Código',
  'summary.col.description': 'Descripción',
  'summary.send': 'Enviar pedido (3 canales)',
  'summary.err.noPdf': 'Error crítico: No se generó el PDF del pedido.',
  'summary.err.unknown': 'Ocurrió un error desconocido al enviar.',

  // confirmation + status lights
  'confirm.titleOk': 'Pedido procesado',
  'confirm.titleErr': 'Pedido con errores',
  'status.noDetails': 'Sin detalles',
  'status.erp.title': 'Integración ERP (simulada)',
  'status.email.title': 'Envío por Email (PDF)',
  'status.email.sent': 'PDF enviado por email (simulado).',
  'status.history.title': 'Actualización Histórico',
  'status.history.default': 'Datos guardados para aprendizaje.',
  'confirm.redownload': 'Volver a descargar PDF',
  'confirm.retryErp': 'Reintentar envío al ERP',
  'confirm.newOrder': 'Procesar nuevo pedido',
  'pdf.modal.title': 'Descarga el PDF del pedido',
  'pdf.modal.body': 'El PDF es el registro del pedido. Descárgalo para continuar.',
  'pdf.modal.download': 'Descargar PDF',
};

const EN: Dict = {
  // header / shell
  'header.subtitle': 'Dictated orders → 31k-article catalog · local replica of the production system',
  'header.demoBadge': 'demo mode · no API keys',
  'footer': 'Voice-to-Order — public, anonymized replica of a production system · Biar Technology',
  'common.back': '← Back',
  'common.loading': 'Processing...',

  // shared field labels / values
  'field.partNumber': 'Part no.',
  'field.plant': 'Plant',
  'field.deadline': 'Deadline',
  'field.notes': 'Notes',
  'value.noPartNumber': 'N/A',
  'value.noPlant': 'N/A',
  'value.unknownPlant': 'Unknown',

  // step: choose input
  'choose.title': 'New order',
  'choose.subtitle': 'Choose how to dictate the order. The whole flow runs locally: transcription and extraction by replaying real orders, real vector search (pgvector).',
  'choose.recorded.title': 'Recorded order',
  'choose.recorded.sub': 'Pick one of the 47 real anonymized orders',
  'choose.mic.title': 'Record microphone',
  'choose.mic.sub': 'webm from the browser',
  'choose.upload.title': 'Upload file',
  'choose.upload.sub': 'mp3 / wav / m4a / ogg',

  // demo picker
  'demo.title': 'Recorded orders (demo)',
  'demo.subtitle': '47 real orders dictated by field technicians (anonymized transcriptions). Pick one to replay the full flow.',
  'demo.loading': 'Loading recordings...',
  'demo.lines': '{n} lines',
  'demo.err.load': 'Error loading recordings',
  'demo.err.process': 'Error processing the recording',

  // mic recorder
  'rec.title': 'Record order',
  'rec.record': '● Record',
  'rec.stop': '■ Stop',
  'rec.recording': 'Recording...',
  'rec.acquiring': 'Accessing the microphone...',
  'rec.stopped': 'Recording ready.',
  'rec.process': 'Process recording',
  'rec.discard': 'Discard',
  'rec.hint': 'In demo mode the recording is replayed against a recorded order (deterministic selection).',
  'rec.err.permission': 'Please allow microphone access.',
  'rec.err.notFound': 'No microphone found.',
  'rec.err.generic': 'Recorder error: {e}',
  'rec.err.process': 'Error processing the recording',

  // uploader
  'upload.title': 'Upload audio',
  'upload.hint': 'In demo mode the content is replayed against a recorded order (deterministic selection).',
  'upload.process': 'Process audio',
  'upload.err.process': 'Error processing the audio',

  // review extracted order
  'review.title': 'Review extracted order',
  'review.transcription': 'Transcription',
  'review.plantVerified': 'Plant verified with the ERP (simulated)',
  'review.col.quantity': 'Quantity',
  'review.col.article': 'Article',
  'review.col.description': 'Description',
  'review.next': 'Search articles in the catalog →',

  // article selector + table
  'select.title': 'Select articles from the catalog',
  'select.loading': 'Searching candidates (learned memory + catalog, vector search)...',
  'select.addManual': '+ Add manually from the catalog',
  'select.confirm': 'Confirm selection →',
  'select.err.search': 'Error searching for articles',
  'select.err.duplicate': 'That article is already in the order.',
  'select.err.noLines': 'No valid lines selected.',
  'table.col.delete': 'Delete',
  'table.col.units': 'Qty',
  'table.col.article': 'Article (original)',
  'table.col.catalogDesc': 'Catalog description (select)',
  'table.empty': 'No articles to select.',
  'table.aria.delete': 'Delete row {a}',

  // catalog search modal
  'catalog.title': 'Search the catalog',
  'catalog.placeholder': 'Type at least 3 characters...',
  'catalog.searching': 'Searching...',
  'catalog.noResults': 'No results.',
  'catalog.quantity': 'Quantity:',
  'catalog.add': 'Add to order',

  // dropdown
  'dropdown.select': 'Select option',
  'dropdown.search': 'Search...',
  'dropdown.noMatch': 'No options match.',

  // finalize form
  'finalize.title': 'Order details',
  'finalize.verifying': 'Verifying...',
  'finalize.err.partNotFound': 'Part number not found.',
  'finalize.err.partVerify': 'Could not verify the part number.',
  'finalize.err.network': 'Network error during verification.',
  'finalize.toSite': 'Send to site',
  'finalize.onlyImpute': 'Only charge to the part (do not order)',
  'finalize.submit': 'Finalize order →',
  'finalize.err.finalize': 'Error finalizing the order',

  // summary + send
  'summary.title': 'Summary & send',
  'summary.partNumber': 'Part no.:',
  'summary.plant': 'Plant:',
  'summary.deadline': 'Deadline:',
  'summary.flags': 'Flags:',
  'summary.flag.toSite': 'Send to site',
  'summary.flag.onlyImpute': 'Charge only',
  'summary.col.units': 'Qty',
  'summary.col.code': 'Code',
  'summary.col.description': 'Description',
  'summary.send': 'Send order (3 channels)',
  'summary.err.noPdf': 'Critical error: the order PDF was not generated.',
  'summary.err.unknown': 'An unknown error occurred while sending.',

  // confirmation + status lights
  'confirm.titleOk': 'Order processed',
  'confirm.titleErr': 'Order with errors',
  'status.noDetails': 'No details',
  'status.erp.title': 'ERP integration (simulated)',
  'status.email.title': 'Email delivery (PDF)',
  'status.email.sent': 'PDF sent by email (simulated).',
  'status.history.title': 'Memory update',
  'status.history.default': 'Data saved for learning.',
  'confirm.redownload': 'Download PDF again',
  'confirm.retryErp': 'Retry ERP submission',
  'confirm.newOrder': 'Process new order',
  'pdf.modal.title': 'Download the order PDF',
  'pdf.modal.body': 'The PDF is the order record. Download it to continue.',
  'pdf.modal.download': 'Download PDF',
};

const DICTS: Record<Lang, Dict> = { es: ES, en: EN };

export type TFunc = (key: string, vars?: Record<string, string | number>) => string;

interface I18nValue {
  lang: Lang;
  setLang: (l: Lang) => void;
  t: TFunc;
}

const I18nContext = createContext<I18nValue | null>(null);

function detectInitial(): Lang {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved === 'es' || saved === 'en') return saved;
  } catch {
    /* localStorage unavailable */
  }
  try {
    return navigator.language?.toLowerCase().startsWith('es') ? 'es' : 'en';
  } catch {
    return 'es';
  }
}

export const LanguageProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [lang, setLangState] = useState<Lang>(detectInitial);

  const setLang = (l: Lang) => {
    setLangState(l);
    try {
      localStorage.setItem(STORAGE_KEY, l);
    } catch {
      /* ignore */
    }
  };

  useEffect(() => {
    try {
      document.documentElement.lang = lang;
    } catch {
      /* ignore */
    }
  }, [lang]);

  const value = useMemo<I18nValue>(
    () => ({
      lang,
      setLang,
      t: (key, vars) => {
        let s = DICTS[lang][key] ?? DICTS.es[key] ?? key;
        if (vars) {
          for (const k of Object.keys(vars)) {
            s = s.split(`{${k}}`).join(String(vars[k]));
          }
        }
        return s;
      },
    }),
    [lang],
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
};

export function useI18n(): I18nValue {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error('useI18n must be used within a LanguageProvider');
  return ctx;
}

// ES | EN segmented toggle for the header.
export const LanguageSwitcher: React.FC = () => {
  const { lang, setLang } = useI18n();
  const langs: Lang[] = ['es', 'en'];
  return (
    <div className="inline-flex rounded-full bg-white/15 p-0.5 text-xs" role="group" aria-label="Language">
      {langs.map((l) => (
        <button
          key={l}
          type="button"
          onClick={() => setLang(l)}
          aria-pressed={lang === l}
          className={`px-2.5 py-0.5 rounded-full uppercase tracking-wide transition-colors ${
            lang === l ? 'bg-white text-indigo-700 font-semibold' : 'text-white/80 hover:text-white'
          }`}
        >
          {l}
        </button>
      ))}
    </div>
  );
};
