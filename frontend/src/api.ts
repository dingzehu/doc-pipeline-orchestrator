export type JobStatus = 'QUEUED' | 'PROCESSING' | 'DONE' | 'FAILED'

export interface Job {
    id: number
    filename: string
    status: JobStatus
    result_json: Record<string, unknown> | null
    error: string | null
    created_at: string
}

export interface SearchResponse {
    answer: string
    sources: string[]
}

export async function uploadPdf(file: File): Promise<Job> {
    const form = new FormData()
    form.append('file', file)
    const res = await fetch('/api/upload/', {method: 'POST', body: form})
    if (!res.ok) throw new Error(`Upload failed: ${res.status}`)
    return res.json()
}

export async function fetchJobs(): Promise<Job[]> {
    const res = await fetch('/api/jobs/')
    if (!res.ok) throw new Error(`Failed to fetch jobs: ${res.status}`)
    return res.json()
}

export async function fetchStatus(id: number): Promise<Job> {
    const res = await fetch(`/api/status/${id}/`)
    if (!res.ok) throw new Error(`Failed to fetch status: ${res.status}`)
    return res.json()
}

export async function askQuestion(question: string): Promise<SearchResponse> {
    const res = await fetch('/api/ask/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
    })
    if (!res.ok) throw new Error (`Ask failed: ${res.status}`)
    return res.json()
}