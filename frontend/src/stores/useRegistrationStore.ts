import { create } from 'zustand';
import type { RegistrationSession, UploadedDocument, HighlightedIssue } from '../types';

interface AgentResult {
  success: boolean;
  results?: any[];
  final_report?: string;
  recommendations_report?: string;
  customer_analysis_report?: string;
  summary?: any;
  comparisons?: any[];
  highlights?: any;
  agent_logs?: any[];
  error?: string;
}

interface RegistrationStore {
  isModalOpen: boolean;
  currentSession: RegistrationSession | null;
  agentResult: AgentResult | null;
  
  openModal: () => void;
  closeModal: () => void;
  
  startNewSession: () => void;
  addDocument: (document: UploadedDocument) => void;
  removeDocument: (documentId: string) => void;
  updateDocumentStatus: (documentId: string, status: UploadedDocument['status'], progress?: number) => void;
  
  updateSessionStatus: (status: RegistrationSession['status']) => void;
  
  addIssues: (issues: HighlightedIssue[]) => void;
  markIssueAsReviewed: (issueId: string, note?: string, correctedValue?: unknown) => void;
  
  setAgentResult: (result: AgentResult | null) => void;
  
  completeSession: () => void;
  cancelSession: () => void;
}

export const useRegistrationStore = create<RegistrationStore>((set) => ({
  isModalOpen: false,
  currentSession: null,
  agentResult: null,
  
  openModal: () => {
    set({ isModalOpen: true });
  },
  
  closeModal: () => {
    set({ 
      isModalOpen: false, 
      currentSession: null,
      agentResult: null // Agent 결과도 초기화
    });
  },
  
  startNewSession: () => {
    const newSession: RegistrationSession = {
      id: `session-${Date.now()}`,
      documents: [],
      ocrResults: [],
      issues: [],
      status: 'uploading',
      createdAt: new Date(),
    };
    set({ 
      currentSession: newSession,
      agentResult: null // Agent 결과도 초기화
    });
  },
  
  addDocument: (document) => {
    set((state) => {
      if (!state.currentSession) return state;
      
      return {
        currentSession: {
          ...state.currentSession,
          documents: [...state.currentSession.documents, document],
        },
      };
    });
  },
  
  removeDocument: (documentId) => {
    set((state) => {
      if (!state.currentSession) return state;
      
      // 문서 삭제
      const updatedDocuments = state.currentSession.documents.filter(
        (doc) => doc.id !== documentId
      );
      
      // 관련 OCR 결과도 삭제
      const updatedOcrResults = state.currentSession.ocrResults.filter(
        (ocr) => ocr.documentId !== documentId
      );
      
      // 관련 이슈도 삭제
      const updatedIssues = state.currentSession.issues.filter(
        (issue) => issue.documentId !== documentId
      );
      
      return {
        currentSession: {
          ...state.currentSession,
          documents: updatedDocuments,
          ocrResults: updatedOcrResults,
          issues: updatedIssues,
        },
      };
    });
  },
  
  updateDocumentStatus: (documentId, status, progress) => {
    set((state) => {
      if (!state.currentSession) return state;
      
      return {
        currentSession: {
          ...state.currentSession,
          documents: state.currentSession.documents.map((doc) =>
            doc.id === documentId
              ? { ...doc, status, progress }
              : doc
          ),
        },
      };
    });
  },
  
  updateSessionStatus: (status) => {
    set((state) => {
      if (!state.currentSession) return state;
      
      return {
        currentSession: {
          ...state.currentSession,
          status,
        },
      };
    });
  },
  
  addIssues: (issues) => {
    set((state) => {
      if (!state.currentSession) return state;
      
      return {
        currentSession: {
          ...state.currentSession,
          issues: [...state.currentSession.issues, ...issues],
          status: 'reviewing',
        },
      };
    });
  },
  
  markIssueAsReviewed: (issueId, note, correctedValue) => {
    set((state) => {
      if (!state.currentSession) return state;
      
      return {
        currentSession: {
          ...state.currentSession,
          issues: state.currentSession.issues.map((issue) =>
            issue.id === issueId
              ? { ...issue, reviewed: true, reviewNote: note, correctedValue }
              : issue
          ),
        },
      };
    });
  },
  
  setAgentResult: (result) => {
    set({ agentResult: result });
  },
  
  completeSession: () => {
    set((state) => {
      if (!state.currentSession) return state;
      
      return {
        currentSession: {
          ...state.currentSession,
          status: 'completed',
          completedAt: new Date(),
        },
      };
    });
  },
  
  cancelSession: () => {
    set({ currentSession: null, agentResult: null, isModalOpen: false });
  },
}));

