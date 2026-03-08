import React, { useState } from 'react';
import { Edit2, Check, X } from 'lucide-react';
import type { IDCardOCRResult } from '../../../api/idCardApi';

interface IDCardResultViewProps {
  result: IDCardOCRResult;
  onFieldChange?: (field: 'name' | 'resident_number' | 'address', value: string) => void;
}

const IDCardResultView: React.FC<IDCardResultViewProps> = ({ result, onFieldChange }) => {
  const [editingField, setEditingField] = useState<'name' | 'resident_number' | 'address' | null>(null);
  const [editedValues, setEditedValues] = useState({
    name: result.data.name,
    resident_number: result.data.resident_number,
    address: result.data.address,
  });

  const handleEdit = (field: 'name' | 'resident_number' | 'address') => {
    setEditingField(field);
  };

  const handleSave = (field: 'name' | 'resident_number' | 'address') => {
    if (onFieldChange) {
      onFieldChange(field, editedValues[field]);
    }
    setEditingField(null);
  };

  const handleCancel = () => {
    setEditedValues({
      name: result.data.name,
      resident_number: result.data.resident_number,
      address: result.data.address,
    });
    setEditingField(null);
  };

  const FieldRow = ({ 
    label, 
    field, 
    value, 
    cropImage 
  }: { 
    label: string; 
    field: 'name' | 'resident_number' | 'address';
    value: string;
    cropImage?: string;
  }) => {
    const isEditing = editingField === field;

    return (
      <div className="border-b border-gray-200 py-4">
        <div className="flex items-start gap-4">
          <div className="w-32 flex-shrink-0">
            <label className="text-sm font-medium text-gray-700">{label}</label>
          </div>
          
          <div className="flex-1">
            {isEditing ? (
              <div className="space-y-2">
                <input
                  type="text"
                  value={editedValues[field]}
                  onChange={(e) => setEditedValues({ ...editedValues, [field]: e.target.value })}
                  className="w-full px-3 py-2 border border-blue-500 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  autoFocus
                />
                <div className="flex gap-2">
                  <button
                    onClick={() => handleSave(field)}
                    className="px-3 py-1.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 flex items-center gap-1"
                  >
                    <Check size={14} />
                    저장
                  </button>
                  <button
                    onClick={handleCancel}
                    className="px-3 py-1.5 bg-gray-200 text-gray-700 text-sm rounded-lg hover:bg-gray-300 flex items-center gap-1"
                  >
                    <X size={14} />
                    취소
                  </button>
                </div>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <span className="text-gray-900 flex-1">{value || '(없음)'}</span>
                <button
                  onClick={() => handleEdit(field)}
                  className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
                  title="수정"
                >
                  <Edit2 size={16} />
                </button>
              </div>
            )}
          </div>

          {cropImage && (
            <div className="w-40 flex-shrink-0">
              <img
                src={`data:image/jpeg;base64,${cropImage}`}
                alt={label}
                className="w-full h-20 object-contain border-2 border-blue-200 rounded-lg bg-gray-50 p-1"
              />
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">📋 추출된 정보 (수정 가능)</h3>
      
      <div className="space-y-0">
        <FieldRow
          label="성명"
          field="name"
          value={editedValues.name}
          cropImage={result.crops.name}
        />
        <FieldRow
          label="주민번호"
          field="resident_number"
          value={editedValues.resident_number}
          cropImage={result.crops.resident}
        />
        <FieldRow
          label="주소"
          field="address"
          value={editedValues.address}
          cropImage={result.crops.address}
        />
      </div>

      {/* 마스킹된 이미지 */}
      {result.masked_image && (
        <div className="mt-6 pt-6 border-t border-gray-200">
          <h4 className="text-sm font-medium text-gray-700 mb-3">🔒 마스킹 처리된 이미지</h4>
          <img
            src={`data:image/jpeg;base64,${result.masked_image}`}
            alt="마스킹된 신분증"
            className="w-full max-w-md border-2 border-gray-300 rounded-lg"
          />
        </div>
      )}

      {/* OCR 텍스트 전체 */}
      <div className="mt-6 pt-6 border-t border-gray-200">
        <h4 className="text-sm font-medium text-gray-700 mb-3">OCR 추출 텍스트 전체</h4>
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
          <pre className="text-sm text-gray-700 whitespace-pre-wrap font-mono">
            {result.ocr_text}
          </pre>
        </div>
      </div>
    </div>
  );
};

export default IDCardResultView;

