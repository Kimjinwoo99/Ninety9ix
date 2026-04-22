import React, { useState } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { createAccessRequest } from '../api/springApi';
import type { UserRole } from '../types';

const Login: React.FC = () => {
  const { login, isAuthenticated, loading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [showRequestForm, setShowRequestForm] = useState(false);
  const [requestName, setRequestName] = useState('');
  const [employeeNumber, setEmployeeNumber] = useState('');
  const [department, setDepartment] = useState('');
  const [requestedRole, setRequestedRole] = useState<UserRole>('STAFF');
  const [requestSubmitting, setRequestSubmitting] = useState(false);
  const [requestMessage, setRequestMessage] = useState('');
  const [requestError, setRequestError] = useState('');

  if (!loading && isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  const nextPath = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname || '/dashboard';

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    setError('');
    try {
      await login(username.trim(), password);
      navigate(nextPath, { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : '로그인에 실패했습니다.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleAccessRequestSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setRequestSubmitting(true);
    setRequestError('');
    setRequestMessage('');
    try {
      await createAccessRequest({
        name: requestName.trim(),
        employeeNumber: employeeNumber.trim(),
        department: department.trim(),
        requestedRole,
      });
      setRequestMessage('아이디 발급 요청이 전송되었습니다. 관리자 승인 후 계정이 생성됩니다.');
      setRequestName('');
      setEmployeeNumber('');
      setDepartment('');
      setRequestedRole('STAFF');
    } catch (err) {
      setRequestError(err instanceof Error ? err.message : '요청 전송에 실패했습니다.');
    } finally {
      setRequestSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-white rounded-xl shadow-lg p-8 space-y-5">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">사내 시스템 로그인</h1>
          <p className="text-sm text-gray-500 mt-1">권한이 있는 관리자/실무자만 접근할 수 있습니다.</p>
        </div>

        <form className="space-y-2" onSubmit={handleSubmit}>
          <label className="block text-sm font-medium text-gray-700" htmlFor="username">
            아이디
          </label>
          <input
            id="username"
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="admin"
            required
            autoComplete="username"
          />
          <label className="block text-sm font-medium text-gray-700 mt-3" htmlFor="password">
            비밀번호
          </label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="비밀번호 입력"
            required
            autoComplete="current-password"
          />
          {error ? <p className="text-sm text-red-600">{error}</p> : null}
          <button
            type="submit"
            disabled={submitting}
            className="w-full mt-3 bg-blue-600 text-white py-2.5 rounded-lg font-semibold hover:bg-blue-700 disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {submitting ? '로그인 중...' : '로그인'}
          </button>
        </form>

        <button
          type="button"
          onClick={() => {
            setShowRequestForm((prev) => !prev);
            setRequestError('');
            setRequestMessage('');
          }}
          className="w-full border border-gray-300 text-gray-700 py-2.5 rounded-lg font-semibold hover:bg-gray-50"
        >
          아이디 발급 요청
        </button>

        {showRequestForm ? (
          <div className="border border-gray-200 rounded-lg p-4 space-y-3 bg-gray-50">
            <h2 className="text-sm font-semibold text-gray-900">사내 계정 발급 요청</h2>
            <form className="space-y-3" onSubmit={handleAccessRequestSubmit}>
              <input
                value={requestName}
                onChange={(e) => setRequestName(e.target.value)}
                placeholder="이름"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                required
              />
              <input
                value={employeeNumber}
                onChange={(e) => setEmployeeNumber(e.target.value)}
                placeholder="사원번호"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                required
              />
              <input
                value={department}
                onChange={(e) => setDepartment(e.target.value)}
                placeholder="부서"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                required
              />
              <select
                value={requestedRole}
                onChange={(e) => setRequestedRole(e.target.value as UserRole)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
              >
                <option value="STAFF">실무자 권한 요청</option>
                <option value="SYSTEM_ADMIN">시스템 관리자 권한 요청</option>
              </select>
              {requestError ? <p className="text-xs text-red-600">{requestError}</p> : null}
              {requestMessage ? <p className="text-xs text-green-600">{requestMessage}</p> : null}
              <button
                type="submit"
                disabled={requestSubmitting}
                className="w-full bg-gray-900 text-white py-2 rounded-lg text-sm font-medium hover:bg-black disabled:opacity-60"
              >
                {requestSubmitting ? '요청 전송 중...' : '요청 전송'}
              </button>
            </form>
          </div>
        ) : null}
      </div>
    </div>
  );
};

export default Login;
