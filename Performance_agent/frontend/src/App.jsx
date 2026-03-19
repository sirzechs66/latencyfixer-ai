import { useState, useEffect } from 'react'

// Backend API URL - configurable via environment
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function App() {
  const [logs, setLogs] = useState('')
  const [code, setCode] = useState('')
  const [systemDesc, setSystemDesc] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [testCases, setTestCases] = useState([])

  // Convert string to Title Case (JS doesn't have .title())
  const titleCase = (s = '') => {
    return String(s)
      .toLowerCase()
      .split(' ')
      .map(w => w.charAt(0).toUpperCase() + w.slice(1))
      .join(' ')
  }

  // Load test cases on mount
  useEffect(() => {
    fetch(`${API_URL}/test-cases`)
      .then(res => res.json())
      .then(data => {
        if (data.test_cases) {
          setTestCases(data.test_cases)
        }
      })
      .catch(err => console.error('Failed to load test cases:', err))
  }, [])

  // Load a test case into the input fields
  const loadTestCase = (testCase) => {
    setLogs(testCase.logs)
    setCode(testCase.code)
    setSystemDesc(testCase.description || '')
    setResult(null)
    setError(null)
  }

  // Run analysis
  const analyze = async () => {
    if (!logs.trim()) {
      setError('Please enter logs to analyze')
      return
    }

    setLoading(true)
    setError(null)

    try {
      const response = await fetch(`${API_URL}/analyze`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          logs,
          code,
          system_description: systemDesc
        })
      })

      if (!response.ok) {
        const errData = await response.json()
        throw new Error(errData.detail || 'Analysis failed')
      }

      const data = await response.json()
      setResult(data)
    } catch (err) {
      setError(err.message)
      setResult(null)
    } finally {
      setLoading(false)
    }
  }

  // Format JSON with syntax highlighting
  const formatJSON = (obj) => {
    const json = JSON.stringify(obj, null, 2)
    return json.replace(
      /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g,
      (match) => {
        let cls = 'json-number'
        if (/^"/.test(match)) {
          if (/:$/.test(match)) {
            cls = 'json-key'
          } else {
            cls = 'json-string'
          }
        } else if (/true|false/.test(match)) {
          cls = 'json-boolean'
        } else if (/null/.test(match)) {
          cls = 'json-null'
        }
        return `<span class="${cls}">${match}</span>`
      }
    )
  }

  // Get score badge class
  const getScoreClass = (score) => {
    if (score >= 8500) return 'excellent'
    if (score >= 7000) return 'good'
    return 'fair'
  }

  return (
    <div className="app-container">
      <header className="header">
        <h1>LatencyFixer AI</h1>
        <p>Performance latency analysis using LangGraph-based multi-stage agent</p>
      </header>

      <div className="main-content">
        {/* Input Section */}
        <div className="input-section">
          {/* Test Case Buttons */}
          {testCases.length > 0 && (
            <div className="test-cases-section">
              <h3>Load Test Case:</h3>
              <div className="test-buttons">
                {testCases.map((tc, idx) => (
                  <button
                    key={idx}
                    className="test-btn"
                    onClick={() => loadTestCase(tc)}
                  >
                    {titleCase(tc.name.replace(/_/g, ' '))}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Logs Input */}
          <div className="form-group">
            <label htmlFor="logs">Error Logs / Stack Traces</label>
            <textarea
              id="logs"
              value={logs}
              onChange={(e) => setLogs(e.target.value)}
              placeholder="Paste your error logs, stack traces, and performance warnings here..."
            />
          </div>

          {/* Code Input */}
          <div className="form-group">
            <label htmlFor="code">Code Snippets (optional)</label>
            <textarea
              id="code"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="Paste relevant code snippets (optional, improves analysis accuracy)..."
              style={{ minHeight: '120px' }}
            />
          </div>

          {/* System Description */}
          <div className="form-group">
            <label htmlFor="system">System Description (optional)</label>
            <textarea
              id="system"
              value={systemDesc}
              onChange={(e) => setSystemDesc(e.target.value)}
              placeholder="Brief description of the system (e.g., 'Real-time streaming API processing data chunks')..."
              style={{ minHeight: '60px' }}
            />
          </div>

          {/* Analyze Button */}
          <button
            className="analyze-btn"
            onClick={analyze}
            disabled={loading || !logs.trim()}
          >
            {loading ? 'Analyzing...' : 'Analyze'}
          </button>

          {/* Error Display */}
          {error && (
            <div className="error">
              <strong>Error:</strong> {error}
            </div>
          )}
        </div>

        {/* Output Section */}
        <div className="output-section">
          {loading && (
            <div className="loading">
              <div className="loading-spinner"></div>
              <p>Running analysis pipeline...</p>
            </div>
          )}

          {result && !loading && (
            <div className="results">
              <div className="results-header">
                <h3>Analysis Results</h3>
                {(() => {
                  const finalScore = (result && result.final_score != null) ? result.final_score : 0
                  return (
                    <>
                      <span className={`score-badge ${getScoreClass(finalScore)}`}>
                        Score: {finalScore.toFixed(0)} / 10,000
                      </span>
                      {(result && (result.llm_requested !== undefined || result.bedrock_available !== undefined)) && (
                        <div style={{ marginLeft: '12px', fontSize: '0.85rem', color: '#666' }}>
                          <div>LLM Requested: {String(result.llm_requested)}</div>
                          <div>Bedrock Available: {String(result.bedrock_available)}</div>
                        </div>
                      )}
                    </>
                  )
                })()}
              </div>

              {/* Root Causes */}
              {result.root_causes?.length > 0 && (
                <div className="result-section">
                  <h4>Root Causes ({result.root_causes.length})</h4>
                  {result.root_causes.map((rc, idx) => (
                    <div key={idx} className="rc-item">
                      <h5>{rc.description}</h5>
                      <p><strong>Category:</strong> {rc.category}</p>
                      <p><strong>Confidence:</strong> {(rc.confidence * 100).toFixed(0)}%</p>
                      {rc.file_path && <p><strong>File:</strong> {rc.file_path}</p>}
                      <div className="meta">
                        Evidence: {rc.evidence?.length || 0} items
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Bottlenecks */}
              {result.bottlenecks?.length > 0 && (
                <div className="result-section">
                  <h4>Bottlenecks ({result.bottlenecks.length})</h4>
                  {result.bottlenecks.map((bn, idx) => (
                    <div key={idx} className="bn-item">
                      <h5>{bn.description}</h5>
                      <p><strong>Severity:</strong> {bn.severity}</p>
                      <p><strong>Impact:</strong> {bn.estimated_impact_ms?.toFixed(0)}ms</p>
                      <p><strong>Location:</strong> {bn.location}</p>
                    </div>
                  ))}
                </div>
              )}

              {/* Fixes */}
              {result.fixes?.length > 0 && (
                <div className="result-section">
                  <h4>Recommended Fixes ({result.fixes.length})</h4>
                  {result.fixes.map((fix, idx) => (
                    <div key={idx} className="fix-item">
                      <h5>{fix.description}</h5>
                      <p><strong>Type:</strong> {fix.fix_type}</p>
                      <p><strong>Expected Improvement:</strong> {fix.expected_latency_improvement_pct?.toFixed(0)}%</p>
                      <p><strong>Complexity:</strong> {fix.complexity}</p>
                      {fix.code_change && (
                        <p><strong>Change:</strong> {fix.code_change}</p>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* Metrics */}
              {result.metrics && Object.keys(result.metrics).length > 0 && (
                <div className="result-section">
                  <h4>Dimension Scores</h4>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                    {Object.entries(result.metrics).map(([key, value]) => (
                      <div key={key}>
                        <strong>{titleCase(key.replace(/_/g, ' '))}:</strong> {(Number(value) || 0).toFixed(3)}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Raw JSON */}
              <div className="result-section">
                <h4>Raw JSON Output</h4>
                <div
                  className="json-output"
                  dangerouslySetInnerHTML={{ __html: formatJSON(result) }}
                />
              </div>
            </div>
          )}

          {!result && !loading && (
            <div style={{ color: '#999', textAlign: 'center', padding: '40px' }}>
              <p>Results will appear here after analysis</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default App
