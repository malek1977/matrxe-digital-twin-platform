import React from 'react';

export default function ImageUploaderPresign({ onUploaded }) {
  const inputRef = React.useRef();

  async function uploadFile(file) {
    const r = await fetch('/api/uploads/presign', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ filename: file.name, contentType: file.type })
    });
    if (!r.ok) throw new Error('presign failed');
    const { url, key } = await r.json();
    await fetch(url, { method: 'PUT', body: file, headers: { 'Content-Type': file.type } });
    onUploaded({ key });
  }

  return (
    <div>
      <input ref={inputRef} type="file" accept="image/*" onChange={e => uploadFile(e.target.files[0])} style={{display:'none'}} />
      <button type="button" onClick={() => inputRef.current?.click()}>Upload Image</button>
    </div>
  );
}
