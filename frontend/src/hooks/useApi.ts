import { useState, useCallback } from 'react';
import api from '@/services/api';
import { AxiosRequestConfig } from 'axios';

type ApiState<T> = {
  data: T | null;
  error: Error | null;
  loading: boolean;
};

type ApiHook<T> = ApiState<T> & {
  execute: (config?: AxiosRequestConfig) => Promise<T | undefined>;
  reset: () => void;
};

export function useApi<T = unknown>(
  method: 'get' | 'post' | 'put' | 'patch' | 'delete',
  url: string,
  _immediate = false,
): ApiHook<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  const reset = useCallback(() => {
    setData(null);
    setError(null);
    setLoading(false);
  }, []);

  const execute = useCallback(
    async (config?: AxiosRequestConfig): Promise<T | undefined> => {
      setLoading(true);
      setError(null);

      try {
        const result = await (api[method] as <T = unknown>(url: string, config?: AxiosRequestConfig) => Promise<T>)<T>(url, config);
        setData(result);
        return result;
      } catch (err) {
        setError(err as Error);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [method, url],
  );


  return { data, error, loading, execute, reset };
}

export function useApiGet<T = unknown>(url: string, immediate = true): ApiHook<T> {
  return useApi<T>('get', url, immediate);
}

export function useApiPost<T = unknown>(url: string): ApiHook<T> {
  return useApi<T>('post', url, false);
}

export function useApiPut<T = unknown>(url: string): ApiHook<T> {
  return useApi<T>('put', url, false);
}

export function useApiPatch<T = unknown>(url: string): ApiHook<T> {
  return useApi<T>('patch', url, false);
}

export function useApiDelete<T = unknown>(url: string): ApiHook<T> {
  return useApi<T>('delete', url, false);
}
