import { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import AppLayout from "@/components/layout/AppLayout";
import { Search, X, Loader2, FileText, ChevronRight } from "lucide-react";
import { syllabusService } from "@/services/syllabusService";
import type { SyllabusSearchParams, SyllabusSearchResult } from "@/types/api";

const SEARCH_FIELDS = [
  { value: "title", label: "Title" },
  { value: "description", label: "Description" },
  { value: "extracted_text", label: "Full Text (OCR)" },
  { value: "subjects", label: "Subjects" },
  { value: "chapters", label: "Chapters" },
  { value: "topics", label: "Topics" },
];

const STATUS_OPTIONS = [
  { value: "", label: "All Statuses" },
  { value: "uploaded", label: "Uploaded" },
  { value: "processing", label: "Processing" },
  { value: "parsed", label: "Parsed" },
  { value: "failed", label: "Failed" },
];

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [searchFields, setSearchFields] = useState<string[]>(["title", "description", "subjects", "chapters", "topics"]);
  const [statusFilter, setStatusFilter] = useState("");
  const [results, setResults] = useState<SyllabusSearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pagination, setPagination] = useState({ total: 0, page: 1, per_page: 20, pages: 0 });
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [debouncedQuery, setDebouncedQuery] = useState("");

  // Debounce search query
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(query);
    }, 300);
    return () => clearTimeout(timer);
  }, [query]);

  // Perform search
  const performSearch = useCallback(async (page = 1) => {
    if (!debouncedQuery.trim()) {
      setResults([]);
      setPagination({ total: 0, page: 1, per_page: 20, pages: 0 });
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const params: SyllabusSearchParams = {
        q: debouncedQuery,
        search_in: searchFields.length > 0 ? searchFields : undefined,
        status: statusFilter || undefined,
        page,
        per_page: 20,
      };

      const response = await syllabusService.searchSyllabi(params);
      setResults(response.items);
      setPagination({
        total: response.total,
        page: response.page,
        per_page: response.per_page,
        pages: response.pages,
      });
    } catch (e: any) {
      const msg = e?.response?.data?.detail || "Search failed. Please try again.";
      setError(msg);
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, [debouncedQuery, searchFields, statusFilter]);

  // Trigger search when debounced query changes
  useEffect(() => {
    if (debouncedQuery !== query) {
      // Query is still being typed, wait for debounce
    }
  }, [query, debouncedQuery]);

  // Search when debounced query changes
  useEffect(() => {
    if (debouncedQuery) {
      performSearch(1);
    } else {
      setResults([]);
      setPagination({ total: 0, page: 1, per_page: 20, pages: 0 });
    }
  }, [debouncedQuery, performSearch]);

  const handleSearch = () => {
    performSearch(1);
  };

  const handleClear = () => {
    setQuery("");
    setDebouncedQuery("");
    setResults([]);
    setPagination({ total: 0, page: 1, per_page: 20, pages: 0 });
  };

  const handlePageChange = (newPage: number) => {
    if (newPage >= 1 && newPage <= pagination.pages) {
      performSearch(newPage);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "parsed":
        return "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400";
      case "processing":
        return "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400";
      case "failed":
        return "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400";
      default:
        return "bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300";
    }
  };

  const getMatchedFieldsDisplay = (fields: string[]) => {
    if (!fields || fields.length === 0) return null;
    return fields.map(f => {
      const field = SEARCH_FIELDS.find(sf => sf.value === f);
      return field ? field.label : f;
    }).join(", ");
  };

  return (
    <AppLayout title="Search Syllabi">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Search Bar */}
        <div className="card p-6 space-y-4">
          <div className="relative">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              placeholder="Search your syllabi by title, subject, topic, or content..."
              className="w-full pl-12 pr-12 py-3 text-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              autoFocus
            />
            {query && (
              <button
                onClick={handleClear}
                className="absolute right-4 top-1/2 -translate-y-1/2 p-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors"
                aria-label="Clear search"
              >
                <X className="w-5 h-5" />
              </button>
            )}
          </div>

          {/* Advanced Options */}
          <button
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 transition-colors"
          >
            <ChevronRight className={`w-4 h-4 transition-transform ${showAdvanced ? "rotate-90" : ""}`} />
            Advanced Filters
          </button>

          {showAdvanced && (
            <div className="space-y-4 pt-4 border-t border-slate-200 dark:border-slate-700 animate-in slide-in-from-top-2 duration-200">
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                  Search In
                </label>
                <div className="flex flex-wrap gap-2">
                  {SEARCH_FIELDS.map((field) => (
                    <label
                      key={field.value}
                      className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm cursor-pointer transition-all border ${
                        searchFields.includes(field.value)
                          ? "bg-primary-100 dark:bg-primary-900/30 border-primary-300 text-primary-700 dark:text-primary-300"
                          : "bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 hover:border-primary-300"
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={searchFields.includes(field.value)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setSearchFields([...searchFields, field.value]);
                          } else {
                            setSearchFields(searchFields.filter(f => f !== field.value));
                          }
                        }}
                        className="w-4 h-4 rounded border-slate-300 text-primary-600 focus:ring-primary-500"
                      />
                      {field.label}
                    </label>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                  Status Filter
                </label>
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="w-full md:w-64 px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                >
                  {STATUS_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          )}
        </div>

        {/* Results */}
        <div className="card">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
              <span className="ml-3 text-slate-600 dark:text-slate-400">Searching…</span>
            </div>
          ) : error ? (
            <div className="p-6 text-center">
              <p className="text-red-500">{error}</p>
            </div>
          ) : results.length === 0 && debouncedQuery ? (
            <div className="p-12 text-center">
              <FileText className="w-16 h-16 text-slate-300 dark:text-slate-600 mx-auto mb-4" />
              <h3 className="font-bold text-slate-700 dark:text-slate-200">No results found</h3>
              <p className="text-slate-500 dark:text-slate-400 mt-1">
                No syllabi match "{debouncedQuery}". Try adjusting your search.
              </p>
            </div>
          ) : results.length === 0 && !debouncedQuery ? (
            <div className="p-12 text-center">
              <FileText className="w-16 h-16 text-slate-300 dark:text-slate-600 mx-auto mb-4" />
              <h3 className="font-bold text-slate-700 dark:text-slate-200">Search your syllabi</h3>
              <p className="text-slate-500 dark:text-slate-400 mt-1">
                Enter a query above to search through your uploaded syllabi.
              </p>
            </div>
          ) : (
            <>
              <div className="p-4 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between">
                <p className="text-sm text-slate-600 dark:text-slate-400">
                  {pagination.total} result{pagination.total !== 1 ? "s" : ""} found for "{debouncedQuery}"
                </p>
              </div>
              <div className="divide-y divide-slate-200 dark:divide-slate-700">
                {results.map((result) => (
                  <Link
                    key={result.id}
                    to={`/syllabus/${result.id}`}
                    className="block p-4 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors"
                  >
                    <div className="flex items-start gap-4">
                      <div className="w-12 h-12 rounded-xl bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center flex-shrink-0">
                        <FileText className="w-6 h-6 text-primary-600 dark:text-primary-400" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <h3 className="font-semibold text-slate-800 dark:text-slate-100 truncate">
                            {result.title}
                          </h3>
                          <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${getStatusColor(result.status)}`}>
                            {result.status}
                          </span>
                        </div>
                        {result.description && (
                          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1 line-clamp-2">
                            {result.description}
                          </p>
                        )}
                        {result.matched_fields && result.matched_fields.length > 0 && (
                          <div className="mt-2 flex items-center gap-1.5 flex-wrap">
                            <span className="text-xs text-slate-400">Matched in:</span>
                            <span className="text-xs text-slate-600 dark:text-slate-300 bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded">
                              {getMatchedFieldsDisplay(result.matched_fields)}
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  </Link>
                ))}
              </div>

              {/* Pagination */}
              {pagination.pages > 1 && (
                <div className="p-4 border-t border-slate-200 dark:border-slate-700">
                  <nav className="flex items-center justify-center gap-1" aria-label="Pagination">
                    <button
                      onClick={() => handlePageChange(pagination.page - 1)}
                      disabled={pagination.page <= 1}
                      className="p-2 rounded-lg text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      aria-label="Previous page"
                    >
                      <ChevronRight className="w-5 h-5 rotate-180" />
                    </button>
                    {Array.from({ length: Math.min(pagination.pages, 5) }, (_, i) => {
                      let pageNum;
                      if (pagination.pages <= 5) {
                        pageNum = i + 1;
                      } else if (pagination.page <= 3) {
                        pageNum = i + 1;
                      } else if (pagination.page >= pagination.pages - 2) {
                        pageNum = pagination.pages - 4 + i;
                      } else {
                        pageNum = pagination.page - 2 + i;
                      }
                      return (
                        <button
                          key={pageNum}
                          onClick={() => handlePageChange(pageNum)}
                          className={`w-8 h-8 rounded-lg text-sm font-medium transition-colors ${
                            pageNum === pagination.page
                              ? "bg-primary-500 text-white"
                              : "text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
                          }`}
                        >
                          {pageNum}
                        </button>
                      );
                    })}
                    <button
                      onClick={() => handlePageChange(pagination.page + 1)}
                      disabled={pagination.page >= pagination.pages}
                      className="p-2 rounded-lg text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      aria-label="Next page"
                    >
                      <ChevronRight className="w-5 h-5" />
                    </button>
                  </nav>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </AppLayout>
  );
}