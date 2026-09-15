import { useRef, useState } from 'react'
import { uploadPdf, type Job } from '../api'

interface Props {
    onUpload: (job: Job) => void
}

export function Dropzone({ onUpload }: Props) {
    const [dragging, setDragging] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const inputRef = useRef<HTMLInputElement>(null)

    async function handleFile(file: File) {
        if (!file.name.endsWith('.pdf')) {
            setError('Only PDF files are accepted')
            return
        }
        setError(null)
        try {
            const job = await uploadPdf(file)
            onUpload(job)
        } catch (e) {
            setError(e instanceof Error ? e.message : 'Upload failed')
        }
    }

    return (
        <div
            className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer
                ${dragging ? 'border-blue-400 bg-blue-50' : 'border-gray-300'}`}
            onClick={() => inputRef.current?.click()}
            onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => {
                e.preventDefault()
                setDragging(false)
                const file = e.dataTransfer.files[0]
                if (file) handleFile(file)
            }}
        >
            <input
                ref={inputRef}
                type="file"
                accept=".pdf"
                className="hidden"
                onChange={(e) => {
                    const file = e.target.files?.[0]
                    if (file) handleFile(file)
                }}
            />
            <p className="text-gray-500">Drop a PDF here or click to browse</p>
            {error && <p className="mt-2 text-sm text-red-400">{error}</p>}
        </div>
      )
}