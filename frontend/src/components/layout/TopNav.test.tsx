import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, expect, it, vi } from 'vitest';
import { TopNav } from './TopNav';

// TopNav calls useQuery -> api.get('/auth/me'). Mock the api client so the
// smoke test never issues a real network request (deterministic, no jsdom
// XHR/fetch dependency, no unhandled rejection noise).
vi.mock('../../lib/api', () => ({
  api: {
    get: vi.fn().mockResolvedValue({ data: { role: 'USER', email: 'smoke@test.local' } }),
  },
}));

// TopNav renders <Link>/<useNavigate> unconditionally at the top level.
// Mock @tanstack/react-router so render doesn't require a real router
// context/history — this is a CI-wiring smoke test (deep interaction is
// Phase 17 scope), so a stubbed Link/useNavigate is sufficient.
vi.mock('@tanstack/react-router', () => ({
  useNavigate: () => vi.fn(),
  Link: ({ children, to, ...rest }: { children?: React.ReactNode; to?: string }) => (
    <a href={typeof to === 'string' ? to : '#'} {...rest}>
      {children}
    </a>
  ),
}));

function renderTopNav() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <TopNav />
    </QueryClientProvider>
  );
}

describe('TopNav', () => {
  it('renders the navigation header deterministically', () => {
    renderTopNav();

    // A stable, always-present element regardless of auth/admin state.
    expect(screen.getByRole('banner')).toBeInTheDocument();
    expect(screen.getByAltText('CoE DSC')).toBeInTheDocument();
    expect(screen.getByLabelText('Open navigation menu')).toBeInTheDocument();
  });
});
