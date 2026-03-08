import React, { useState, useEffect } from 'react';
import { 
  TrendingUp, 
  TrendingDown, 
  Users, 
  FileCheck, 
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  Wifi,
  Tv,
  Phone,
  Smartphone
} from 'lucide-react';

type TabType = 'overview' | 'internet' | 'tv' | 'phone';

const Dashboard: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  
  // Overview Stats
  const [overviewStats, setOverviewStats] = useState({
    today: { total: 0, approved: 0, rejected: 0, pending: 0 },
    avgProcessingTime: 0,
    autoApprovalRate: 0,
  });

  // Detail Stats
  const [detailStats, setDetailStats] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [weekStats, setWeekStats] = useState<number[]>([0, 0, 0, 0, 0, 0, 0]);

  // Fetch Overview Data from localStorage
  useEffect(() => {
    const loadDashboardData = () => {
      try {
        const today = new Date().toISOString().split('T')[0];
        const dashboardStats = JSON.parse(localStorage.getItem('dashboardStats') || '{}');
        const weekStats = JSON.parse(localStorage.getItem('weekStats') || '[]');
        
        const todayStats = dashboardStats[today] || {
          total: 0,
          approved: 0,
          rejected: 0,
          pending: 0,
          processingTimes: [],
        };
        
        // 평균 처리 시간 계산
        const avgProcessingTime = todayStats.processingTimes.length > 0
          ? Math.round(todayStats.processingTimes.reduce((a: number, b: number) => a + b, 0) / todayStats.processingTimes.length)
          : 0;
        
        setOverviewStats({
          today: {
            total: todayStats.total,
            approved: todayStats.approved,
            rejected: todayStats.rejected,
            pending: todayStats.pending,
          },
          avgProcessingTime,
          autoApprovalRate: todayStats.total > 0 
            ? Math.round((todayStats.approved / todayStats.total) * 100)
            : 0,
        });
        
        // 주간 처리 추이 업데이트 (weekStats를 상태로 관리)
        // weekStats가 배열이고 길이가 7인지 확인
        let validWeekStats = weekStats;
        if (!Array.isArray(weekStats) || weekStats.length !== 7) {
          validWeekStats = [0, 0, 0, 0, 0, 0, 0];
        }
        setWeekStats(validWeekStats);
      } catch (error) {
        console.error('Error loading dashboard data:', error);
      }
    };
    
    loadDashboardData();
    
    // 주기적으로 업데이트 (다른 탭에서 승인 완료 시 반영)
    const interval = setInterval(loadDashboardData, 1000);
    return () => clearInterval(interval);
  }, []);

  // Fetch Detail Data when tab changes
  useEffect(() => {
    if (activeTab === 'overview') {
      setDetailStats(null);
      return;
    }

    const fetchDetail = async () => {
      setLoading(true);
      try {
        const response = await fetch(`http://localhost:8000/api/stats/${activeTab}`);
        if (!response.ok) throw new Error(`Failed to fetch ${activeTab} stats`);
        const data = await response.json();
        setDetailStats(data);
      } catch (error) {
        console.error(`Error fetching ${activeTab} stats:`, error);
      } finally {
        setLoading(false);
      }
    };

    fetchDetail();
  }, [activeTab]);

  const formatTime = (seconds: number) => {
    const minutes = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${minutes}분 ${secs}초`;
  };

  // --- Render Helpers ---

  const renderOverview = () => (
    <>
      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="p-3 bg-blue-100 rounded-lg">
              <Users className="text-blue-600" size={24} />
            </div>
            <div className="flex items-center text-green-600 text-sm font-medium">
              <TrendingUp size={16} />
              <span className="ml-1">+12%</span>
            </div>
          </div>
          <div className="text-3xl font-bold text-gray-900">{overviewStats.today.total}</div>
          <div className="text-sm text-gray-500 mt-1">오늘 처리 건수</div>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="p-3 bg-green-100 rounded-lg">
              <CheckCircle className="text-green-600" size={24} />
            </div>
            <div className="flex items-center text-green-600 text-sm font-medium">
              <TrendingUp size={16} />
              <span className="ml-1">+8%</span>
            </div>
          </div>
          <div className="text-3xl font-bold text-gray-900">{overviewStats.today.approved}</div>
          <div className="text-sm text-gray-500 mt-1">승인 완료</div>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="p-3 bg-purple-100 rounded-lg">
              <Clock className="text-purple-600" size={24} />
            </div>
            <div className="flex items-center text-green-600 text-sm font-medium">
              <TrendingDown size={16} />
              <span className="ml-1">-15%</span>
            </div>
          </div>
          <div className="text-3xl font-bold text-gray-900">{formatTime(overviewStats.avgProcessingTime)}</div>
          <div className="text-sm text-gray-500 mt-1">평균 처리 시간</div>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="p-3 bg-indigo-100 rounded-lg">
              <FileCheck className="text-indigo-600" size={24} />
            </div>
            <div className="flex items-center text-green-600 text-sm font-medium">
              <TrendingUp size={16} />
              <span className="ml-1">+5%</span>
            </div>
          </div>
          <div className="text-3xl font-bold text-gray-900">{overviewStats.autoApprovalRate}%</div>
          <div className="text-sm text-gray-500 mt-1">자동 승인율</div>
        </div>
      </div>

      {/* Charts Row - Mock for now */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">주간 처리 추이</h3>
          <div className="h-64 flex items-end justify-around gap-2">
            {weekStats.map((value, index) => {
              const maxValue = Math.max(...weekStats, 1);
              // 바 높이 계산: 최소 8px, 최대 100% (값이 0이면 4px)
              const heightPercent = maxValue > 0 ? (value / maxValue) * 100 : 0;
              const minHeightPx = value === 0 ? 4 : 8;
              // 퍼센트 높이를 픽셀로 변환 (256px = 100%)
              const heightPx = Math.max((heightPercent / 100) * 256, minHeightPx);
              
              return (
                <div key={index} className="flex-1 flex flex-col items-center">
                  <div
                    className="w-full bg-blue-500 rounded-t hover:bg-blue-600 transition-all cursor-pointer relative group"
                    style={{ 
                      height: `${heightPx}px`
                    }}
                  >
                    {value > 0 && (
                      <div className="hidden group-hover:block absolute -top-8 left-1/2 transform -translate-x-1/2 bg-gray-900 text-white text-xs px-2 py-1 rounded whitespace-nowrap z-10">
                        {value}건
                      </div>
                    )}
                  </div>
                  <span className="text-xs text-gray-500 mt-2">
                    {['월', '화', '수', '목', '금', '토', '일'][index]}
                  </span>
                  <span className="text-xs text-gray-700 font-medium mt-1">{value}</span>
                </div>
              );
            })}
          </div>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">오늘의 처리 상태</h3>
          <div className="space-y-4">
            <div>
               <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-700">승인 완료</span>
                <span className="text-sm font-semibold">{overviewStats.today.approved}건</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-3">
                <div 
                  className="bg-green-500 h-3 rounded-full transition-all" 
                  style={{ 
                    width: overviewStats.today.total > 0 
                      ? `${(overviewStats.today.approved / overviewStats.today.total) * 100}%` 
                      : '0%' 
                  }} 
                />
              </div>
            </div>
            {overviewStats.today.rejected > 0 && (
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-700">반려</span>
                  <span className="text-sm font-semibold">{overviewStats.today.rejected}건</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-3">
                  <div 
                    className="bg-red-500 h-3 rounded-full transition-all" 
                    style={{ 
                      width: overviewStats.today.total > 0 
                        ? `${(overviewStats.today.rejected / overviewStats.today.total) * 100}%` 
                        : '0%' 
                    }} 
                  />
                </div>
              </div>
            )}
            {overviewStats.today.pending > 0 && (
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-700">대기 중</span>
                  <span className="text-sm font-semibold">{overviewStats.today.pending}건</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-3">
                  <div 
                    className="bg-yellow-500 h-3 rounded-full transition-all" 
                    style={{ 
                      width: overviewStats.today.total > 0 
                        ? `${(overviewStats.today.pending / overviewStats.today.total) * 100}%` 
                        : '0%' 
                    }} 
                  />
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );

  const renderDetailStats = () => {
    if (loading) return <div className="text-center py-12">로딩 중...</div>;
    if (!detailStats) return <div className="text-center py-12">데이터가 없습니다.</div>;

    const dataKey = activeTab === 'internet' ? 'speed_distribution' : 'type_distribution';
    const distribution = detailStats[dataKey] || [];

    return (
      <div className="space-y-6">
        {/* Summary Card */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">총 가입 건수</h3>
          <p className="text-3xl font-bold text-blue-600">{detailStats.total_count}건</p>
        </div>

        {/* Distribution Chart (Simple Bar) */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-6">
            {activeTab === 'internet' ? '속도별 가입 현황' : '상품 유형별 가입 현황'}
          </h3>
          
          <div className="space-y-4">
            {distribution.map((item: any, index: number) => (
              <div key={index}>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-700">{item.name}</span>
                  <span className="text-sm font-semibold text-gray-900">{item.value}건</span>
                </div>
                <div className="w-full bg-gray-100 rounded-full h-4 overflow-hidden">
                  <div 
                    className="bg-blue-500 h-full rounded-full transition-all duration-500"
                    style={{ width: `${(item.value / detailStats.total_count) * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">대시보드</h1>
        <p className="text-sm text-gray-500 mt-1">
          서비스별 상세 현황을 확인하세요
        </p>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          {[
            { id: 'overview', label: '종합 현황', icon: Users },
            { id: 'internet', label: '인터넷', icon: Wifi },
            { id: 'tv', label: 'TV', icon: Tv },
            { id: 'phone', label: '전화', icon: Phone },
          ].map((tab) => (
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

      {/* Content */}
      {activeTab === 'overview' ? renderOverview() : renderDetailStats()}
    </div>
  );
};

export default Dashboard;
