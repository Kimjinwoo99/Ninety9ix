import React from 'react';
import { Shield, Bell, User, Database } from 'lucide-react';

const Settings: React.FC = () => {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">설정</h1>
        <p className="text-sm text-gray-500 mt-1">
          시스템 설정 및 사용자 관리
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-3 bg-blue-100 rounded-lg">
              <Shield className="text-blue-600" size={24} />
            </div>
            <h3 className="text-lg font-semibold text-gray-900">Agent 규칙</h3>
          </div>
          <p className="text-sm text-gray-600 mb-4">
            자동 판단 임계값 및 검증 규칙을 설정합니다.
          </p>
          <button className="w-full py-2 border border-gray-300 text-gray-700 font-medium rounded-lg hover:bg-gray-50">
            설정하기
          </button>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-3 bg-green-100 rounded-lg">
              <Database className="text-green-600" size={24} />
            </div>
            <h3 className="text-lg font-semibold text-gray-900">필수 필드 관리</h3>
          </div>
          <p className="text-sm text-gray-600 mb-4">
            문서 유형별 필수 입력 필드를 관리합니다.
          </p>
          <button className="w-full py-2 border border-gray-300 text-gray-700 font-medium rounded-lg hover:bg-gray-50">
            설정하기
          </button>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-3 bg-purple-100 rounded-lg">
              <User className="text-purple-600" size={24} />
            </div>
            <h3 className="text-lg font-semibold text-gray-900">사용자 관리</h3>
          </div>
          <p className="text-sm text-gray-600 mb-4">
            시스템 사용자 및 권한을 관리합니다.
          </p>
          <button className="w-full py-2 border border-gray-300 text-gray-700 font-medium rounded-lg hover:bg-gray-50">
            설정하기
          </button>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-3 bg-yellow-100 rounded-lg">
              <Bell className="text-yellow-600" size={24} />
            </div>
            <h3 className="text-lg font-semibold text-gray-900">알림 설정</h3>
          </div>
          <p className="text-sm text-gray-600 mb-4">
            시스템 알림 및 이메일 설정을 관리합니다.
          </p>
          <button className="w-full py-2 border border-gray-300 text-gray-700 font-medium rounded-lg hover:bg-gray-50">
            설정하기
          </button>
        </div>
      </div>
    </div>
  );
};

export default Settings;

