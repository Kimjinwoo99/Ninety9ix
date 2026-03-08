import React from 'react';
import { Calendar, Download, TrendingUp, FileText, Clock, CheckCircle2 } from 'lucide-react';

const Report: React.FC = () => {
  const monthlyData = [
    { month: '1월', processed: 450, approved: 420, rejected: 30 },
    { month: '2월', processed: 520, approved: 495, rejected: 25 },
    { month: '3월', processed: 480, approved: 455, rejected: 25 },
    { month: '4월', processed: 550, approved: 520, rejected: 30 },
    { month: '5월', processed: 600, approved: 575, rejected: 25 },
    { month: '6월', processed: 580, approved: 560, rejected: 20 },
  ];

  const agentPerformance = {
    totalAnalyzed: 3180,
    correctPredictions: 2862,
    falsePositives: 156,
    falseNegatives: 162,
    accuracy: 90,
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">리포트</h1>
          <p className="text-sm text-gray-500 mt-1">
            처리 통계 및 Agent 성능 분석
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button className="px-4 py-2 border border-gray-300 text-gray-700 font-medium rounded-lg hover:bg-gray-50 transition-colors flex items-center gap-2">
            <Calendar size={18} />
            기간 선택
          </button>
          <button className="px-4 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-2">
            <Download size={18} />
            PDF 다운로드
          </button>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg p-6 text-white">
          <FileText className="mb-4 opacity-80" size={32} />
          <div className="text-3xl font-bold">{agentPerformance.totalAnalyzed}</div>
          <div className="text-sm opacity-90 mt-1">총 분석 문서</div>
        </div>

        <div className="bg-gradient-to-br from-green-500 to-green-600 rounded-lg p-6 text-white">
          <CheckCircle2 className="mb-4 opacity-80" size={32} />
          <div className="text-3xl font-bold">{agentPerformance.accuracy}%</div>
          <div className="text-sm opacity-90 mt-1">Agent 정확도</div>
        </div>

        <div className="bg-gradient-to-br from-purple-500 to-purple-600 rounded-lg p-6 text-white">
          <Clock className="mb-4 opacity-80" size={32} />
          <div className="text-3xl font-bold">3:42</div>
          <div className="text-sm opacity-90 mt-1">평균 처리 시간</div>
        </div>

        <div className="bg-gradient-to-br from-indigo-500 to-indigo-600 rounded-lg p-6 text-white">
          <TrendingUp className="mb-4 opacity-80" size={32} />
          <div className="text-3xl font-bold">+15%</div>
          <div className="text-sm opacity-90 mt-1">월간 증가율</div>
        </div>
      </div>

      {/* Monthly Trend Chart */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-6">월별 처리 추이</h3>
        <div className="h-80 flex items-end justify-around gap-4">
          {monthlyData.map((data, index) => {
            const maxValue = Math.max(...monthlyData.map((d) => d.processed));
            
            return (
              <div key={index} className="flex-1 flex flex-col items-center gap-2">
                <div className="w-full relative" style={{ height: '280px' }}>
                  {/* Approved */}
                  <div
                    className="absolute bottom-0 w-full bg-green-500 rounded-t hover:bg-green-600 transition-all cursor-pointer group"
                    style={{ height: `${(data.approved / maxValue) * 100}%` }}
                  >
                    <div className="hidden group-hover:block absolute -top-8 left-1/2 transform -translate-x-1/2 bg-gray-900 text-white text-xs px-2 py-1 rounded whitespace-nowrap">
                      승인: {data.approved}
                    </div>
                  </div>
                  
                  {/* Rejected */}
                  <div
                    className="absolute w-full bg-red-500 rounded-t hover:bg-red-600 transition-all cursor-pointer group"
                    style={{ 
                      bottom: `${(data.approved / maxValue) * 100}%`,
                      height: `${(data.rejected / maxValue) * 100}%`
                    }}
                  >
                    <div className="hidden group-hover:block absolute -top-8 left-1/2 transform -translate-x-1/2 bg-gray-900 text-white text-xs px-2 py-1 rounded whitespace-nowrap">
                      반려: {data.rejected}
                    </div>
                  </div>
                </div>
                
                <span className="text-sm font-medium text-gray-700">{data.month}</span>
                <span className="text-xs text-gray-500">{data.processed}건</span>
              </div>
            );
          })}
        </div>
        
        <div className="flex items-center justify-center gap-6 mt-6 pt-6 border-t border-gray-200">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-green-500 rounded"></div>
            <span className="text-sm text-gray-600">승인</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-red-500 rounded"></div>
            <span className="text-sm text-gray-600">반려</span>
          </div>
        </div>
      </div>

      {/* Agent Performance */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Accuracy Breakdown */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-6">Agent 판단 정확도</h3>
          
          <div className="space-y-4">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-700">정확한 판단</span>
                <span className="text-sm font-semibold text-green-600">
                  {agentPerformance.correctPredictions} / {agentPerformance.totalAnalyzed}
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-3">
                <div
                  className="bg-green-500 h-3 rounded-full"
                  style={{ width: `${(agentPerformance.correctPredictions / agentPerformance.totalAnalyzed) * 100}%` }}
                />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-700">False Positive (과탐지)</span>
                <span className="text-sm font-semibold text-yellow-600">
                  {agentPerformance.falsePositives}
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-3">
                <div
                  className="bg-yellow-500 h-3 rounded-full"
                  style={{ width: `${(agentPerformance.falsePositives / agentPerformance.totalAnalyzed) * 100}%` }}
                />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-700">False Negative (미탐지)</span>
                <span className="text-sm font-semibold text-red-600">
                  {agentPerformance.falseNegatives}
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-3">
                <div
                  className="bg-red-500 h-3 rounded-full"
                  style={{ width: `${(agentPerformance.falseNegatives / agentPerformance.totalAnalyzed) * 100}%` }}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Processing Time Distribution */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-6">처리 시간 분포</h3>
          
          <div className="space-y-4">
            {[
              { range: '1분 미만', count: 450, percentage: 15 },
              { range: '1-3분', count: 1200, percentage: 38 },
              { range: '3-5분', count: 980, percentage: 31 },
              { range: '5-10분', count: 420, percentage: 13 },
              { range: '10분 이상', count: 130, percentage: 3 },
            ].map((item, index) => (
              <div key={index}>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-700">{item.range}</span>
                  <span className="text-sm font-semibold text-gray-900">
                    {item.count}건 ({item.percentage}%)
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-3">
                  <div
                    className="bg-blue-500 h-3 rounded-full"
                    style={{ width: `${item.percentage * 2.5}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Report;

