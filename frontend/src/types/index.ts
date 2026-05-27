export interface ScrapedURLMetadata {
  url: string;
  title: string;
  slug: string;
  markdown_path: string;
  executive_summary: string;
  tags: string[];
  categories: string[];
}

export interface Message {
  message_id?: string;
  datetime_utc: string;
  sender: string;
  content: string;
  media_type?: string;
  links?: string[];
  attachments?: string[];
  tags: string[];
  summary?: string | null;
  scraped_urls: ScrapedURLMetadata[];
}

export interface Segment {
  segment_id: string;
  start_time: string;
  end_time: string;
  messages: Message[];
  summary: string;
  tags: string[];
}

export interface Source {
  segment_id: string;
  title: string;
  slug: string;
  summary: string;
  tags: string[];
  categories: string[];
  url: string;
  type?: 'segment' | 'webpage';
  messages?: Message[];
  scraped_urls?: ScrapedURLMetadata[];
}

export interface TSNECoordinate {
  id: string;
  x: number;
  y: number;
  category: string;
}

export interface TrendingTag {
  tag: string;
  count: number;
}

export interface GapSuggestion {
  tag: string;
  suggestion: string;
}

export interface GapReport {
  dangling_tags: string[];
  broken_urls: string[];
  gap_suggestions: GapSuggestion[];
}

export interface AtlasData {
  heatmap: Record<string, number>;
  trending_tags: TrendingTag[];
  tsne_coordinates: TSNECoordinate[];
  gap_report: GapReport;
}

export interface IngestTask {
  id: string;
  url: string;
  category: string;
  status: string;
  progress: number;
  serverTaskId?: string;
}
