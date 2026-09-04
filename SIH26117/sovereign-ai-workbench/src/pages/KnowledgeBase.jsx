import { useState , useRef } from "react";
import {
  Search,
  Upload,
  FileText,
  Database,
  FolderOpen,
  CheckCircle2,
  Clock3,
  MoreVertical,
  Trash2,
  Eye,
  ShieldCheck,
  Brain,
  FileSpreadsheet,
  FileImage,
} from "lucide-react";

function KnowledgeBase() {
  const [search, setSearch] = useState("");
  const [addedKnowledge, setAddedKnowledge] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [deletedFiles, setDeletedFiles] = useState([]);
  const fileInputRef = useRef(null);

const handleAddKnowledge = () => {
  fileInputRef.current.click();
};

   const handleKnowledgeFile = (event) => {
  const file = event.target.files[0];

  if (!file) return;

  const newFile = {
    name: file.name,
    type: file.type.includes("image")
      ? "Image"
      : file.type.includes("spreadsheet")
      ? "Excel"
      : "PDF",
    category: "New Source",
    size: `${(file.size / 1024 / 1024).toFixed(2)} MB`,
    status: "Processing",
    updated: "Just now",
  };

  setAddedKnowledge((prev) => [newFile, ...prev]);

  setTimeout(() => {
    setAddedKnowledge((prev) =>
      prev.map((item) =>
        item.name === file.name
          ? { ...item, status: "Indexing" }
          : item
      )
    );
  }, 2000);

  setTimeout(() => {
    setAddedKnowledge((prev) =>
      prev.map((item) =>
        item.name === file.name
          ? { ...item, status: "Indexed" }
          : item
      )
    );
  }, 5000);
};


// DELETE FUNCTION
const handleDeleteKnowledge = (fileName) => {
  setAddedKnowledge((prev) =>
    prev.filter((item) => item.name !== fileName)
  );

  setDeletedFiles((prev) => [...prev, fileName]);

  if (selectedFile?.name === fileName) {
    setSelectedFile(null);
  }
};

  const knowledgeFiles = [
    {
      name: "Maintenance_SOP.pdf",
      type: "PDF",
      category: "Maintenance",
      size: "4.2 MB",
      status: "Indexed",
      updated: "Today",
    },
    {
      name: "Safety_Guidelines.pdf",
      type: "PDF",
      category: "Safety",
      size: "2.8 MB",
      status: "Indexed",
      updated: "Yesterday",
    },
    {
      name: "Equipment_Manual.pdf",
      type: "PDF",
      category: "Equipment",
      size: "8.6 MB",
      status: "Indexed",
      updated: "2 days ago",
    },
    {
      name: "Plant_Equipment_Image.png",
      type: "Image",
      category: "Engineering",
      size: "1.9 MB",
      status: "Indexed",
      updated: "3 days ago",
    },
    {
      name: "Equipment_Data.xlsx",
      type: "Excel",
      category: "Operations",
      size: "1.4 MB",
      status: "Processing",
      updated: "Today",
    },
  ];

    const allKnowledgeFiles = [
  ...addedKnowledge,
  ...knowledgeFiles.filter(
    (file) => !deletedFiles.includes(file.name)
  ),
];

const filteredFiles = allKnowledgeFiles.filter((file) =>
  file.name.toLowerCase().includes(search.toLowerCase())
);
  const getFileIcon = (type) => {
    if (type === "Image") return FileImage;
    if (type === "Excel") return FileSpreadsheet;
    return FileText;
  };

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      {/* Header */}
      <header className="border-b border-slate-800 bg-slate-900 px-6 py-5">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Knowledge Base</h1>
            <p className="mt-1 text-sm text-slate-400">
              Manage internal documents used by the local AI
            </p>
          </div>

          <div className="flex items-center gap-4">
            <div className="hidden items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-400 sm:flex">
              <ShieldCheck size={16} />
              Local Storage
            </div>

            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-blue-600 font-semibold">
              L
            </div>
          </div>
        </div>
      </header>

      {/* Main */}
      <main className="p-6">
        {/* Intro */}
        <div className="mb-6 rounded-2xl border border-slate-800 bg-slate-900 p-6">
          <div className="flex flex-col justify-between gap-5 md:flex-row md:items-center">
            <div className="flex items-start gap-4">
              <div className="rounded-xl bg-blue-500/10 p-3 text-blue-400">
                <Brain size={28} />
              </div>

              <div>
                <h2 className="text-lg font-semibold">
                  Internal Knowledge Repository
                </h2>
                <p className="mt-1 max-w-2xl text-sm text-slate-400">
                  Documents stored here are indexed locally and can be searched
                  by the AI agents using the organization's private knowledge
                  base.
                </p>
              </div>
            </div>

            <button
                onClick={handleAddKnowledge}
                className="flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-5 py-3 font-medium transition hover:bg-blue-500"
                >
                <Upload size={18} />
                Add Knowledge
                </button>

                <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.png,.jpg,.jpeg,.xlsx,.xls,.doc,.docx"
                onChange={handleKnowledgeFile}
                className="hidden"
                />
          </div>
        </div>

        {/* Stats */}
        <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-3">
          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
            <div className="mb-3 flex items-center justify-between">
              <p className="text-sm text-slate-400">Knowledge Sources</p>
              <Database className="text-blue-400" size={20} />
            </div>
            <p className="text-3xl font-bold">86</p>
            <p className="mt-1 text-xs text-slate-500">
              Documents indexed locally
            </p>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
            <div className="mb-3 flex items-center justify-between">
              <p className="text-sm text-slate-400">Indexed Content</p>
              <FolderOpen className="text-purple-400" size={20} />
            </div>
            <p className="text-3xl font-bold">1.8M</p>
            <p className="mt-1 text-xs text-slate-500">
              Text chunks available to AI
            </p>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
            <div className="mb-3 flex items-center justify-between">
              <p className="text-sm text-slate-400">Vector Database</p>
              <CheckCircle2 className="text-emerald-400" size={20} />
            </div>
            <p className="text-3xl font-bold">Healthy</p>
            <p className="mt-1 text-xs text-emerald-400">
              Local RAG system operational
            </p>
          </div>
        </div>

        {/* Search and filters */}
        <div className="mb-4 flex flex-col gap-3 md:flex-row">
          <div className="relative flex-1">
            <Search
              size={18}
              className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500"
            />

            <input
              type="text"
              placeholder="Search knowledge base..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full rounded-xl border border-slate-800 bg-slate-900 py-3 pl-11 pr-4 text-sm outline-none transition focus:border-blue-500"
            />
          </div>

          <select className="rounded-xl border border-slate-800 bg-slate-900 px-4 py-3 text-sm text-slate-300 outline-none">
            <option>All Categories</option>
            <option>Maintenance</option>
            <option>Safety</option>
            <option>Equipment</option>
            <option>Engineering</option>
            <option>Operations</option>
          </select>
        </div>

        {/* Knowledge files */}
        <div className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900">
          <div className="border-b border-slate-800 px-6 py-4">
            <h3 className="font-semibold">Knowledge Sources</h3>
          </div>

          <div className="divide-y divide-slate-800">
            {filteredFiles.map((file, index) => {
              const FileIcon = getFileIcon(file.type);

              return (
                <div
                  key={index}
                  className="flex flex-col gap-4 px-6 py-5 transition hover:bg-slate-800/40 md:flex-row md:items-center md:justify-between"
                >
                  <div className="flex items-center gap-4">
                    <div className="rounded-xl bg-slate-800 p-3">
                      <FileIcon size={22} className="text-blue-400" />
                    </div>

                    <div>
                      <p className="font-medium">{file.name}</p>

                      <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-500">
                        <span>{file.category}</span>
                        <span>•</span>
                        <span>{file.size}</span>
                        <span>•</span>
                        <span>Updated {file.updated}</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-4">
                   {file.status === "Indexed" ? (
  <span className="flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-3 py-1.5 text-xs text-emerald-400">
    <CheckCircle2 size={14} />
    Indexed
  </span>
            ) : file.status === "Indexing" ? (
            <span className="flex items-center gap-1.5 rounded-full bg-blue-500/10 px-3 py-1.5 text-xs text-blue-400">
                <Clock3 size={14} />
                Indexing...
            </span>
            ) : (
            <span className="flex items-center gap-1.5 rounded-full bg-yellow-500/10 px-3 py-1.5 text-xs text-yellow-400">
                <Clock3 size={14} />
                Processing
            </span>
            )}

                 <button
                    onClick={() => setSelectedFile(file)}
                    className="rounded-lg p-2 text-slate-400 transition hover:bg-slate-800 hover:text-white"
                    >
                    <Eye size={18} />
                    </button>
                    <button
                        onClick={() => handleDeleteKnowledge(file.name)}
                        className="rounded-lg p-2 text-slate-400 transition hover:bg-slate-800 hover:text-red-400"
                        >
                        <Trash2 size={18} />
                        </button>
                        <button className="rounded-lg p-2 text-slate-400 transition hover:bg-slate-800 hover:text-white">
                      <MoreVertical size={18} />
                    </button>
                  </div>
                </div>
              );
            })}

            {filteredFiles.length === 0 && (
              <div className="px-6 py-12 text-center text-slate-500">
                No documents found.
              </div>
            )}
          </div>
        </div>

        {/* Security info */}
        <div className="mt-6 flex items-start gap-3 rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4">
          <ShieldCheck
            size={20}
            className="mt-0.5 shrink-0 text-emerald-400"
          />

          <div>
            <p className="text-sm font-medium text-emerald-400">
              Sovereign Knowledge Security
            </p>
            <p className="mt-1 text-xs leading-5 text-slate-400">
              All documents, embeddings and search operations remain inside
              the organization's on-premise environment. No external API or
              cloud service is required.
            </p>
          </div>
        </div>
        
      </main>
      {selectedFile && (
  <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
    
    <div className="w-full max-w-lg rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl">
      
      {/* Popup Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Knowledge Details</h2>
          <p className="mt-1 text-sm text-slate-500">
            Document information
          </p>
        </div>

        <button
          onClick={() => setSelectedFile(null)}
          className="rounded-lg px-3 py-2 text-slate-400 transition hover:bg-slate-800 hover:text-white"
        >
          ✕
        </button>
      </div>

      {/* File Info */}
      <div className="flex items-center gap-4 rounded-xl bg-slate-800/60 p-4">
        <div className="rounded-xl bg-blue-500/10 p-3 text-blue-400">
          {(() => {
            const FileIcon = getFileIcon(selectedFile.type);
            return <FileIcon size={24} />;
          })()}
        </div>

        <div className="min-w-0">
          <p className="truncate font-medium">
            {selectedFile.name}
          </p>
          <p className="mt-1 text-sm text-slate-500">
            {selectedFile.type}
          </p>
        </div>
      </div>

      {/* Details */}
      <div className="mt-6 space-y-4">
        <div className="flex justify-between">
          <span className="text-slate-500">Category</span>
          <span className="text-slate-300">
            {selectedFile.category}
          </span>
        </div>

        <div className="flex justify-between">
          <span className="text-slate-500">File Size</span>
          <span className="text-slate-300">
            {selectedFile.size}
          </span>
        </div>

        <div className="flex justify-between">
          <span className="text-slate-500">Updated</span>
          <span className="text-slate-300">
            {selectedFile.updated}
          </span>
        </div>

        <div className="flex justify-between">
          <span className="text-slate-500">Status</span>
          <span className="text-emerald-400">
            {selectedFile.status}
          </span>
        </div>
      </div>

      {/* Security */}
      <div className="mt-6 rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4">
        <div className="flex items-center gap-2 text-sm text-emerald-400">
          <ShieldCheck size={17} />
          Secure Local Knowledge
        </div>

        <p className="mt-2 text-xs leading-5 text-slate-500">
          This knowledge source is stored and processed inside the
          sovereign on-premise environment.
        </p>
      </div>

      {/* Close */}
      <button
        onClick={() => setSelectedFile(null)}
        className="mt-6 w-full rounded-xl bg-slate-800 py-3 transition hover:bg-slate-700"
      >
        Close
      </button>
    </div>
  </div>
)}
    </div>
  );
}

export default KnowledgeBase;