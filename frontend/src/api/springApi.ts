import type { AccessRequest, AuthUser, Customer, ProvisionHistory, UserRole } from '../types';
import { getAuthToken } from './authStorage';

const springBase = (import.meta.env.VITE_SPRING_API_URL as string | undefined)?.replace(/\/$/, '');

export function isSpringConfigured(): boolean {
  return Boolean(springBase && springBase.length > 0);
}

function extractErrorMessage(rawText: string): string {
  try {
    const parsed = JSON.parse(rawText) as { message?: string; error?: string };
    return (parsed.message || parsed.error || rawText || '').toString();
  } catch {
    return rawText;
  }
}

function mapConflictMessage(rawText: string, fallback: string): string {
  const msg = extractErrorMessage(rawText);
  if (msg.includes('아이디')) return '중복된 아이디입니다';
  if (msg.includes('사원번호')) return '이미 아이디가 존재하는 사원번호입니다';
  return fallback;
}

async function springFetch(path: string, init?: RequestInit): Promise<Response> {
  if (!springBase) {
    throw new Error('VITE_SPRING_API_URL이 설정되지 않았습니다.');
  }
  const token = getAuthToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (init?.headers) {
    if (init.headers instanceof Headers) {
      init.headers.forEach((value, key) => {
        headers[key] = value;
      });
    } else if (Array.isArray(init.headers)) {
      init.headers.forEach(([key, value]) => {
        headers[key] = value;
      });
    } else {
      Object.assign(headers, init.headers);
    }
  }
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  const response = await fetch(`${springBase}${path}`, {
    ...init,
    headers,
  });
  if (response.status === 401) {
    throw new Error('인증이 만료되었습니다. 다시 로그인해 주세요.');
  }
  if (response.status === 403) {
    throw new Error('권한이 없습니다.');
  }
  return response;
}

export async function loginToSpring(payload: { username: string; password: string }): Promise<{ token: string; user: AuthUser }> {
  const res = await springFetch('/api/v1/auth/login', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`로그인 실패 (${res.status}): ${text}`);
  }
  const data: { token: string; tokenType: string; user: AuthUser } = await res.json();
  return {
    token: data.token,
    user: data.user,
  };
}

export async function fetchMeFromSpring(): Promise<AuthUser> {
  const res = await springFetch('/api/v1/auth/me', { method: 'GET' });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`내 정보 조회 실패 (${res.status}): ${text}`);
  }
  return await res.json();
}

export async function signUpStaffFromSpring(payload: {
  username: string;
  password: string;
  name: string;
  role: UserRole;
}): Promise<AuthUser> {
  const res = await springFetch('/api/v1/auth/signup', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const text = await res.text();
    if (res.status === 409) {
      throw new Error(mapConflictMessage(text, '중복 정보로 사용자 생성에 실패했습니다.'));
    }
    throw new Error(`사용자 생성 실패 (${res.status}): ${text}`);
  }
  return await res.json();
}

export async function provisionFromAccessRequest(payload: {
  requestId: number;
  username: string;
  password: string;
}): Promise<AuthUser> {
  const res = await springFetch('/api/v1/auth/provision-from-request', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const text = await res.text();
    if (res.status === 409) {
      throw new Error(mapConflictMessage(text, '중복 정보로 계정 생성에 실패했습니다.'));
    }
    throw new Error(`요청 기반 계정 생성 실패 (${res.status}): ${text}`);
  }
  return await res.json();
}

export async function fetchUsersFromSpring(): Promise<AuthUser[]> {
  const res = await springFetch('/api/v1/auth/users', { method: 'GET' });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`사용자 목록 조회 실패 (${res.status}): ${text}`);
  }
  return await res.json();
}

export async function deleteUserFromSpring(userId: number): Promise<void> {
  const res = await springFetch(`/api/v1/auth/users/${userId}`, { method: 'DELETE' });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`사용자 삭제 실패 (${res.status}): ${text}`);
  }
}

export async function fetchProvisionHistories(): Promise<ProvisionHistory[]> {
  const res = await springFetch('/api/v1/auth/provision-histories', { method: 'GET' });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`발급 히스토리 조회 실패 (${res.status}): ${text}`);
  }
  return await res.json();
}

export async function fetchCustomersFromSpring(): Promise<Customer[]> {
  const res = await springFetch('/api/v1/customers', { method: 'GET' });
  if (!res.ok) {
    throw new Error(`고객 목록 로드 실패 (${res.status})`);
  }
  const data: Array<Omit<Customer, 'registeredAt'> & { registeredAt: string }> = await res.json();
  return data.map((c) => ({
    ...c,
    registeredAt: new Date(c.registeredAt),
  }));
}

export async function postCustomerToSpring(customer: {
  id: string;
  name: string;
  phone: string;
  address?: string;
  registeredAt: Date;
  status: 'active' | 'inactive' | 'pending';
}): Promise<void> {
  const res = await springFetch('/api/v1/customers', {
    method: 'POST',
    body: JSON.stringify({
      id: customer.id,
      name: customer.name,
      phone: customer.phone,
      address: customer.address,
      registeredAt: customer.registeredAt.toISOString(),
      status: customer.status,
    }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Spring 고객 저장 실패 (${res.status}): ${text}`);
  }
}

export async function createAccessRequest(payload: {
  name: string;
  employeeNumber: string;
  department: string;
  requestedRole: UserRole;
}): Promise<AccessRequest> {
  const res = await springFetch('/api/v1/access-requests', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const text = await res.text();
    if (res.status === 409) {
      throw new Error(mapConflictMessage(text, '이미 접수된 정보가 있어 요청할 수 없습니다.'));
    }
    throw new Error(`발급 요청 실패 (${res.status}): ${text}`);
  }
  return await res.json();
}

export async function fetchAccessRequests(status?: 'PENDING' | 'APPROVED' | 'REJECTED'): Promise<AccessRequest[]> {
  const query = status ? `?status=${status}` : '';
  const res = await springFetch(`/api/v1/access-requests${query}`, { method: 'GET' });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`요청 목록 조회 실패 (${res.status}): ${text}`);
  }
  return await res.json();
}

export async function reviewAccessRequest(
  requestId: number,
  payload: { status: 'REJECTED'; reviewNote?: string }
): Promise<AccessRequest> {
  const res = await springFetch(`/api/v1/access-requests/${requestId}/review`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`요청 처리 실패 (${res.status}): ${text}`);
  }
  return await res.json();
}
