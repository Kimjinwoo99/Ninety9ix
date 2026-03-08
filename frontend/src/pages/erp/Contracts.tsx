import React, { useState, useEffect } from 'react';
import { Search, Filter, Download, Wifi, Tv, Phone, Smartphone, FileText } from 'lucide-react';

type TabType = 'internet' | 'tv' | 'phone' | 'device';

const Contracts: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('internet');
  const [searchQuery, setSearchQuery] = useState('');
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const loadData = () => {
      setLoading(true);
      try {
        const storedContracts = JSON.parse(localStorage.getItem('contracts') || '[]');
        // activeTab에 따라 필터링 (현재는 모든 계약 표시)
        setData(storedContracts);
      } catch (error) {
        console.error('Error loading data:', error);
        setData([]);
      } finally {
        setLoading(false);
      }
    };

    loadData();
    
    // 주기적으로 업데이트 (다른 탭에서 승인 완료 시 반영)
    const interval = setInterval(loadData, 1000);
    return () => clearInterval(interval);
  }, [activeTab]);

  // Dynamic Columns based on Tab
  const renderTableHeader = () => {
    const commonHeaders = (
      <>
        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">고객명</th>
        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">신청일</th>
      </>
    );
    const actionHeader = <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">관련 서류</th>;

    switch (activeTab) {
      case 'internet':
        return (
          <tr>
            {commonHeaders}
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">요금제</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">속도</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">약정</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">상태</th>
            {actionHeader}
          </tr>
        );
      case 'tv':
        return (
          <tr>
            {commonHeaders}
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">상품유형</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">셋탑박스</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">약정</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">상태</th>
            {actionHeader}
          </tr>
        );
      case 'phone':
        return (
          <tr>
            {commonHeaders}
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">전화구분</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">요금제</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">희망번호</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">상태</th>
            {actionHeader}
          </tr>
        );
      case 'device':
        return (
          <tr>
            {commonHeaders}
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">기기명</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">가격</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">구매방식</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">상태</th>
            {actionHeader}
          </tr>
        );
      default: return null;
    }
  };

  const renderTableBody = () => {
    if (loading) return <tr><td colSpan={7} className="px-6 py-12 text-center">로딩 중...</td></tr>;
    if (data.length === 0) return <tr><td colSpan={7} className="px-6 py-12 text-center text-gray-500">데이터가 없습니다.</td></tr>;

    return data.map((item, index) => {
      const rowClass = "hover:bg-gray-50";
      const cellClass = "px-6 py-4 whitespace-nowrap text-sm text-gray-900";
      
      const documentButton = (
        <td className={cellClass}>
          <button className="flex items-center gap-1 text-blue-600 hover:text-blue-800 bg-blue-50 hover:bg-blue-100 px-3 py-1 rounded-md transition-colors">
            <FileText size={16} />
            <span className="text-xs font-medium">서류 보기</span>
          </button>
        </td>
      );

      const commonCells = (
        <>
          <td className={`${cellClass} font-medium`}>{item.customer_name}</td>
          <td className={cellClass}>{item.application_date}</td>
        </>
      );

      const statusCell = (
        <td className={cellClass}>
          <span className="px-2 py-1 bg-green-100 text-green-700 text-xs rounded-full">{item.status}</span>
        </td>
      );

      if (activeTab === 'internet') {
        return (
          <tr key={index} className={rowClass}>
            {commonCells}
            <td className={cellClass}>{item.plan_name}</td>
            <td className={cellClass}>{item.speed_category}</td>
            <td className={cellClass}>{item.contract_period}</td>
            {statusCell}
            {documentButton}
          </tr>
        );
      } else if (activeTab === 'tv') {
        return (
          <tr key={index} className={rowClass}>
            {commonCells}
            <td className={cellClass}>{item.service_type}</td>
            <td className={cellClass}>{item.settop_type}</td>
            <td className={cellClass}>{item.contract_period}</td>
            {statusCell}
            {documentButton}
          </tr>
        );
      } else if (activeTab === 'phone') {
        return (
          <tr key={index} className={rowClass}>
            {commonCells}
            <td className={cellClass}>{item.phone_type}</td>
            <td className={cellClass}>{item.plan_name}</td>
            <td className={cellClass}>{item.desired_number}</td>
            {statusCell}
            {documentButton}
          </tr>
        );
      } else if (activeTab === 'device') {
        return (
          <tr key={index} className={rowClass}>
            {commonCells}
            <td className={cellClass}>{item.device_model}</td>
            <td className={cellClass}>{item.price?.toLocaleString()}원</td>
            <td className={cellClass}>{item.purchase_type}</td>
            {statusCell}
            {documentButton}
          </tr>
        );
      }
      return null;
    });
  };

  const tabs = [
    { id: 'internet', label: '인터넷 계약', icon: Wifi },
    { id: 'tv', label: 'TV 계약', icon: Tv },
    { id: 'phone', label: '전화 계약', icon: Phone },
    { id: 'device', label: '단말 판매', icon: Smartphone },
  ];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">계약 관리</h1>
          <p className="text-sm text-gray-500 mt-1">
            상품별 계약 현황 및 관련 서류를 관리합니다
          </p>
        </div>
        <button className="px-4 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-2">
          <Download size={18} />
          엑셀 다운로드
        </button>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as TabType)}
              className={`
                group inline-flex items-center py-4 px-1 border-b-2 font-medium text-sm
                ${activeTab === tab.id
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}
              `}
            >
              <tab.icon
                className={`
                  -ml-0.5 mr-2 h-5 w-5
                  ${activeTab === tab.id ? 'text-blue-500' : 'text-gray-400 group-hover:text-gray-500'}
                `}
              />
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Search and Filter Bar */}
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <div className="flex flex-col md:flex-row gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
            <input
              type="text"
              placeholder="고객명 또는 계약번호로 검색..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div className="flex items-center gap-2">
            <Filter className="text-gray-400" size={20} />
            <select className="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500">
              <option value="all">전체 상태</option>
              <option value="active">활성</option>
              <option value="pending">대기</option>
            </select>
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              {renderTableHeader()}
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {renderTableBody()}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default Contracts;
