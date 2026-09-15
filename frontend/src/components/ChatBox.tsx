import { useState, type FormEvent } from "react"
import { askQuestion, type SearchResponse } from "../api"

export function ChatBox() {
    const [question, setQuestion] = useState("")
    const [result, setResult] = useState<SearchResponse | null>(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    async function handleSubmit(e: FormEvent<HTMLFormElement>) {
        e.preventDefault()      // stop the browser from reloading
        if (!question.trim()) return
        setLoading(true)
        setError(null)
        setResult(null)
        try {
            const data = await askQuestion(question)
            setResult(data)
        } catch {
            setError("Could not reach the search service.")
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="mt-8 border border-gray-200 rounded-lg p-4">
            <h2 className="text-lg font-semibold mb-3">Ask a question</h2>

            <form onSubmit={handleSubmit} className="flex gap-2">
                <input
                    type="text"
                    value={question}
                    onChange={e => setQuestion(e.target.value)}
                    placeholder="Ask about your uploaded documents…"
                    className="flex-1 border border-gray-300 rounded px-3 py-2 text-sm"
                />
                <button
                    type="submit"
                    disabled={loading}
                    className="bg-blue-600 text-white px-4 py-2 rounded text-sm disabled:opacity-50"
                >
                    {loading ? "Asking…" : "Ask"}
                </button>
            </form>

            {error && (
                <p className="text-red-500 text-sm mt-2">{error}</p>
            )}

            {result && (
                <div className="mt-4">
                    <p className="text-sm font-medium">Answer</p>
                    <p className="text-sm mt-1 whitespace-pre-wrap">{result.answer}</p>

                    {result.sources.length > 0 && (
                        <div className="mt-3">
                            <p className="text-xs font-medium text-gray-500 uppercase">Sources</p>
                            <ul className="mt-1 space-y-1">
                                {result.sources.map((src, i) => (
                                    <li key={i} className="text-xs text-gray-600 border-l-2 border-blue-300 pl-2">
                                        {src}
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}
                </div>
            )}
        </div>
    )
}