import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, X, Check, Loader2, Image as ImageIcon, Film } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";
const API = `${BACKEND_URL}/api`;

export default function GuestUpload({ token, folderName, allowedTypes }) {
    const [uploads, setUploads] = useState([]);
    const [uploading, setUploading] = useState(false);

    const onDrop = useCallback((acceptedFiles, rejectedFiles) => {
        // Handle rejected files (wrong type)
        if (rejectedFiles.length > 0) {
            toast.error(`Some files were rejected. Allowed types: ${allowedTypes?.join(', ') || 'All'}`);
        }

        const newUploads = acceptedFiles.map(file => ({
            file,
            id: Math.random().toString(36).substring(7),
            status: 'pending', // pending, uploading, success, error
            progress: 0
        }));

        setUploads(prev => [...prev, ...newUploads]);
    }, [allowedTypes]);

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept: allowedTypes ? allowedTypes.reduce((acc, type) => {
            // Map extensions to MIME types roughly
            if (type === '.jpg' || type === '.jpeg') acc['image/jpeg'] = [];
            if (type === '.png') acc['image/png'] = [];
            if (type === '.mp4') acc['video/mp4'] = [];
            if (type === '.mov') acc['video/quicktime'] = [];
            return acc;
        }, {}) : undefined
    });

    const removeUpload = (id) => {
        setUploads(prev => prev.filter(u => u.id !== id));
    };

    const startUpload = async () => {
        setUploading(true);

        // Upload sequentially to avoid overwhelming connection
        for (let i = 0; i < uploads.length; i++) {
            const upload = uploads[i];
            if (upload.status === 'success') continue;

            setUploads(prev => prev.map(u => u.id === upload.id ? { ...u, status: 'uploading' } : u));

            const formData = new FormData();
            formData.append('file', upload.file);
            formData.append('token', token);

            try {
                const res = await fetch(`${API}/files/public-upload`, {
                    method: 'POST',
                    body: formData
                });

                if (res.ok) {
                    setUploads(prev => prev.map(u => u.id === upload.id ? { ...u, status: 'success', progress: 100 } : u));
                } else {
                    const errorData = await res.json().catch(() => ({}));
                    const errorMessage = errorData.detail || `Upload failed (${res.status})`;
                    throw new Error(errorMessage);
                }
            } catch (e) {
                setUploads(prev => prev.map(u => u.id === upload.id ? { ...u, status: 'error', error: e.message } : u));
            }
        }

        setUploading(false);
        toast.success('Upload queue finished');
    };

    const pendingCount = uploads.filter(u => u.status === 'pending').length;

    return (
        <div className="max-w-2xl mx-auto px-4 py-12">
            <div className="text-center mb-8">
                <h1 className="text-3xl font-serif text-gray-900 mb-2">Upload to {folderName}</h1>
                <p className="text-gray-500">
                    Share your memories with the couple.
                    {allowedTypes && ` Allowed files: ${allowedTypes.join(', ')}`}
                </p>
            </div>

            {/* Dropzone */}
            <div
                {...getRootProps()}
                className={`border-2 border-dashed rounded-xl p-12 text-center transition-colors cursor-pointer mb-8
          ${isDragActive ? 'border-[#ad946d] bg-[#ad946d]/5' : 'border-gray-300 hover:border-[#ad946d]'}
        `}
            >
                <input {...getInputProps()} />
                <div className="w-16 h-16 rounded-full bg-[#ad946d]/10 flex items-center justify-center mx-auto mb-4">
                    <Upload className="w-8 h-8 text-[#ad946d]" />
                </div>
                <p className="text-lg font-medium text-gray-900 mb-1">
                    {isDragActive ? 'Drop files here' : 'Click or drop files to upload'}
                </p>
                <p className="text-sm text-gray-500">
                    High resolution photos and videos supported
                </p>
            </div>

            {/* File List */}
            <AnimatePresence>
                {uploads.length > 0 && (
                    <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className="space-y-3 mb-8"
                    >
                        {uploads.map((upload) => (
                            <div key={upload.id} className="bg-white border border-gray-200 rounded-lg p-3 flex items-center justify-between shadow-sm">
                                <div className="flex items-center gap-3 overflow-hidden">
                                    <div className="w-10 h-10 rounded bg-gray-100 flex items-center justify-center flex-shrink-0">
                                        {upload.file.type.startsWith('video') ? (
                                            <Film className="w-5 h-5 text-gray-500" />
                                        ) : (
                                            <ImageIcon className="w-5 h-5 text-gray-500" />
                                        )}
                                    </div>
                                    <div className="min-w-0">
                                        <p className="text-sm font-medium text-gray-900 truncate">{upload.file.name}</p>
                                        <p className="text-xs text-gray-500">{(upload.file.size / 1024 / 1024).toFixed(1)} MB</p>
                                    </div>
                                </div>

                                <div className="flex items-center gap-3">
                                    {upload.status === 'uploading' && <Loader2 className="w-5 h-5 text-[#ad946d] animate-spin" />}
                                    {upload.status === 'success' && <Check className="w-5 h-5 text-green-500" />}
                                    {upload.status === 'error' && (
                                        <div className="group relative">
                                            <X className="w-5 h-5 text-red-500 cursor-help" />
                                            {upload.error && (
                                                <div className="absolute right-0 top-full mt-2 w-48 bg-red-50 text-red-600 text-xs p-2 rounded shadow-lg z-20 hidden group-hover:block border border-red-100">
                                                    {upload.error}
                                                </div>
                                            )}
                                        </div>
                                    )}

                                    {upload.status === 'pending' && (
                                        <button onClick={() => removeUpload(upload.id)} className="text-gray-400 hover:text-red-500">
                                            <X className="w-5 h-5" />
                                        </button>
                                    )}
                                </div>
                            </div>
                        ))}
                    </motion.div>
                )}
            </AnimatePresence>


            {/* Actions */}
            {pendingCount > 0 && (
                <div className="text-center">
                    <Button
                        onClick={startUpload}
                        disabled={uploading}
                        className="bg-[#ad946d] hover:bg-[#9a8460] text-white px-8 py-6 text-lg rounded-full shadow-lg hover:shadow-xl transition-all"
                    >
                        {uploading ? (
                            <>
                                <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                                Uploading...
                            </>
                        ) : (
                            <>
                                <Upload className="w-5 h-5 mr-2" />
                                Upload {pendingCount} Files
                            </>
                        )}
                    </Button>
                </div>
            )}
        </div>
    );
}
