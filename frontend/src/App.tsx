import { useState } from "react"
import { Dropzone } from "./components/Dropzone"
import { JobList } from "./components/JobList"
import { ChatBox } from "./components/ChatBox"
import type { Job } from "./api"


function App() {
  const [newJob, setNewJob] = useState<Job | null>(null)

  function handleUpload(job: Job) {
    setNewJob(job)
  }
  
  return (
    <div className="max-w-2xl mx-auto p-6">
      <h1 className="text-2xl font-bold mb-6">Doc Pipeline</h1>
        <Dropzone onUpload={handleUpload} />
        <JobList newJob={newJob} />
        <ChatBox />
    </div>
  )
}

export default App
