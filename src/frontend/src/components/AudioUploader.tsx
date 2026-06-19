// Upload-an-audio-file input path (ported).
import React, { useState } from 'react';
import { processAudio } from '../api/apiService';
import type { ProcessAudioResponse } from '../types/api_models';
import { useI18n } from '../i18n';

interface AudioUploaderProps {
  onAudioProcessed: (data: ProcessAudioResponse) => void;
  setIsLoading: (v: boolean) => void;
  setError: (msg: string | null) => void;
  onGoBack: () => void;
}

export const AudioUploader: React.FC<AudioUploaderProps> = ({
  onAudioProcessed,
  setIsLoading,
  setError,
  onGoBack,
}) => {
  const { t } = useI18n();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const handleSubmit = async () => {
    if (!selectedFile) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await processAudio(selectedFile);
      onAudioProcessed(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('upload.err.process'));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-xl p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-gray-800">{t('upload.title')}</h2>
        <button onClick={onGoBack} className="text-sm text-indigo-600 hover:underline">{t('common.back')}</button>
      </div>
      <input
        type="file"
        accept="audio/*,.mp3,.wav,.m4a,.ogg,.mp4"
        onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
        className="block w-full text-sm text-gray-600 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100"
      />
      {selectedFile && (
        <p className="mt-2 text-sm text-gray-500">
          {selectedFile.name} ({(selectedFile.size / 1024).toFixed(1)} KB)
        </p>
      )}
      <p className="mt-2 text-xs text-gray-400">{t('upload.hint')}</p>
      <button
        onClick={handleSubmit}
        disabled={!selectedFile}
        className="mt-4 px-5 py-2 bg-indigo-600 text-white text-sm font-medium rounded-md hover:bg-indigo-700 disabled:bg-gray-300"
      >
        {t('upload.process')}
      </button>
    </div>
  );
};
