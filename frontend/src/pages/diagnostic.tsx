import { useEffect, useState } from 'react';

export default function DiagnosticPage() {
  const [apiUrl, setApiUrl] = useState('');
  const [backendHealth, setBackendHealth] = useState<any>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    const url = process.env.NEXT_PUBLIC_API_URL || 'not set';
    setApiUrl(url);

    // Test backend connection
    const testBackend = async () => {
      try {
        const response = await fetch(`${url}/health`);
        const data = await response.json();
        setBackendHealth({ status: 'success', data });
      } catch (err: any) {
        setError(err.message);
        setBackendHealth({ status: 'error', message: err.message });
      }
    };

    if (url !== 'not set') {
      testBackend();
    }
  }, []);

  return (
    <div style={{ padding: '2rem', fontFamily: 'monospace' }}>
      <h1>🔍 Deployment Diagnostic</h1>
      
      <div style={{ marginTop: '2rem', padding: '1rem', background: '#f5f5f5', borderRadius: '8px' }}>
        <h2>Environment Variables</h2>
        <p><strong>NEXT_PUBLIC_API_URL:</strong> {apiUrl}</p>
      </div>

      <div style={{ marginTop: '2rem', padding: '1rem', background: '#f5f5f5', borderRadius: '8px' }}>
        <h2>Backend Connection Test</h2>
        {backendHealth ? (
          <div>
            <p><strong>Status:</strong> {backendHealth.status}</p>
            {backendHealth.status === 'success' ? (
              <pre style={{ background: '#e8f5e9', padding: '1rem', borderRadius: '4px' }}>
                {JSON.stringify(backendHealth.data, null, 2)}
              </pre>
            ) : (
              <pre style={{ background: '#ffebee', padding: '1rem', borderRadius: '4px' }}>
                {backendHealth.message}
              </pre>
            )}
          </div>
        ) : (
          <p>Testing...</p>
        )}
        {error && (
          <div style={{ marginTop: '1rem', padding: '1rem', background: '#ffebee', borderRadius: '4px' }}>
            <strong>Error:</strong> {error}
          </div>
        )}
      </div>

      <div style={{ marginTop: '2rem', padding: '1rem', background: '#f5f5f5', borderRadius: '8px' }}>
        <h2>Expected Configuration</h2>
        <p><strong>Frontend URL:</strong> https://frontend-tau-sage-99.vercel.app</p>
        <p><strong>Backend URL:</strong> https://deepfakedetection-production-ab9b.up.railway.app</p>
        <p><strong>Railway FRONTEND_ORIGINS should include:</strong></p>
        <pre style={{ background: 'white', padding: '0.5rem', borderRadius: '4px' }}>
https://frontend-tau-sage-99.vercel.app,http://localhost:3000
        </pre>
      </div>

      <div style={{ marginTop: '2rem' }}>
        <h2>Manual Test</h2>
        <p>Open browser console and try:</p>
        <pre style={{ background: '#f5f5f5', padding: '1rem', borderRadius: '4px' }}>
{`fetch('${apiUrl}/health')
  .then(r => r.json())
  .then(console.log)
  .catch(console.error)`}
        </pre>
      </div>
    </div>
  );
}
