'use client';
const API_BASE_URL = "http://localhost:5000/"; // Flask default port
import { useState } from 'react';

export default function Page() {
    const [query, setQuery] = useState('');
    const [output, setOutput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [currentCsvId, setCurrentCsvId] = useState<string | null>(null);
    const [results, setResults] = useState<any>(null);
    const [isNetworkError, setIsNetworkError] = useState(false);

    const submitQuery = async () => {
        if (!query.trim()) return;

        setIsLoading(true);
        setOutput('');
        setCurrentCsvId(null);
        setResults(null);
        setIsNetworkError(false);

        try {
            const response = await fetch("http://localhost:5000/query", {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query, include_csv_id: true }),
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            if (data.error) {
                setOutput(`Error: ${data.error}`);
                setIsNetworkError(false);
            } else {
                setCurrentCsvId(data.csv_id);
                setResults(data);
                setOutput('success');
                setIsNetworkError(false);
            }
        } catch (err: any) {
            const isNetworkIssue =
                err.name === 'TypeError' ||
                err.message.includes('fetch') ||
                err.message.includes('network') ||
                err.message.includes('Failed to fetch') ||
                err.message.includes('NetworkError') ||
                !navigator.onLine;

            if (isNetworkIssue) {
                setIsNetworkError(true);
                setOutput('Network error occurred. Please check your connection and try again.');
            } else {
                setIsNetworkError(false);
                setOutput(`Request failed: ${err.message}`);
            }
        } finally {
            setIsLoading(false);
        }
    };

    const downloadCsv = () => {
        if (!currentCsvId) {
            alert('No data available for CSV export');
            return;
        }

        const link = document.createElement('a');
        link.href = `${API_BASE_URL}/export-csv/${currentCsvId}`;
        link.download = `query_results_${currentCsvId}.csv`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    const handleExample = (text: string) => {
        setQuery(text);
        setTimeout(() => submitQuery(), 200);
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
        if (e.key === 'Enter') {
            submitQuery();
        }
    };

    return (
        <div
            className="min-h-screen font-sans"
            style={{ background: '#11111b', margin: 0, padding: '2rem' }}
            data-oid="_de4ccs"
        >
            <div
                className="max-w-6xl mx-auto rounded-lg shadow-lg"
                style={{ background: '#1e1e2e', padding: '2rem' }}
                data-oid="62u0p39"
            >
                <h2
                    className="text-2xl font-bold mb-6"
                    style={{ color: '#cdd6f4' }}
                    data-oid="ml-.kyg"
                >
                    IEX Electricity Market Query
                </h2>

                {/* Input Section */}
                <div className="flex gap-4 mb-4" data-oid="wq88dcv">
                    <div className="flex-1 relative" data-oid="kwjuc17">
                        <input
                            type="text"
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                            onKeyDown={handleKeyDown}
                            placeholder="Ask about electricity bids..."
                            className="w-full px-4 py-3 text-base border-2 border-gray-200 rounded-lg shadow-sm transition-all duration-200 ease-in-out focus:border-pink-400 focus:ring-2 focus:ring-pink-100 focus:outline-none hover:border-gray-300"
                            style={{ 
                                color: '#000000',
                                '::placeholder': { color: '#4a4a4a' }
                            }}
                            data-oid="14dybya"
                        />

                        <div
                            className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 pointer-events-none"
                            data-oid="bbremq9"
                        >
                            <svg
                                width="20"
                                height="20"
                                viewBox="0 0 24 24"
                                fill="none"
                                stroke="currentColor"
                                strokeWidth="2"
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                data-oid="7sphqzp"
                            >
                                <circle cx="11" cy="11" r="8" data-oid="82v_e_e"></circle>
                                <path d="m21 21-4.35-4.35" data-oid="imoop7x"></path>
                            </svg>
                        </div>
                    </div>

                    <button
                        onClick={submitQuery}
                        disabled={isLoading}
                        className="px-4 py-2 text-base cursor-pointer rounded border-none transition-all duration-200"
                        style={{
                            backgroundColor: isLoading ? '#6c7086' : '#f38ba8',
                            color: '#11111b',
                            fontWeight: '600',
                        }}
                        onMouseEnter={(e) => {
                            if (!isLoading) {
                                e.target.style.backgroundColor = '#eba0ac';
                            }
                        }}
                        onMouseLeave={(e) => {
                            if (!isLoading) {
                                e.target.style.backgroundColor = '#f38ba8';
                            }
                        }}
                        data-oid="ppqtxq:"
                    >
                        {isLoading ? 'Processing...' : 'Submit'}
                    </button>
                </div>

                {/* Example Buttons */}
                <div className="flex flex-wrap gap-2 mb-8" data-oid="h1m9nnp">
                    <button
                        onClick={() =>
                            handleExample('What is the average MCP_Rs_MWh for last week?')
                        }
                        className="px-3 py-2 text-sm cursor-pointer rounded border transition-all duration-200"
                        style={{
                            color: '#f38ba8',
                            backgroundColor: '#313244',
                            borderColor: '#f38ba8',
                        }}
                        onMouseEnter={(e) => {
                            e.target.style.backgroundColor = '#f38ba8';
                            e.target.style.color = '#11111b';
                        }}
                        onMouseLeave={(e) => {
                            e.target.style.backgroundColor = '#313244';
                            e.target.style.color = '#f38ba8';
                        }}
                        data-oid="tkdmjq_"
                    >
                        Avg MCP last week
                    </button>
                    <button
                        onClick={() => handleExample('Show me all purchase bids in RTM yesterday')}
                        className="px-3 py-2 text-sm cursor-pointer rounded border transition-all duration-200"
                        style={{
                            color: '#f38ba8',
                            backgroundColor: '#313244',
                            borderColor: '#f38ba8',
                        }}
                        onMouseEnter={(e) => {
                            e.target.style.backgroundColor = '#f38ba8';
                            e.target.style.color = '#11111b';
                        }}
                        onMouseLeave={(e) => {
                            e.target.style.backgroundColor = '#313244';
                            e.target.style.color = '#f38ba8';
                        }}
                        data-oid="exqgpkw"
                    >
                        RTM purchase bids
                    </button>
                    <button
                        onClick={() => handleExample('Show daily volume trends for the past month')}
                        className="px-3 py-2 text-sm cursor-pointer rounded border transition-all duration-200"
                        style={{
                            color: '#f38ba8',
                            backgroundColor: '#313244',
                            borderColor: '#f38ba8',
                        }}
                        onMouseEnter={(e) => {
                            e.target.style.backgroundColor = '#f38ba8';
                            e.target.style.color = '#11111b';
                        }}
                        onMouseLeave={(e) => {
                            e.target.style.backgroundColor = '#313244';
                            e.target.style.color = '#f38ba8';
                        }}
                        data-oid="l5if2bf"
                    >
                        Volume trends
                    </button>
                    <button
                        onClick={() => handleExample('Show price variations by hour for today')}
                        className="px-3 py-2 text-sm cursor-pointer rounded border transition-all duration-200"
                        style={{
                            color: '#f38ba8',
                            backgroundColor: '#313244',
                            borderColor: '#f38ba8',
                        }}
                        onMouseEnter={(e) => {
                            e.target.style.backgroundColor = '#f38ba8';
                            e.target.style.color = '#11111b';
                        }}
                        onMouseLeave={(e) => {
                            e.target.style.backgroundColor = '#313244';
                            e.target.style.color = '#f38ba8';
                        }}
                        data-oid="e8eioom"
                    >
                        Hourly prices
                    </button>
                </div>

                {/* Loading Indicator */}
                {isLoading && (
                    <div className="flex items-center gap-3 mt-8" data-oid="trhp0ug">
                        <div
                            className="inline-block w-5 h-5 border-3 rounded-full animate-spin"
                            style={{
                                borderColor: 'rgba(243, 139, 168, 0.3)',
                                borderTopColor: '#f38ba8',
                            }}
                            data-oid="7j0z6jz"
                        ></div>
                        <span style={{ color: '#cdd6f4' }} data-oid="io8tg.p">
                            Processing query...
                        </span>
                    </div>
                )}

                {/* Output Section */}
                {output && !isLoading && (
                    <div className="mt-8" data-oid="k.tgzc1">
                        {output.startsWith('Error:') ||
                        output.startsWith('Request failed:') ||
                        output.startsWith('Network error') ? (
                            <div
                                className="p-4 rounded-lg border-l-4"
                                style={{
                                    color: '#b00020',
                                    backgroundColor: '#fddede',
                                    borderLeftColor: isNetworkError ? '#ff9800' : '#b00020',
                                }}
                                data-oid="as4sp6n"
                            >
                                <div className="flex items-start gap-3" data-oid="3_qj-lz">
                                    <div className="flex-shrink-0 mt-0.5" data-oid="-3z6sm.">
                                        {isNetworkError ? (
                                            <svg
                                                width="20"
                                                height="20"
                                                viewBox="0 0 24 24"
                                                fill="none"
                                                stroke="currentColor"
                                                strokeWidth="2"
                                                strokeLinecap="round"
                                                strokeLinejoin="round"
                                                data-oid="n8yo3xc"
                                            >
                                                <path
                                                    d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"
                                                    data-oid="z40ev0w"
                                                ></path>
                                                <line
                                                    x1="12"
                                                    y1="9"
                                                    x2="12"
                                                    y2="13"
                                                    data-oid="3b99cp1"
                                                ></line>
                                                <line
                                                    x1="12"
                                                    y1="17"
                                                    x2="12.01"
                                                    y2="17"
                                                    data-oid="5egbgfy"
                                                ></line>
                                            </svg>
                                        ) : (
                                            <svg
                                                width="20"
                                                height="20"
                                                viewBox="0 0 24 24"
                                                fill="none"
                                                stroke="currentColor"
                                                strokeWidth="2"
                                                strokeLinecap="round"
                                                strokeLinejoin="round"
                                                data-oid="jd03bry"
                                            >
                                                <circle
                                                    cx="12"
                                                    cy="12"
                                                    r="10"
                                                    data-oid="1vr420m"
                                                ></circle>
                                                <line
                                                    x1="15"
                                                    y1="9"
                                                    x2="9"
                                                    y2="15"
                                                    data-oid="wn.:644"
                                                ></line>
                                                <line
                                                    x1="9"
                                                    y1="9"
                                                    x2="15"
                                                    y2="15"
                                                    data-oid="f6yc78o"
                                                ></line>
                                            </svg>
                                        )}
                                    </div>
                                    <div className="flex-1" data-oid="rrpya-c">
                                        <p className="font-medium mb-1" data-oid="krhcisg">
                                            {isNetworkError ? 'Connection Issue' : 'Error'}
                                        </p>
                                        <p className="text-sm" data-oid="7a:wpv8">
                                            {output}
                                        </p>
                                        {isNetworkError && (
                                            <button
                                                onClick={submitQuery}
                                                className="mt-3 px-4 py-2 text-sm font-medium rounded-md border border-transparent transition-colors duration-200"
                                                style={{
                                                    backgroundColor: '#e12885',
                                                    color: 'white',
                                                }}
                                                onMouseEnter={(e) =>
                                                    (e.target.style.backgroundColor = '#c21e73')
                                                }
                                                onMouseLeave={(e) =>
                                                    (e.target.style.backgroundColor = '#e12885')
                                                }
                                                data-oid="_t-isdq"
                                            >
                                                Try Again
                                            </button>
                                        )}
                                    </div>
                                </div>
                            </div>
                        ) : output === 'success' && results ? (
                            <div data-oid="o7bwj2c">
                                {/* Generated SQL */}
                                <p
                                    className="font-bold mb-2"
                                    style={{ color: '#cdd6f4' }}
                                    data-oid="uuf.07n"
                                >
                                    Generated SQL:
                                </p>
                                <pre
                                    className="p-4 rounded overflow-x-auto mb-6"
                                    style={{ backgroundColor: '#181825', color: '#cdd6f4' }}
                                    data-oid="cy-9tsb"
                                >
                                    {results.generated_sql}
                                </pre>

                                {/* Results */}
                                {results.results && results.results.rows.length > 0 ? (
                                    <div
                                        className={`grid gap-8 ${results.graph ? 'lg:grid-cols-2' : 'grid-cols-1'}`}
                                        data-oid="xwrev:7"
                                    >
                                        {/* Graph */}
                                        {results.graph && (
                                            <div
                                                className="text-center p-4 rounded-lg shadow-md"
                                                style={{ backgroundColor: '#313244' }}
                                                data-oid="ezoqyxl"
                                            >
                                                <div
                                                    className="text-xl font-bold mb-4"
                                                    style={{ color: '#cdd6f4' }}
                                                    data-oid="2hc7nl9"
                                                >
                                                    Data Visualization
                                                </div>
                                                <img
                                                    src={`data:image/png;base64,${results.graph}`}
                                                    alt="Data Visualization Chart"
                                                    className="max-w-full h-auto block mx-auto rounded"
                                                    data-oid="nvtrmdv"
                                                />
                                            </div>
                                        )}

                                        {/* Table */}
                                        <div className="overflow-x-auto" data-oid="ery4x09">
                                            <div
                                                className="flex justify-between items-center mb-4"
                                                data-oid=":gvxria"
                                            >
                                                <p
                                                    className="font-bold"
                                                    style={{ color: '#cdd6f4' }}
                                                    data-oid="3pxldg4"
                                                >
                                                    Results ({results.results.rows.length} rows):
                                                </p>
                                                <button
                                                    onClick={downloadCsv}
                                                    disabled={!currentCsvId}
                                                    className="px-4 py-2 text-sm rounded border-none cursor-pointer disabled:cursor-not-allowed transition-colors duration-200"
                                                    style={{
                                                        backgroundColor: currentCsvId
                                                            ? '#a6e3a1'
                                                            : '#6c7086',
                                                        color: '#11111b',
                                                    }}
                                                    onMouseEnter={(e) => {
                                                        if (currentCsvId) {
                                                            e.target.style.backgroundColor =
                                                                '#94d3a2';
                                                        }
                                                    }}
                                                    onMouseLeave={(e) => {
                                                        if (currentCsvId) {
                                                            e.target.style.backgroundColor =
                                                                '#a6e3a1';
                                                        }
                                                    }}
                                                    data-oid=".hgc:.l"
                                                >
                                                    Download CSV
                                                </button>
                                            </div>

                                            <table
                                                className="w-full border-collapse"
                                                data-oid="0etjpry"
                                            >
                                                <thead data-oid="nd-wysc">
                                                    <tr data-oid="s6kc2m2">
                                                        {results.results.columns.map((col, idx) => (
                                                            <th
                                                                key={idx}
                                                                className="p-2 border"
                                                                style={{
                                                                    borderColor: '#45475a',
                                                                    backgroundColor: '#45475a',
                                                                    color: '#cdd6f4',
                                                                }}
                                                                data-oid=".kheceb"
                                                            >
                                                                {col}
                                                            </th>
                                                        ))}
                                                    </tr>
                                                </thead>
                                                <tbody data-oid="g38-a2w">
                                                    {results.results.rows.map((row, rowIdx) => (
                                                        <tr key={rowIdx} data-oid="2wu_wq0">
                                                            {row.map((cell, cellIdx) => (
                                                                <td
                                                                    key={cellIdx}
                                                                    className="p-2 border"
                                                                    style={{
                                                                        borderColor: '#45475a',
                                                                        backgroundColor: '#313244',
                                                                        color: '#cdd6f4',
                                                                    }}
                                                                    data-oid="-m9doj1"
                                                                >
                                                                    {cell !== null ? cell : 'NULL'}
                                                                </td>
                                                            ))}
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                        </div>
                                    </div>
                                ) : (
                                    <p style={{ color: '#a6e3a1' }} data-oid="1xlp2-_">
                                        Query succeeded, but no rows returned.
                                    </p>
                                )}
                            </div>
                        ) : null}
                    </div>
                )}
            </div>
        </div>
    );
}
