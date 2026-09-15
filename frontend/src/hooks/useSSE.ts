import { useEffect, useState } from "react"

export interface SSEEvent {
    status: string
    step?: string
    error?: string
}

export function useSSE(jobId: number | null) {
    const [event, setEvent] = useState<SSEEvent | null>(null)
    const [done, setDone] = useState(false)

    useEffect(() => {
        if (jobId === null) return
        if (done) return

        const es = new EventSource(`/api/events/${jobId}/`)

        es.onmessage = (e) => {
            const data: SSEEvent = JSON.parse(e.data)
            setEvent(data)
            if (data.status === 'DONE' || data.status === 'FAILED') {
                es.close()
                setDone(true)
            }
        }

        es.onerror = () => {
            es.close()
            setDone(true)
        }

        return () => es.close()
    }, [jobId])

    return {event, done}
}