export interface UploadOutcome<T> {
  ok: boolean;
  status: number;
  data: T | null;
}

/**
 * Posts `formData` to a same-origin BFF route with upload-progress events — something the
 * Fetch API has no way to report for a *request* body, so this is the one place in the app
 * that reaches for `XMLHttpRequest` instead of `fetch`. Only ever called with a same-origin
 * `/api/**` path: the browser must never call the backend directly.
 */
export function uploadFormData<T>(
  url: string,
  formData: FormData,
  onProgress: (percent: number) => void,
): Promise<UploadOutcome<T>> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", url);
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress(Math.round((event.loaded / event.total) * 100));
    };
    xhr.onload = () => {
      let data: T | null = null;
      try {
        data = xhr.responseText ? (JSON.parse(xhr.responseText) as T) : null;
      } catch {
        data = null;
      }
      resolve({ ok: xhr.status >= 200 && xhr.status < 300, status: xhr.status, data });
    };
    xhr.onerror = () => reject(new Error("Network error during upload"));
    xhr.send(formData);
  });
}
