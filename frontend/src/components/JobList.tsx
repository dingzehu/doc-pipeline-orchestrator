import { useEffect, useState } from "react"
import { fetchJobs, type Job } from "../api"
import { JobItem } from "./JobItem"

interface Props {
    newJob: Job | null
}

export function JobList({ newJob }: Props) {
    const [jobs, setJobs] = useState<Job[]>([])

    // load existing jobs on page load
    useEffect(() => {
        fetchJobs().then(setJobs)
    }, [])

    // prep end a newly uploaded job to the top of the list
    useEffect(() => {
        if (!newJob) return
        setJobs(prev => [newJob, ...prev])
    }, [newJob])

    if (jobs.length === 0) {
        return <p className="text-gray-400 text-sm mt-4">
            No jobs yet — upload a PDF above.
        </p>
    }

    return (
        <div className="mt-4">
            {jobs.map(job => (
                <JobItem key={job.id} initialJob={job} />
            ))}
        </div>
    )
}