import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export interface Topic {
  topicCode: string;
  topicTitle: string;
  component: string;
  topicStatus: string;
  solicitationTitle: string;
  topicId: string;
  programYear?: number;
  releaseNumber?: string;
  technologyArea?: string;
  keywords?: string[];
}

export interface SearchRequest {
  term?: string;
  page: number;
  page_size: number;
  components?: string[];
  program_years?: number[];
}

export interface SearchResponse {
  topics: Topic[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}

export interface DownloadRequest {
  selected_topics: string[];
  search_term?: string;
  page: number;
  page_size: number;
}

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const searchTopics = async (params: SearchRequest): Promise<SearchResponse> => {
  const response = await api.get('/search', { params });
  return response.data;
};

export const downloadPdf = async (topicId: string): Promise<Blob> => {
  const response = await api.get(`/download/${topicId}`, {
    responseType: 'blob',
  });
  return response.data;
};

export const downloadMultiplePdfs = async (request: DownloadRequest): Promise<Blob> => {
  const response = await api.post('/download-multiple', request, {
    responseType: 'blob',
  });
  return response.data;
}; 