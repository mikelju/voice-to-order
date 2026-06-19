// Microphone recording input path via react-media-recorder (ported).
import React, { useState } from 'react';
import { useReactMediaRecorder } from 'react-media-recorder';
import { processAudio } from '../api/apiService';
import type { ProcessAudioResponse } from '../types/api_models';
import { useI18n } from '../i18n';

interface AudioRecorderHandlerProps {
  onAudioProcessed: (data: ProcessAudioResponse) => void;
  setIsLoading: (v: boolean) => void;
  setError: (msg: string | null) => void;
  onGoBack: () => void;
}

export const AudioRecorderHandler: React.FC<AudioRecorderHandlerProps> = ({
  onAudioProcessed,
  setIsLoading,
  setError,
  onGoBack,
}) => {
  const { t } = useI18n();
  const [recordedAudioBlob, setRecordedAudioBlob] = useState<Blob | null>(null);
  const [audioUrlForPlayback, setAudioUrlForPlayback] = useState<string | null>(null);

  const { status, startRecording, stopRecording, error: recorderError } =
    useReactMediaRecorder({
      audio: true,
      onStop: (blobUrl: string, blob: Blob) => {
        setRecordedAudioBlob(blob);
        setAudioUrlForPlayback(blobUrl);
      },
    });

  const recorderErrorMessage = (() => {
    if (!recorderError) return null;
    if (recorderError.includes('Permission') || recorderError.includes('NotAllowed')) {
      return t('rec.err.permission');
    }
    if (recorderError.includes('NotFound')) return t('rec.err.notFound');
    return t('rec.err.generic', { e: recorderError });
  })();

  const handleProcessRecordedAudio = async () => {
    if (!recordedAudioBlob) return;
    setIsLoading(true);
    setError(null);
    try {
      const fileName = `grabacion_${new Date().toISOString().replace(/[:.]/g, '-')}.webm`;
      const file = new File([recordedAudioBlob], fileName, { type: 'audio/webm' });
      const data = await processAudio(file);
      onAudioProcessed(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('rec.err.process'));
    } finally {
      setIsLoading(false);
    }
  };

  const handleDiscard = () => {
    setRecordedAudioBlob(null);
    setAudioUrlForPlayback(null);
  };

  return (
    <div className="bg-white rounded-lg shadow-xl p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-gray-800">{t('rec.title')}</h2>
        <button onClick={onGoBack} className="text-sm text-indigo-600 hover:underline">{t('common.back')}</button>
      </div>
      {recorderErrorMessage && (
        <p className="mb-3 text-sm text-red-600">{recorderErrorMessage}</p>
      )}
      <div className="flex items-center gap-3">
        {status !== 'recording' ? (
          <button
            onClick={startRecording}
            className="px-5 py-2 bg-red-600 text-white text-sm font-medium rounded-md hover:bg-red-700"
          >
            {t('rec.record')}
          </button>
        ) : (
          <button
            onClick={stopRecording}
            className="px-5 py-2 bg-gray-800 text-white text-sm font-medium rounded-md hover:bg-gray-900 animate-pulse"
          >
            {t('rec.stop')}
          </button>
        )}
        <span className="text-sm text-gray-500">
          {status === 'recording' && t('rec.recording')}
          {status === 'acquiring_media' && t('rec.acquiring')}
          {status === 'stopped' && t('rec.stopped')}
        </span>
      </div>
      {audioUrlForPlayback && (
        <div className="mt-4 space-y-3">
          <audio controls src={audioUrlForPlayback} className="w-full" />
          <div className="flex gap-3">
            <button
              onClick={handleProcessRecordedAudio}
              className="px-5 py-2 bg-indigo-600 text-white text-sm font-medium rounded-md hover:bg-indigo-700"
            >
              {t('rec.process')}
            </button>
            <button
              onClick={handleDiscard}
              className="px-5 py-2 bg-gray-100 text-gray-700 text-sm font-medium rounded-md hover:bg-gray-200"
            >
              {t('rec.discard')}
            </button>
          </div>
        </div>
      )}
      <p className="mt-3 text-xs text-gray-400">{t('rec.hint')}</p>
    </div>
  );
};
