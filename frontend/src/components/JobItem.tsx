import { useEffect, useState } from "react"
import { fetchStatus, type Job } from "../api"
import { useSSE } from "../hooks/useSSE"

interface Props {
    initialJob: Job
}

export function JobItem({ initialJob }: Props) {
    const [job, setJob] = useState<Job>(initialJob)
    const { event, done } = useSSE(job.id)

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
                <span className={`text-sm font-semibold ${statusColour[job.status]}`}>
                    {job.status}{step ? ` — ${step}` : ''}
                </span>
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
            {job.status === 'FAILED' && job.error && (
                <p className="mt-1 text-xs text-red-400">{job.error}</p>
            )}
        </div>
    )
}
