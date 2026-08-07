import { render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { ReportPage } from './report';

// Mock fetchReportData to return a controlled fixture
vi.mock('../../lib/reports', () => ({
  fetchReportData: vi.fn(),
}));

// Mock api module — report.tsx imports it for handleDownload's PDF fetch
vi.mock('../../lib/api', () => ({
  api: {
    get: vi.fn(),
    defaults: { baseURL: 'http://localhost:8000/api/v1' },
  },
}));

// Mock TanStack Router
vi.mock('@tanstack/react-router', () => ({
  createFileRoute: () => () => ({}),
  useSearch: () => ({
    initiative_id: '42',
  }),
}));

import { fetchReportData } from '../../lib/reports';

describe('ReportPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('renders radar SVG and priority list from mocked report contract', async () => {
    const mockContract = {
      assessment_id: 1,
      version: 1,
      initiative: {
        name: 'Test Initiative',
        organization: null,
        contact_name: null,
        participant_type: null,
      },
      dimension_scores: [
        { category_id: 'cat-1', name: 'Dimension A', score: 2.5 },
      ],
      priority_list: [
        {
          category_id: 'cat-1',
          name: 'Data Governance',
          score: 2.34,
          band_id: 'orange',
          band_label: 'Preparatory',
          band_color: '#ff9900',
        },
        {
          category_id: 'cat-2',
          name: 'Data Quality',
          score: 3.15,
          band_id: 'yellow',
          band_label: 'Implementation',
          band_color: '#ffcc00',
        },
      ],
      radar_chart_svg: '<svg><polygon points="1,1 2,2 3,3" fill="#76b82a" stroke="#76b82a" stroke-width="2"/><text fill="#008ecf">Dimension A</text></svg>',
      maturity_bands: [
        { id: 'green', label: 'Scaling', min: 4.0, max: 5.0, color: '#76b82a' },
        { id: 'orange', label: 'Preparatory', min: 1.5, max: 2.99, color: '#ff9900' },
        { id: 'yellow', label: 'Implementation', min: 3.0, max: 3.99, color: '#ffcc00' },
      ],
    };

    vi.mocked(fetchReportData).mockResolvedValue(mockContract);

    render(<ReportPage />);

    // Wait for the component's useEffect to resolve and data to render
    await waitFor(() => {
      expect(screen.getByText('Test Initiative')).toBeInTheDocument();
    });

    // Assert radar SVG is rendered
    const svgContainer = screen.getByText('Maturity radar').closest('div');
    const svgElement = svgContainer?.querySelector('svg');
    expect(svgElement).toBeInTheDocument();
    expect(svgElement?.querySelector('polygon')?.getAttribute('fill')).toBe('#76b82a');
    expect(screen.getByText('Dimension A')).toBeInTheDocument();

    // Assert priority list items
    expect(screen.getByText('Data Governance')).toBeInTheDocument();
    expect(screen.getByText('Data Quality')).toBeInTheDocument();
    expect(screen.getByText('Preparatory')).toBeInTheDocument();
    expect(screen.getByText('Implementation')).toBeInTheDocument();

    // Assert scores are formatted with .toFixed(2)
    expect(screen.getByText('2.34')).toBeInTheDocument();
    expect(screen.getByText('3.15')).toBeInTheDocument();

    // Assert color dots match band_color (colors are converted to rgb by jsdom)
    const colorDots = screen.getByText('Priority areas').closest('div')?.querySelectorAll('[aria-hidden]');
    expect(colorDots).toHaveLength(2);
    expect(colorDots?.[0]?.getAttribute('style')).toContain('background: rgb(255, 153, 0)');
    expect(colorDots?.[1]?.getAttribute('style')).toContain('background: rgb(255, 204, 0)');
  });

  it('renders error message and retry button on fetch failure', async () => {
    vi.mocked(fetchReportData).mockRejectedValue(new Error('Network error'));

    render(<ReportPage />);

    // Wait for the error state to render
    await waitFor(() => {
      expect(screen.getByText(/couldn't load this report/i)).toBeInTheDocument();
    });

    // Assert retry button is present
    const retryButton = screen.getByRole('button', { name: /Retry/i });
    expect(retryButton).toBeInTheDocument();
  });
});
