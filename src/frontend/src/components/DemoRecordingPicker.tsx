// Replica addition: pick one of the 47 recorded (anonymized) orders in demo mode.
import React, { useEffect, useState } from 'react';
import { getDemoRecordings, processAudio } from '../api/apiService';
import type { DemoRecording, ProcessAudioResponse } from '../types/api_models';
import { useI18n } from '../i18n';

interface DemoRecordingPickerProps {
  onAudioProcessed: (data: ProcessAudioResponse) => void;
  setIsLoading: (v: boolean) => void;
  setError: (msg: string | null) => void;
  onGoBack: () => void;
}

export const DemoRecordingPicker: React.FC<DemoRecordingPickerProps> = ({
  onAudioProcessed,
  setIsLoading,
  setError,
  onGoBack,
}) => {
  const { t } = useI18n();
  const [recordings, setRecordings] = useState<DemoRecording[]>([]);
  const [loadingList, setLoadingList] = useState(true);

  useEffect(() => {
    let cancelled = false;
    getDemoRecordings()
      .then((recs) => {
        if (!cancelled) setRecordings(recs);
      })
      .catch((err) => setError(err instanceof Error ? err.message : t('demo.err.load')))
      .finally(() => {
        if (!cancelled) setLoadingList(false);
      });
    return () => {
      cancelled = true;
    };
  }, [setError]);

  const handlePick = async (rec: DemoRecording) => {
    setIsLoading(true);
    setError(null);
    try {
      // demo replay: the file content is irrelevant, the recording_id drives it
      const dummy = new File([new Blob(['demo'])], 'demo.wav', { type: 'audio/wav' });
      const data = await processAudio(dummy, rec.recording_id);
      onAudioProcessed(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('demo.err.process'));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-xl p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-gray-800">{t('demo.title')}</h2>
        <button onClick={onGoBack} className="text-sm text-indigo-600 hover:underline">{t('common.back')}</button>
      </div>
      <p className="text-sm text-gray-500 mb-4">{t('demo.subtitle')}</p>
      {loadingList ? (
        <p className="text-sm text-gray-500">{t('demo.loading')}</p>
      ) : (
        <ul className="divide-y divide-gray-100 border border-gray-100 rounded-md max-h-96 overflow-y-auto custom-scrollbar">
          {recordings.map((rec) => (
            <li
              key={rec.recording_id}
              onClick={() => handlePick(rec)}
              className="px-4 py-3 cursor-pointer hover:bg-indigo-50 transition-colors"
            >
              <div className="flex items-center justify-between gap-3">
                <span className="text-xs font-mono text-gray-400 flex-shrink-0">
                  #{rec.recording_id + 1}
                </span>
                <span className="text-sm text-gray-700 flex-1 line-clamp-2">{rec.transcription}</span>
                <span className="text-xs bg-indigo-100 text-indigo-700 rounded-full px-2 py-0.5 flex-shrink-0">
                  {t('demo.lines', { n: rec.n_items })}
                </span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};
