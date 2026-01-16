// TwinService - simple wrapper to post multipart FormData to /api/twins
export const TwinService = {
  async createDigitalTwin(formData) {
    const resp = await fetch('/api/twins', {
      method: 'POST',
      credentials: 'include',
      body: formData
    });
    if (!resp.ok) {
      const err = await resp.json().catch(()=>({ message: 'server_error' }));
      throw new Error(err?.message || `HTTP ${resp.status}`);
    }
    return resp.json();
  }
};
export default TwinService;
