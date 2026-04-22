import React from 'react';
import { RefreshCw } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import {
  deleteUserFromSpring,
  fetchAccessRequests,
  fetchProvisionHistories,
  fetchUsersFromSpring,
  provisionFromAccessRequest,
  reviewAccessRequest,
} from '../api/springApi';
import type { AccessRequest, AuthUser, ProvisionHistory } from '../types';

const UserManagement: React.FC = () => {
  const { user: currentUser } = useAuth();
  const [users, setUsers] = React.useState<AuthUser[]>([]);
  const [usersLoading, setUsersLoading] = React.useState(false);
  const [usersError, setUsersError] = React.useState('');
  const [deletingUserId, setDeletingUserId] = React.useState<number | null>(null);

  const [accessRequests, setAccessRequests] = React.useState<AccessRequest[]>([]);
  const [requestLoading, setRequestLoading] = React.useState(false);
  const [requestError, setRequestError] = React.useState('');
  const [requestItemErrors, setRequestItemErrors] = React.useState<Record<number, string>>({});
  const [accountDrafts, setAccountDrafts] = React.useState<Record<number, { username: string; password: string }>>({});
  const [provisioningRequestId, setProvisioningRequestId] = React.useState<number | null>(null);

  const [histories, setHistories] = React.useState<ProvisionHistory[]>([]);
  const [historiesLoading, setHistoriesLoading] = React.useState(false);
  const [historiesError, setHistoriesError] = React.useState('');

  const loadUsers = React.useCallback(async () => {
    setUsersLoading(true);
    setUsersError('');
    try {
      setUsers(await fetchUsersFromSpring());
    } catch (err) {
      setUsersError(err instanceof Error ? err.message : '사용자 목록 조회 실패');
    } finally {
      setUsersLoading(false);
    }
  }, []);

  const loadRequests = React.useCallback(async () => {
    setRequestLoading(true);
    setRequestError('');
    setRequestItemErrors({});
    try {
      setAccessRequests(await fetchAccessRequests());
    } catch (err) {
      setRequestError(err instanceof Error ? err.message : '요청 목록 조회 실패');
    } finally {
      setRequestLoading(false);
    }
  }, []);

  const loadHistories = React.useCallback(async () => {
    setHistoriesLoading(true);
    setHistoriesError('');
    try {
      setHistories(await fetchProvisionHistories());
    } catch (err) {
      setHistoriesError(err instanceof Error ? err.message : '발급 이력 조회 실패');
    } finally {
      setHistoriesLoading(false);
    }
  }, []);

  React.useEffect(() => {
    void loadUsers();
    void loadRequests();
    void loadHistories();
  }, [loadUsers, loadRequests, loadHistories]);

  const canDeleteTarget = (target: AuthUser): { allowed: boolean; reason?: string } => {
    if (currentUser?.id === target.id) return { allowed: false, reason: '본인 계정 삭제 불가' };
    if (target.superAdmin || target.username === 'admin') return { allowed: false, reason: '최고 관리자 계정 삭제 불가' };
    if (target.role === 'SYSTEM_ADMIN' && !(currentUser?.username === 'admin' || currentUser?.superAdmin)) {
      return { allowed: false, reason: '다른 관리자 삭제는 최고 관리자만 가능' };
    }
    return { allowed: true };
  };

  const handleDelete = async (target: AuthUser) => {
    const permission = canDeleteTarget(target);
    if (!permission.allowed) {
      alert(permission.reason);
      return;
    }
    if (!confirm(`${target.username} 계정을 삭제하시겠습니까?`)) return;
    setDeletingUserId(target.id);
    try {
      await deleteUserFromSpring(target.id);
      await loadUsers();
    } catch (err) {
      setUsersError(err instanceof Error ? err.message : '사용자 삭제 실패');
    } finally {
      setDeletingUserId(null);
    }
  };

  const updateDraft = (id: number, key: 'username' | 'password', value: string) => {
    setAccountDrafts((prev) => ({
      ...prev,
      [id]: {
        username: prev[id]?.username ?? '',
        password: prev[id]?.password ?? '',
        [key]: value,
      },
    }));
  };

  const handleProvision = async (request: AccessRequest) => {
    const draft = accountDrafts[request.id] ?? { username: '', password: '' };
    if (!draft.username.trim() || draft.password.length < 8) {
      setRequestItemErrors((prev) => ({ ...prev, [request.id]: '요청별 아이디/비밀번호(8자 이상)를 입력해 주세요.' }));
      return;
    }
    const duplicatedUsername = users.some((u) => u.username === draft.username.trim());
    if (duplicatedUsername) {
      setRequestItemErrors((prev) => ({ ...prev, [request.id]: '중복된 아이디입니다' }));
      return;
    }
    const duplicatedEmployeeNumber = users.some((u) => u.employeeNumber && u.employeeNumber === request.employeeNumber);
    if (duplicatedEmployeeNumber) {
      setRequestItemErrors((prev) => ({ ...prev, [request.id]: '이미 아이디가 존재하는 사원번호입니다' }));
      return;
    }
    setProvisioningRequestId(request.id);
    setRequestItemErrors((prev) => {
      const next = { ...prev };
      delete next[request.id];
      return next;
    });
    try {
      await provisionFromAccessRequest({
        requestId: request.id,
        username: draft.username.trim(),
        password: draft.password,
      });
      await loadUsers();
      await loadRequests();
      await loadHistories();
      setAccountDrafts((prev) => {
        const next = { ...prev };
        delete next[request.id];
        return next;
      });
    } catch (err) {
      setRequestItemErrors((prev) => ({
        ...prev,
        [request.id]: err instanceof Error ? err.message : '요청 처리 실패',
      }));
    } finally {
      setProvisioningRequestId(null);
    }
  };

  const handleReject = async (request: AccessRequest) => {
    try {
      setRequestItemErrors((prev) => {
        const next = { ...prev };
        delete next[request.id];
        return next;
      });
      await reviewAccessRequest(request.id, { status: 'REJECTED', reviewNote: '관리자 반려' });
      await loadRequests();
    } catch (err) {
      setRequestItemErrors((prev) => ({
        ...prev,
        [request.id]: err instanceof Error ? err.message : '반려 처리 실패',
      }));
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">사용자 관리</h1>
          <p className="text-sm text-gray-500 mt-1">권한 사용자 조회/삭제와 발급 요청 처리를 관리합니다.</p>
        </div>
        <button
          onClick={() => {
            void loadUsers();
            void loadRequests();
            void loadHistories();
          }}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm hover:bg-gray-50 flex items-center gap-2"
        >
          <RefreshCw size={16} />
          새로고침
        </button>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-200 font-semibold text-gray-900">권한 사용자 목록</div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">ID</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">이름</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">사원번호</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">부서</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">권한</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">삭제</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {usersLoading ? (
                <tr><td colSpan={6} className="px-6 py-4 text-center text-sm text-gray-500">로딩 중...</td></tr>
              ) : usersError ? (
                <tr><td colSpan={6} className="px-6 py-4 text-center text-sm text-red-600">{usersError}</td></tr>
              ) : users.length === 0 ? (
                <tr><td colSpan={6} className="px-6 py-4 text-center text-sm text-gray-500">사용자가 없습니다.</td></tr>
              ) : (
                users.map((u) => {
                  const permission = canDeleteTarget(u);
                  return (
                    <tr key={u.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 text-sm">{u.username}</td>
                      <td className="px-6 py-4 text-sm">{u.name}</td>
                      <td className="px-6 py-4 text-sm">{u.employeeNumber || '-'}</td>
                      <td className="px-6 py-4 text-sm">{u.department || '-'}</td>
                      <td className="px-6 py-4 text-sm">{u.role}{u.superAdmin ? ' (최고 관리자)' : ''}</td>
                      <td className="px-6 py-4 text-sm">
                        <button
                          onClick={() => void handleDelete(u)}
                          disabled={!permission.allowed || deletingUserId === u.id}
                          className="px-2 py-1 text-xs rounded bg-red-600 text-white disabled:opacity-50"
                          title={permission.reason}
                        >
                          {deletingUserId === u.id ? '삭제 중...' : '삭제'}
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 p-4 space-y-3">
        <h2 className="font-semibold text-gray-900">발급 요청 처리</h2>
        {requestLoading ? (
          <p className="text-sm text-gray-500">요청 로딩 중...</p>
        ) : accessRequests.length === 0 ? (
          <p className="text-sm text-gray-500">요청이 없습니다.</p>
        ) : (
          accessRequests.map((r) => (
            <div key={r.id} className="border border-gray-200 rounded-lg p-3">
              <div className="text-sm font-medium">{r.name} / {r.employeeNumber} / {r.department} / 요청권한 {r.requestedRole}</div>
              <div className="text-xs text-gray-500 mt-1">상태: {r.status}</div>
              {r.status === 'PENDING' ? (
                <div className="mt-2 flex items-center gap-2">
                  <input
                    value={accountDrafts[r.id]?.username ?? ''}
                    onChange={(e) => updateDraft(r.id, 'username', e.target.value)}
                    placeholder="아이디"
                    className="border border-gray-300 rounded px-2 py-1 text-xs"
                  />
                  <input
                    type="password"
                    value={accountDrafts[r.id]?.password ?? ''}
                    onChange={(e) => updateDraft(r.id, 'password', e.target.value)}
                    placeholder="비밀번호(8자 이상)"
                    className="border border-gray-300 rounded px-2 py-1 text-xs"
                  />
                  <button
                    onClick={() => void handleProvision(r)}
                    disabled={provisioningRequestId === r.id}
                    className="px-2 py-1 text-xs bg-green-600 text-white rounded disabled:opacity-50"
                  >
                    {provisioningRequestId === r.id ? '처리 중...' : '승인+계정생성'}
                  </button>
                  <button
                    onClick={() => void handleReject(r)}
                    className="px-2 py-1 text-xs bg-red-600 text-white rounded"
                  >
                    반려
                  </button>
                </div>
              ) : null}
              {requestItemErrors[r.id] ? (
                <p className="text-xs text-red-600 mt-2">{requestItemErrors[r.id]}</p>
              ) : null}
            </div>
          ))
        )}
      </div>

      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <h2 className="font-semibold text-gray-900 mb-3">발급 완료 알림 로그</h2>
        {historiesLoading ? (
          <p className="text-sm text-gray-500">이력 로딩 중...</p>
        ) : historiesError ? (
          <p className="text-sm text-red-600">{historiesError}</p>
        ) : histories.length === 0 ? (
          <p className="text-sm text-gray-500">발급 이력이 없습니다.</p>
        ) : (
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {histories.map((h) => (
              <div key={h.id} className="border border-gray-200 rounded p-2 text-sm">
                <div>{h.message}</div>
                <div className="text-xs text-gray-500">
                  요청 {h.accessRequestId} / 사용자 {h.userId} / 처리자 {h.issuedBy} / {new Date(h.issuedAt).toLocaleString('ko-KR')}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default UserManagement;
