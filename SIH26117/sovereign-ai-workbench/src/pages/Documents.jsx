import { useState, useRef  } from "react";
import {
  Upload,
  Search,
  FileText,
  FileImage,
  FileSpreadsheet,
  Eye,
  Trash2,
  ShieldCheck,
  CheckCircle2,
  Clock3,
  HardDrive,
} from "lucide-react";

function Documents() {
const [search, setSearch] = useState("");
const [uploading, setUploading] = useState(false);
const [processing, setProcessing] = useState(false);
const [selectedFile, setSelectedFile] = useState(null);
const [uploadedDocuments, setUploadedDocuments] = useState([]);
const [selectedDocument, setSelectedDocument] = useState(null);
  const fileInputRef = useRef(null);

const handleUploadClick = () => {
  fileInputRef.current.click();
};

const handleFileChange = (event) => {
  const file = event.target.files[0];

  if (!file) return;

  setSelectedFile(file);
  setUploading(true);

  setTimeout(() => {
    setUploading(false);
    setProcessing(true);

    setTimeout(() => {
     setProcessing(false);

setUploadedDocuments((prev) => [
  ...prev,
  {
    name: file.name,
    type: file.type || "Document",
    size: `${(file.size / 1024 / 1024).toFixed(2)} MB`,
    date: "Just now",
    status: "Processed",
    icon: <FileText size={22} />,
  },
]);

alert(`${file.name} processed successfully!`);
    }, 3000);

  }, 2000);
};

  const documents = [
    {
      name: "Inspection_Report_2026.pdf",
      type: "PDF Document",
      size: "2.4 MB",
      date: "Today, 10:42 AM",
      status: "Processed",
      icon: <FileText size={22} />,
    },
    {
      name: "Maintenance_SOP.pdf",
      type: "PDF Document",
      size: "5.8 MB",
      date: "Yesterday, 4:18 PM",
      status: "Processed",
      icon: <FileText size={22} />,
    },
    {
      name: "Plant_Equipment_Image.png",
      type: "Image",
      size: "1.7 MB",
      date: "Sep 2, 2026",
      status: "Processed",
      icon: <FileImage size={22} />,
    },
    {
      name: "Equipment_Data.xlsx",
      type: "Spreadsheet",
      size: "846 KB",
      date: "Sep 1, 2026",
      status: "Processed",
      icon: <FileSpreadsheet size={22} />,
    },
    {
      name: "Safety_Guidelines.pdf",
      type: "PDF Document",
      size: "3.2 MB",
      date: "Aug 30, 2026",
      status: "Processing",
      icon: <FileText size={22} />,
    },
  ];

  const allDocuments = [...uploadedDocuments, ...documents];

const filteredDocuments = allDocuments.filter((doc) =>
  doc.name.toLowerCase().includes(search.toLowerCase())
);

  return (
    <div className="min-h-screen bg-slate-950 text-white">

      {/* Header */}
      <header className="h-20 border-b border-slate-800 flex items-center justify-between px-6 lg:px-8">

        <div>
          <p className="text-xs text-slate-500 uppercase tracking-wider">
            Workspace
          </p>

          <h1 className="text-xl font-semibold mt-1">
            Documents
          </h1>
        </div>

        <div className="flex items-center gap-4">

          <div className="hidden sm:flex items-center gap-2 px-4 py-2 rounded-full border border-emerald-500/20 bg-emerald-500/5">
            <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />

            <span className="text-sm text-emerald-400">
              Local Storage
            </span>
          </div>

          <div className="w-10 h-10 rounded-full bg-slate-800 flex items-center justify-center font-semibold">
            L
          </div>

        </div>

      </header>


      {/* Main */}
      <main className="p-6 lg:p-8">

        <div className="max-w-7xl mx-auto">

          {/* Page Introduction */}
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-5 mb-8">

            <div>
              <h2 className="text-2xl font-bold">
                Document Workspace
              </h2>

              <p className="text-slate-500 mt-2">
                Upload, manage and analyze confidential industrial documents.
              </p>
            </div>


            {/* Upload Button */}
            <button
  onClick={handleUploadClick}
  className="flex items-center justify-center gap-2 px-5 py-3 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-medium transition"
>
  <Upload size={18} />

  Upload Document
</button>
{selectedFile && (
  <div className="mb-6 p-5 rounded-2xl border border-slate-800 bg-slate-900/60">

    <div className="flex items-center justify-between mb-4">
      <div>
        <p className="font-medium text-white">
          {selectedFile.name}
        </p>

        <p className="text-xs text-slate-500 mt-1">
          {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
        </p>
      </div>

      <span
        className={`px-3 py-1 rounded-full text-xs font-medium ${
          uploading
            ? "bg-yellow-500/10 text-yellow-400"
            : processing
            ? "bg-blue-500/10 text-blue-400"
            : "bg-emerald-500/10 text-emerald-400"
        }`}
      >
        {uploading
          ? "Uploading..."
          : processing
          ? "AI Processing..."
          : "Completed"}
      </span>
    </div>

    <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
      <div
        className={`h-full transition-all duration-700 ${
          uploading
            ? "w-1/3 bg-yellow-400"
            : processing
            ? "w-2/3 bg-blue-400"
            : "w-full bg-emerald-400"
        }`}
      ></div>
    </div>

    <div className="flex justify-between mt-4 text-xs text-slate-500">
      <span>Upload</span>
      <span>OCR / Vision</span>
      <span>AI Analysis</span>
      <span>Completed</span>
    </div>

  </div>
)}
<input
  ref={fileInputRef}
  type="file"
  accept=".pdf,.png,.jpg,.jpeg,.xlsx,.xls,.doc,.docx"
  onChange={handleFileChange}
  className="hidden"
/>

          </div>


          {/* Security Banner */}
          <div className="mb-6 rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-5">

            <div className="flex items-start gap-4">

              <div className="w-10 h-10 shrink-0 rounded-xl bg-emerald-500/10 flex items-center justify-center">
                <ShieldCheck
                  size={21}
                  className="text-emerald-400"
                />
              </div>

              <div>

                <h3 className="font-medium text-emerald-400">
                  Secure On-Premise Storage
                </h3>

                <p className="text-sm text-slate-500 mt-1">
                  Uploaded files remain inside the organization's
                  environment and are not sent to external services.
                </p>

              </div>

            </div>

          </div>


          {/* Stats */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-5 mb-6">

            <DocumentStat
              icon={<FileText size={20} />}
              title="Total Documents"
              value="128"
            />

            <DocumentStat
              icon={<CheckCircle2 size={20} />}
              title="Processed"
              value="124"
            />

            <DocumentStat
              icon={<HardDrive size={20} />}
              title="Storage Used"
              value="2.4 GB"
            />

          </div>


          {/* Search + Filters */}
          <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-4 mb-6">

            <div className="flex flex-col md:flex-row gap-4">

              <div className="relative flex-1">

                <Search
                  size={18}
                  className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500"
                />

                <input
                  type="text"
                  placeholder="Search documents..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl py-3 pl-11 pr-4 text-sm text-white placeholder:text-slate-600 outline-none focus:border-emerald-500/40"
                />

              </div>


              <select className="bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm text-slate-400 outline-none">
                <option>All Types</option>
                <option>PDF</option>
                <option>Images</option>
                <option>Spreadsheets</option>
              </select>

            </div>

          </div>


          {/* Documents List */}
          <div className="rounded-2xl border border-slate-800 bg-slate-900/50 overflow-hidden">

            {/* Table Header */}
            <div className="hidden md:grid grid-cols-12 gap-4 px-6 py-4 border-b border-slate-800 text-xs text-slate-500 uppercase tracking-wider">

              <div className="col-span-5">
                Document
              </div>

              <div className="col-span-2">
                Size
              </div>

              <div className="col-span-2">
                Uploaded
              </div>

              <div className="col-span-2">
                Status
              </div>

              <div className="col-span-1">
              </div>

            </div>


            {/* Rows */}
            {filteredDocuments.length > 0 ? (

              filteredDocuments.map((doc, index) => (

                <div
                  key={index}
                  className="grid grid-cols-1 md:grid-cols-12 gap-4 md:items-center px-6 py-5 border-b border-slate-800 last:border-0 hover:bg-slate-900 transition"
                >

                  {/* Document */}
                  <div className="md:col-span-5 flex items-center gap-4">

                    <div className="w-11 h-11 shrink-0 rounded-xl bg-slate-800 flex items-center justify-center text-emerald-400">
                      {doc.icon}
                    </div>

                    <div className="min-w-0">

                      <p className="font-medium text-sm truncate">
                        {doc.name}
                      </p>

                      <p className="text-xs text-slate-500 mt-1">
                        {doc.type}
                      </p>

                    </div>

                  </div>


                  {/* Size */}
                  <div className="md:col-span-2">

                    <p className="text-sm text-slate-400">
                      {doc.size}
                    </p>

                  </div>


                  {/* Date */}
                  <div className="md:col-span-2">

                    <p className="text-sm text-slate-400">
                      {doc.date}
                    </p>

                  </div>


                  {/* Status */}
                  <div className="md:col-span-2">

                    {doc.status === "Processed" ? (

                      <span className="inline-flex items-center gap-2 text-xs text-emerald-400">

                        <CheckCircle2 size={15} />

                        Processed

                      </span>

                    ) : (

                      <span className="inline-flex items-center gap-2 text-xs text-yellow-400">

                        <Clock3 size={15} />

                        Processing

                      </span>

                    )}

                  </div>
                    {/* Actions */}
                <div className="md:col-span-1 flex md:justify-end">

                <button
                    onClick={() => setSelectedDocument(doc)}
                    className="flex items-center gap-2 px-3 py-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
                >
                    <Eye size={16} />
                    <span>View</span>
                </button>

                </div>

                  
                </div>

              ))

            ) : (

              <div className="py-16 text-center">

                <FileText
                  size={35}
                  className="mx-auto text-slate-700"
                />

                <p className="text-slate-400 mt-4">
                  No documents found
                </p>

                <p className="text-xs text-slate-600 mt-1">
                  Try another search term.
                </p>

              </div>

            )}

          </div>
            {/* Document Preview Modal */}
{selectedDocument && (
  <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">

    <div className="w-full max-w-lg bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl">

      <div className="flex items-center justify-between mb-6">

        <h2 className="text-xl font-semibold">
          Document Details
        </h2>

        <button
          onClick={() => setSelectedDocument(null)}
          className="text-slate-400 hover:text-white text-xl"
        >
          ✕
        </button>

      </div>

      <div className="flex items-center gap-4 p-4 bg-slate-800/60 rounded-xl">

        <div className="w-12 h-12 rounded-xl bg-emerald-500/10 flex items-center justify-center text-emerald-400">
          {selectedDocument.icon}
        </div>

        <div className="min-w-0">

          <p className="font-medium truncate">
            {selectedDocument.name}
          </p>

          <p className="text-sm text-slate-500 mt-1">
            {selectedDocument.type}
          </p>

        </div>

      </div>

      <div className="mt-6 space-y-4">

        <div className="flex justify-between">
          <span className="text-slate-500">File Size</span>
          <span className="text-slate-300">
            {selectedDocument.size}
          </span>
        </div>

        <div className="flex justify-between">
          <span className="text-slate-500">Uploaded</span>
          <span className="text-slate-300">
            {selectedDocument.date}
          </span>
        </div>

        <div className="flex justify-between">
          <span className="text-slate-500">Status</span>
          <span className="text-emerald-400">
            {selectedDocument.status}
          </span>
        </div>

      </div>

      <div className="mt-6 p-4 rounded-xl bg-emerald-500/5 border border-emerald-500/10">

        <div className="flex items-center gap-2 text-emerald-400 text-sm">
          <ShieldCheck size={17} />
          Secure Local Document
        </div>

        <p className="text-xs text-slate-500 mt-2">
          This document is processed inside the
          sovereign on-premise environment.
        </p>

      </div>

      <button
        onClick={() => setSelectedDocument(null)}
        className="w-full mt-6 py-3 rounded-xl bg-slate-800 hover:bg-slate-700 transition"
      >
        Close
      </button>

    </div>

  </div>
)}

          {/* Bottom Info */}
          <div className="flex items-center justify-center gap-2 mt-6 text-xs text-slate-600">

            <ShieldCheck size={14} />

            <span>
              All documents are processed within the secure local environment
            </span>

          </div>

        </div>

      </main>

    </div>
  );
}


/* Document Stat */

function DocumentStat({ icon, title, value }) {

  return (

    <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-5">

      <div className="flex items-center justify-between">

        <div>

          <p className="text-sm text-slate-500">
            {title}
          </p>

          <p className="text-2xl font-bold mt-2">
            {value}
          </p>

        </div>

        <div className="w-10 h-10 rounded-xl bg-slate-800 flex items-center justify-center text-emerald-400">
          {icon}
        </div>

      </div>

    </div>

  );
}


export default Documents;