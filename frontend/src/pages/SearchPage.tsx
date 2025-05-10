import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { searchTopics } from '../api/client';
import type { Topic, SearchRequest } from '../api/client';

export default function SearchPage() {
  const [searchParams, setSearchParams] = useState<SearchRequest>({
    term: '',
    page: 0,
    page_size: 10,
  });

  const { data, isLoading, error } = useQuery({
    queryKey: ['search', searchParams],
    queryFn: () => searchTopics(searchParams),
    enabled: searchParams.term?.length > 0,
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setSearchParams(prev => ({ ...prev, page: 0 }));
  };

  const handlePageChange = (newPage: number) => {
    setSearchParams(prev => ({ ...prev, page: newPage }));
  };

  return (
    <div className="space-y-6">
      <form onSubmit={handleSearch} className="flex gap-4">
        <input
          type="text"
          value={searchParams.term}
          onChange={(e) => setSearchParams(prev => ({ ...prev, term: e.target.value }))}
          placeholder="Search topics..."
          className="input flex-1"
        />
        <button type="submit" className="btn btn-primary">
          Search
        </button>
      </form>

      {isLoading && (
        <div className="text-center py-8">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          An error occurred while searching. Please try again.
        </div>
      )}

      {data && (
        <div className="space-y-4">
          <div className="text-sm text-gray-500">
            Found {data.total} results
          </div>
          
          <div className="grid gap-4">
            {data.topics.map((topic: Topic) => (
              <div key={topic.topicId} className="bg-white shadow rounded-lg p-6">
                <div className="flex justify-between items-start">
                  <div>
                    <h3 className="text-lg font-medium text-gray-900">{topic.topicTitle}</h3>
                    <p className="mt-1 text-sm text-gray-500">Topic Code: {topic.topicCode}</p>
                  </div>
                  <button
                    onClick={() => window.open(`/api/v1/download/${topic.topicId}`, '_blank')}
                    className="btn btn-secondary"
                  >
                    Download PDF
                  </button>
                </div>
                <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="font-medium">Component:</span> {topic.component}
                  </div>
                  <div>
                    <span className="font-medium">Status:</span> {topic.topicStatus}
                  </div>
                  {topic.programYear && (
                    <div>
                      <span className="font-medium">Program Year:</span> {topic.programYear}
                    </div>
                  )}
                  {topic.releaseNumber && (
                    <div>
                      <span className="font-medium">Release Number:</span> {topic.releaseNumber}
                    </div>
                  )}
                </div>
                {topic.keywords && topic.keywords.length > 0 && (
                  <div className="mt-4">
                    <span className="font-medium">Keywords:</span>
                    <div className="mt-1 flex flex-wrap gap-2">
                      {topic.keywords.map((keyword, index) => (
                        <span
                          key={index}
                          className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-primary-100 text-primary-800"
                        >
                          {keyword}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>

          {data.total > 0 && (
            <div className="flex justify-between items-center mt-6">
              <button
                onClick={() => handlePageChange(searchParams.page - 1)}
                disabled={searchParams.page === 0}
                className="btn btn-secondary disabled:opacity-50"
              >
                Previous
              </button>
              <span className="text-sm text-gray-500">
                Page {searchParams.page + 1} of {Math.ceil(data.total / searchParams.page_size)}
              </span>
              <button
                onClick={() => handlePageChange(searchParams.page + 1)}
                disabled={!data.has_more}
                className="btn btn-secondary disabled:opacity-50"
              >
                Next
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
} 