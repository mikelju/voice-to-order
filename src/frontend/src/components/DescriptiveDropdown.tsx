// Searchable per-row dropdown (ported as-is from the original).
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { Option } from '../types';

interface DescriptiveDropdownProps {
  options: Option[];
  selectedOptionId?: string;
  onSelect: (optionId: string) => void;
}

export const DescriptiveDropdown: React.FC<DescriptiveDropdownProps> = ({
  options,
  selectedOptionId,
  onSelect,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const dropdownRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);

  const selectedOption = useMemo(
    () => options.find((opt) => opt.id === selectedOptionId),
    [options, selectedOptionId],
  );
  const displayText = selectedOption ? selectedOption.label : 'Seleccionar opción';

  const handleClickOutside = useCallback((event: MouseEvent) => {
    if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
      setIsOpen(false);
    }
  }, []);

  const toggleOpen = () => {
    const nextIsOpenState = !isOpen;
    if (nextIsOpenState) {
      setSearchTerm(selectedOption ? selectedOption.label : '');
    }
    setIsOpen(nextIsOpenState);
  };

  useEffect(() => {
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      if (searchInputRef.current) {
        searchInputRef.current.focus();
        if (searchTerm === (selectedOption ? selectedOption.label : '')) {
          const valueLength = searchInputRef.current.value.length;
          searchInputRef.current.setSelectionRange(valueLength, valueLength);
        }
      }
    } else {
      document.removeEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen, handleClickOutside, selectedOption, searchTerm]);

  const filteredOptions = useMemo(() => {
    const trimmedSearchTerm = searchTerm.trim();
    const currentSelectedLabel = selectedOption ? selectedOption.label.trim() : '';
    if (isOpen && trimmedSearchTerm === currentSelectedLabel) return options;
    const searchWords = trimmedSearchTerm
      .toLowerCase()
      .split(/\s+/)
      .filter((word) => word.length > 0);
    if (searchWords.length === 0) return options;
    return options.filter((option) => {
      const optionLabelLower = option.label.toLowerCase();
      return searchWords.every((word) => optionLabelLower.includes(word));
    });
  }, [options, searchTerm, selectedOption, isOpen]);

  const handleOptionClick = (optionId: string) => {
    const newSelectedOption = options.find((opt) => opt.id === optionId);
    onSelect(optionId);
    setIsOpen(false);
    setSearchTerm(newSelectedOption ? newSelectedOption.label : '');
  };

  return (
    <div ref={dropdownRef} className="relative w-full">
      <button
        type="button"
        onClick={toggleOpen}
        className="w-full flex items-center justify-between gap-1 px-2 py-1.5 text-left text-sm border border-gray-300 rounded-md bg-white hover:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-500"
      >
        <span className="truncate">{displayText}</span>
        <svg
          className={`w-4 h-4 flex-shrink-0 text-gray-500 transition-transform ${isOpen ? 'rotate-180' : ''}`}
          fill="none" stroke="currentColor" viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {isOpen && (
        <div className="absolute z-20 mt-1 w-full bg-white border border-gray-200 rounded-md shadow-lg">
          <input
            ref={searchInputRef}
            type="search"
            placeholder="Buscar..."
            autoComplete="off"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full px-2 py-1.5 text-sm border-b border-gray-200 focus:outline-none"
          />
          <ul
            role="listbox"
            className="max-h-52 sm:max-h-56 overflow-y-auto custom-scrollbar text-sm"
          >
            {filteredOptions.map((option) => (
              <li
                key={option.id}
                role="option"
                aria-selected={option.id === selectedOptionId}
                onClick={() => handleOptionClick(option.id)}
                className={`px-2 py-1.5 cursor-pointer hover:bg-indigo-500 hover:text-white ${
                  option.id === selectedOptionId
                    ? 'bg-indigo-50 font-medium text-indigo-600'
                    : 'text-gray-700'
                }`}
              >
                {option.label}
              </li>
            ))}
            {filteredOptions.length === 0 && (
              <li className="px-2 py-2 text-gray-400">No options match.</li>
            )}
          </ul>
        </div>
      )}
    </div>
  );
};
