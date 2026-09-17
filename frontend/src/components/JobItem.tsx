import { useEffect, useRef, useState } from "react"
import { fetchStatus, summarisePdf, type Job } from "../api"
import { useSSE } from "../hooks/useSSE"

interface Props {
    initialJob: Job
}

export function JobItem({ initialJob }: Props) {
    const [job, setJob] = useState<Job>(initialJob)
    const [summarising, setSummarising] = useState(false)
    const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)
    const { event, done } = useSSE(job.id, initialJob.status)

    // SSE update --- keep job status in sync with live events
    useEffect(() => {
        if (!event) return
        setJob(prev => ({ ...prev, status: event.status as Job['status'] }))
    }, [event])

    // polling fallback --- kicks in only after SSE finishes or if SSE never connected
    useEffect(() => {
        if (!done) return
        fetchStatus(job.id).then(setJob)
    }, [done])

    // stop polling when summary arrives or component unmounts
    useEffect(() => {
        if (job.summary && pollRef.current) {
            clearInterval(pollRef.current)
            pollRef.current = null
            setSummarising(false)
        }
    }, [job.summary])

    async function handleSummarise() {
        setSummarising(true)
        await summarisePdf(job.id)
        pollRef.current = setInterval(async () => {
            const updated = await fetchStatus(job.id)
            setJob(updated)
        }, 3000)
    }

    const statusColour: Record<Job['status'], string> = {
        QUEUED:     'text-gray-400',
        PROCESSING: 'text-yellow-400',
        DONE:       'text-green-400',
        FAILED:     'text-red-400'
    }

    const step = event?.step ?? ''

    return (
        <div className="border rounded p-3 mb-2">
            <div className="flex justify-between items-center">
                <span className="font-mono text-sm">{job.filename}</span>
                <div className="flex items-center gap-2">
                    {job.status === 'DONE' && !job.summary && (
                        <button
                            onClick={handleSummarise}
                            disabled={summarising}
                            className="text-xs px-2 py-1 rounded bg-blue-500 text-white disabled:opacity-50"
                        >
                            {summarising ? 'Summarising…' : 'Summarise'}
                        </button>
                    )}
                    <span className={`text-sm font-semibold ${statusColour[job.status]}`}>
                        {job.status}{step ? ` — ${step}` : ''}
                    </span>
                </div>
            </div>
            {job.status === 'PROCESSING' && (
                <div className="mt-2 h-1.5 bg-gray-200 rounded">
                    <div
                        className="h-1.5 bg-yellow-400 rounded transition-all duration-500"
                        style={{ width: step === 'extracted' ? '66%' : '33%' }}
                    />
                </div>
            )}
            {job.status === 'DONE' && (
                <div className="mt-2 h-1.5 bg-green-400 rounded" />
            )}
            {job.summary && (
                <p className="mt-2 text-sm text-gray-300">{job.summary}</p>
            )}
            {job.status === 'FAILED' && job.error && (
                <p className="mt-1 text-xs text-red-400">{job.error}</p>
            )}
        </div>
    )
}
